"""Registro cerrado de herramientas de lectura de LÍA."""
from __future__ import annotations
from datetime import date
from modules.dbapi_compat import sqlite3
from modules.calendario_inteligente.repository import CalendarioInteligenteRepository
from modules.idp_documental.repository import IDPRepository
from .error_catalog import explain

ALLOWED_TOOLS = frozenset({'get_pending_activities_summary','get_document_processing_status','get_format_generation_status','get_structured_error'})

def _int_arg(args, name, minimum=1):
    try: value=int(args.get(name))
    except (TypeError,ValueError): raise ValueError(f'{name} debe ser un entero válido.')
    if value<minimum: raise ValueError(f'{name} no es válido.')
    return value

def execute(tool_name: str, *, args: dict, database_path: str, tenant_id: int, user: dict) -> dict:
    if tool_name not in ALLOWED_TOOLS: raise PermissionError('Herramienta no autorizada para LÍA.')
    if tool_name=='get_structured_error': return explain(str(args.get('code') or ''))
    if tool_name=='get_pending_activities_summary':
        rows=CalendarioInteligenteRepository(database_path).list_mis_pendientes(user,limit=100)
        today=date.today().isoformat(); overdue=sum(1 for x in rows if x.get('fecha_limite') and str(x['fecha_limite'])<today)
        due_today=sum(1 for x in rows if str(x.get('fecha_limite') or '')==today)
        return {'total':len(rows),'overdue':overdue,'due_today':due_today,'upcoming':max(0,len(rows)-overdue-due_today),'items':[{'id':x.get('id'),'title':x.get('titulo'),'due_date':x.get('fecha_limite'),'status':x.get('estado'),'module':x.get('modulo')} for x in rows[:5]]}
    if tool_name=='get_document_processing_status':
        item=IDPRepository(database_path).get_document(_int_arg(args,'document_id'),tenant_id)
        if not item: raise LookupError('Documento no encontrado o no autorizado.')
        validations=item.get('resultados_validacion') or []
        return {'document_id':item.get('id'),'status':item.get('estado'),'stage':item.get('etapa'),'progress':item.get('progreso'),'document_type':item.get('tipo_documento'),'error_code':item.get('error_codigo'),'error_message':item.get('error_mensaje'),'validation_errors':sum(1 for x in validations if str(x.get('nivel')).upper()=='CRITICO'),'warnings':sum(1 for x in validations if str(x.get('nivel')).upper()=='ADVERTENCIA')}
    test_id=_int_arg(args,'test_id')
    conn=sqlite3.connect(database_path);conn.row_factory=sqlite3.Row
    row=conn.execute('''SELECT p.id,p.estado,p.total_usuarios,p.errores_json,p.archivo_generado,p.fecha_creacion,t.tipo
      FROM mp_pruebas p JOIN mp_plantillas t ON t.id=p.plantilla_id
      WHERE p.id=? AND COALESCE(t.fundacion_id,1)=?''',(test_id,tenant_id)).fetchone();conn.close()
    if not row: raise LookupError('Generación no encontrada o no autorizada.')
    return {'test_id':row['id'],'format_type':row['tipo'],'status':row['estado'],'total_users':row['total_usuarios'],'has_errors':bool(row['errores_json']),'file_available':bool(row['archivo_generado']),'download_ready':str(row['estado']).upper() in {'OK','COMPLETADO','GENERADO'} and bool(row['archivo_generado']),'created_at':row['fecha_creacion']}
