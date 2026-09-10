"""Intenciones deterministas de créditos para LIAM; solo SUPERADMIN modifica."""
from __future__ import annotations
from datetime import date, datetime, timedelta
import json, re, unicodedata, uuid
from modules.dbapi_compat import sqlite3
from modules.facturacion_suscripcion.repository import BillingRepository
from modules.facturacion_suscripcion.services import BillingService

def _plain(value):
    value=unicodedata.normalize('NFKD',str(value or '').casefold())
    return ''.join(c for c in value if not unicodedata.combining(c))

def parse_credit_request(question):
    q=_plain(question)
    if 'credito' not in q and not any(x in q for x in ('suscripcion','vigencia','vencida','vencer')):return None
    days=re.search(r'\b(\d{1,4})\s*dias?\b',q);credits=re.search(r'\b(\d{1,9})\s*creditos?\b',q)
    mutation=any(x in q for x in ('activa','activar','renueva','renovar','agrega','agregar','asigna','asignar','suspende','suspender'))
    name_match=re.search(r'\b(?:a|de)\s+(?:la\s+)?fundacion\s+([a-z0-9][a-z0-9 .&-]{2,}?)(?=\s+(?:por|durante|con|de)\s+\d|$)',q)
    name=(name_match.group(1).strip(' .') if name_match else None)
    if mutation:
        action='suspend_subscription' if any(x in q for x in ('suspende','suspender')) else ('add_credits' if credits and any(x in q for x in ('agrega','agregar','asigna','asignar')) else 'renew_days')
        return {'kind':'mutation','action':action,'foundation_name':name,'days':int(days.group(1)) if days else None,'credits':int(credits.group(1)) if credits else None}
    return {'kind':'query','action':'credit_summary','foundation_name':name}

def _find_foundation(repo,name):
    if not name:return None
    rows=repo.fetch_all('SELECT id,nombre FROM fundaciones WHERE LOWER(nombre)=LOWER(?) ORDER BY id LIMIT 2',(name,))
    if not rows:rows=repo.fetch_all('SELECT id,nombre FROM fundaciones WHERE LOWER(nombre) LIKE LOWER(?) ORDER BY nombre LIMIT 3',(f'%{name}%',))
    if len(rows)!=1:raise ValueError('No encontré una única fundación con ese nombre. Indica el nombre completo.')
    return rows[0]

def query(database_path,spec,role,current_foundation):
    repo=BillingRepository(database_path);service=BillingService(repo)
    target=_find_foundation(repo,spec.get('foundation_name')) if spec.get('foundation_name') else None
    if target:
        if role!='SUPERADMIN' and int(target['id'])!=int(current_foundation):raise PermissionError('Solo puedes consultar el crédito de tu propia fundación.')
        sub=service.get_subscription(int(target['id']))
        if not sub:raise LookupError('La fundación no tiene una suscripción configurada.')
        return {'scope':'foundation','foundation':target['nombre'],'subscription':sub,'message':f"{target['nombre']} tiene {int(sub.get('creditos_disponibles') or 0)} créditos disponibles, estado {sub.get('estado') or 'sin estado'} y vencimiento {sub.get('fecha_vencimiento') or 'sin fecha'}."}
    if role=='SUPERADMIN':
        data=service.dashboard();stats=data.get('stats') or {};subs=data.get('suscripciones') or []
        low=sum(1 for s in subs if int(s.get('creditos_incluidos_periodo') or 0)>0 and 0<int(s.get('creditos_disponibles') or 0)<=int(s.get('creditos_incluidos_periodo') or 0)*.2);empty=sum(1 for s in subs if int(s.get('creditos_disponibles') or 0)<=0)
        message=f"Hay {int(stats.get('fundaciones_total') or 0)} fundaciones: {int(stats.get('activas') or 0)} activas, {int(stats.get('por_vencer') or 0)} por vencer, {int(stats.get('vencidas') or 0)} vencidas, {low} con crédito bajo y {empty} con crédito agotado."
        return {'scope':'global','stats':stats,'low_credit':low,'exhausted':empty,'message':message}
    sub=service.get_subscription(int(current_foundation));return {'scope':'own','subscription':sub,'message':f"Tu fundación tiene {int(sub.get('creditos_disponibles') or 0)} créditos disponibles y estado {sub.get('estado') or 'sin estado'}."}

def create_proposal(database_path,spec,user_id):
    if spec.get('action')=='renew_days' and not spec.get('days'):raise ValueError('Indica cuántos días deseas agregar.')
    if spec.get('action')=='add_credits' and not spec.get('credits'):raise ValueError('Indica cuántos créditos deseas agregar.')
    repo=BillingRepository(database_path);target=_find_foundation(repo,spec.get('foundation_name'))
    if not target:raise ValueError('Indica la fundación que deseas modificar.')
    service=BillingService(repo);before=service.get_subscription(int(target['id']))
    if not before:raise LookupError('La fundación no tiene una suscripción configurada.')
    args={'fundacion_id':int(target['id']),'fundacion_nombre':target['nombre'],'days':spec.get('days'),'credits':spec.get('credits')}
    if spec['action']=='renew_days':
        current=date.fromisoformat(str(before.get('fecha_vencimiento'))[:10]);base=max(date.today(),current);args['new_expiry']=(base+timedelta(days=int(spec['days']))).isoformat();summary=f"Agregar {spec['days']} días a {target['nombre']}: vence {before.get('fecha_vencimiento')} y quedaría hasta {args['new_expiry']}."
    elif spec['action']=='add_credits':
        args['new_balance']=int(before.get('creditos_disponibles') or 0)+int(spec['credits']);summary=f"Agregar {spec['credits']} créditos a {target['nombre']}: pasaría de {int(before.get('creditos_disponibles') or 0)} a {args['new_balance']}."
    else: summary=f"Suspender la suscripción de {target['nombre']}."
    proposal_id=uuid.uuid4().hex;now=datetime.now();expires=now+timedelta(minutes=5);conn=sqlite3.connect(database_path)
    conn.execute('INSERT INTO lia_action_proposals(proposal_id,usuario_id,action_name,target_fundacion_id,arguments_json,before_json,status,expires_at,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(proposal_id,int(user_id),spec['action'],int(target['id']),json.dumps(args,ensure_ascii=False),json.dumps(before,ensure_ascii=False,default=str),'PENDING',expires.isoformat(timespec='seconds'),now.isoformat(timespec='seconds')));conn.commit();conn.close()
    return {'proposal_id':proposal_id,'summary':summary,'label':'Confirmar operación','confirmation_required':True,'server_confirmation':True,'expires_at':expires.isoformat(timespec='seconds')}

def confirm(database_path,proposal_id,user_id,role):
    if role!='SUPERADMIN':raise PermissionError('Solo SUPERADMIN puede modificar créditos o suscripciones.')
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row;row=conn.execute('SELECT * FROM lia_action_proposals WHERE proposal_id=?',(proposal_id,)).fetchone()
    if not row:conn.close();raise LookupError('La propuesta no existe.')
    row=dict(row)
    if int(row['usuario_id'])!=int(user_id):conn.close();raise PermissionError('La propuesta pertenece a otro usuario.')
    if row['status']!='PENDING' or datetime.fromisoformat(row['expires_at'])<datetime.now():conn.close();raise ValueError('La confirmación venció o ya fue utilizada.')
    args=json.loads(row['arguments_json']);updated=conn.execute("UPDATE lia_action_proposals SET status='EXECUTING' WHERE proposal_id=? AND status='PENDING'",(proposal_id,))
    if int(getattr(updated,'rowcount',0) or 0)!=1:conn.rollback();conn.close();raise ValueError('La propuesta ya está siendo procesada.')
    conn.commit();conn.close()
    repo=BillingRepository(database_path);service=BillingService(repo)
    try:
        if row['action_name']=='add_credits':service.asignar_creditos({'fundacion_id':args['fundacion_id'],'creditos':args['credits'],'accion':'asignacion_lian','descripcion':'Asignación confirmada mediante LIAM','idempotency_key':'liam-'+proposal_id})
        elif row['action_name']=='renew_days':service.upsert_subscription({'fundacion_id':args['fundacion_id'],'fecha_vencimiento':args['new_expiry'],'estado':'ACTIVA','observaciones':'Renovación confirmada mediante LIAM'},args['fundacion_id'])
        elif row['action_name']=='suspend_subscription':service.upsert_subscription({'fundacion_id':args['fundacion_id'],'estado':'SUSPENDIDA','observaciones':'Suspensión confirmada mediante LIAM'},args['fundacion_id'])
        else:raise ValueError('Acción financiera no registrada.')
        after=service.get_subscription(args['fundacion_id']);status='COMPLETED'
    except Exception:
        after={};status='FAILED';raise
    finally:
        conn=sqlite3.connect(database_path);conn.execute('UPDATE lia_action_proposals SET status=?,after_json=?,completed_at=? WHERE proposal_id=?',(status,json.dumps(after,ensure_ascii=False,default=str),datetime.now().isoformat(timespec='seconds'),proposal_id));conn.commit();conn.close()
    return {'message':f"Operación completada para {args['fundacion_nombre']}. Saldo: {int(after.get('creditos_disponibles') or 0)} créditos; vencimiento: {after.get('fecha_vencimiento') or 'sin fecha'}.",'subscription':after}
