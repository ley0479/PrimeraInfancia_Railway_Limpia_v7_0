from __future__ import annotations

import json
import hashlib
import re
import unicodedata
import uuid
from datetime import datetime

from flask import g, jsonify, request
from modules.seguridad.services import get_request_user_context, require_roles


SCHEMA_VERSION = "1.0"
READ_ROLES = ('SUPERADMIN', 'GERENTE', 'COORDINADOR', 'NUTRICIONISTA')
EDIT_ROLES = READ_ROLES

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sn_materiales_tematicos (
 id INTEGER PRIMARY KEY AUTOINCREMENT, fundacion_id INTEGER NOT NULL,
 idp_documento_id INTEGER NOT NULL, periodo TEXT, estado TEXT NOT NULL DEFAULT 'BORRADOR',
 schema_version TEXT NOT NULL DEFAULT '1.0', extraction_id TEXT,
 titulo_documento TEXT, metodo_extraccion TEXT, extractor_version TEXT,
 resultado_original_json TEXT NOT NULL DEFAULT '{}', advertencias_json TEXT NOT NULL DEFAULT '[]',
 campos_faltantes_json TEXT NOT NULL DEFAULT '[]', revision INTEGER NOT NULL DEFAULT 1,
 creado_por INTEGER, revisado_por INTEGER, creado_en TEXT NOT NULL, actualizado_en TEXT NOT NULL,
 revisado_en TEXT, publicado_en TEXT,
 UNIQUE(fundacion_id,idp_documento_id), FOREIGN KEY(idp_documento_id) REFERENCES idp_documentos(id)
);
CREATE TABLE IF NOT EXISTS sn_temas (
 id INTEGER PRIMARY KEY AUTOINCREMENT, fundacion_id INTEGER NOT NULL, material_id INTEGER NOT NULL,
 version INTEGER NOT NULL DEFAULT 1, titulo_original TEXT NOT NULL, titulo_normalizado TEXT,
 categoria_sugerida TEXT, subtemas_json TEXT NOT NULL DEFAULT '[]', fragmento_origen TEXT,
 localizador_json TEXT NOT NULL DEFAULT '{}', procedencia_json TEXT NOT NULL DEFAULT '{}',
 estado TEXT NOT NULL DEFAULT 'BORRADOR', revision INTEGER NOT NULL DEFAULT 1,
 creado_por INTEGER, actualizado_por INTEGER, creado_en TEXT NOT NULL, actualizado_en TEXT NOT NULL,
 FOREIGN KEY(material_id) REFERENCES sn_materiales_tematicos(id), UNIQUE(material_id,id,version)
);
CREATE TABLE IF NOT EXISTS sn_tema_correcciones (
 id INTEGER PRIMARY KEY AUTOINCREMENT, fundacion_id INTEGER NOT NULL, tema_id INTEGER NOT NULL,
 revision_anterior INTEGER NOT NULL, valor_anterior_json TEXT NOT NULL, valor_nuevo_json TEXT NOT NULL,
 motivo TEXT, usuario_id INTEGER, creado_en TEXT NOT NULL, FOREIGN KEY(tema_id) REFERENCES sn_temas(id)
);
CREATE TABLE IF NOT EXISTS sn_tema_asignaciones (
 id INTEGER PRIMARY KEY AUTOINCREMENT, fundacion_id INTEGER NOT NULL, tema_id INTEGER NOT NULL,
 tema_version INTEGER NOT NULL, periodo TEXT NOT NULL, unidad_id INTEGER NOT NULL,
 responsable_id INTEGER, estado TEXT NOT NULL DEFAULT 'PUBLICADA', creado_por INTEGER,
 creado_en TEXT NOT NULL, actualizado_en TEXT NOT NULL,
 FOREIGN KEY(tema_id) REFERENCES sn_temas(id), FOREIGN KEY(unidad_id) REFERENCES master_unidades(id),
 UNIQUE(fundacion_id,tema_id,tema_version,periodo,unidad_id)
);
CREATE TABLE IF NOT EXISTS sn_actividad_temas (
 fundacion_id INTEGER NOT NULL, actividad_id INTEGER NOT NULL, tema_id INTEGER NOT NULL,
 tema_version INTEGER NOT NULL, creado_por INTEGER, creado_en TEXT NOT NULL,
 PRIMARY KEY(fundacion_id,actividad_id,tema_id,tema_version),
 FOREIGN KEY(actividad_id) REFERENCES sn_actividades_integrales(id), FOREIGN KEY(tema_id) REFERENCES sn_temas(id)
);
CREATE TABLE IF NOT EXISTS sn_actividad_calendario (
 fundacion_id INTEGER NOT NULL, actividad_id INTEGER NOT NULL, calendario_entregable_id INTEGER NOT NULL,
 fecha_sincronizada TEXT NOT NULL, creado_por INTEGER, creado_en TEXT NOT NULL, actualizado_en TEXT NOT NULL,
 PRIMARY KEY(fundacion_id,actividad_id), UNIQUE(fundacion_id,calendario_entregable_id),
 FOREIGN KEY(actividad_id) REFERENCES sn_actividades_integrales(id)
);
CREATE TABLE IF NOT EXISTS sn_informes_tematicos (
 id INTEGER PRIMARY KEY AUTOINCREMENT, fundacion_id INTEGER NOT NULL, actividad_id INTEGER NOT NULL,
 version INTEGER NOT NULL, snapshot_hash TEXT NOT NULL, snapshot_json TEXT NOT NULL,
 faltantes_json TEXT NOT NULL DEFAULT '[]', estado TEXT NOT NULL DEFAULT 'BORRADOR_INCOMPLETO',
 producto_id INTEGER, plantilla_codigo TEXT, plantilla_version TEXT, producto_sha256 TEXT,
 disparador TEXT NOT NULL DEFAULT 'MANUAL', observaciones_revision TEXT,
 creado_por INTEGER, creado_en TEXT NOT NULL, revisado_por INTEGER, revisado_en TEXT,
 aprobado_por INTEGER, aprobado_en TEXT, actualizado_en TEXT NOT NULL,
 UNIQUE(fundacion_id,actividad_id,version), UNIQUE(fundacion_id,actividad_id,snapshot_hash),
 FOREIGN KEY(actividad_id) REFERENCES sn_actividades_integrales(id), FOREIGN KEY(producto_id) REFERENCES sn_productos_actividad(id)
);
CREATE INDEX IF NOT EXISTS idx_sn_informe_tematico_estado ON sn_informes_tematicos(fundacion_id,estado,actividad_id);
CREATE INDEX IF NOT EXISTS idx_sn_material_tenant_estado ON sn_materiales_tematicos(fundacion_id,estado,periodo);
CREATE INDEX IF NOT EXISTS idx_sn_tema_material ON sn_temas(fundacion_id,material_id,estado);
CREATE INDEX IF NOT EXISTS idx_sn_asignacion_periodo ON sn_tema_asignaciones(fundacion_id,periodo,unidad_id,estado);
"""


def _now():
    return datetime.now().isoformat(timespec='seconds')


def _ctx():
    raw = get_request_user_context()
    return int(raw.get('fundacion_id') or 1), raw.get('usuario_id') or raw.get('id')


def _user():
    raw=getattr(g,'current_user',None) or {}
    return {**raw,'id':raw.get('id'),'fundacion_id':int(raw.get('fundacion_id') or 1),'rol':str(raw.get('rol') or '').upper()}


def _allowed_units(user):
    if user.get('rol') in {'SUPERADMIN','GERENTE','COORDINADOR'}: return None
    raw=user.get('unidades')
    if isinstance(raw,str):
        try: raw=json.loads(raw)
        except Exception: raw=[x.strip() for x in raw.split(',') if x.strip()]
    return [str(x).strip() for x in raw if str(x).strip()] if isinstance(raw,list) else []


def _unit_key(value): return ' '.join(str(value or '').strip().upper().split())


def _can_access_unit(name,user):
    allowed=_allowed_units(user)
    return True if allowed is None else _unit_key(name) in {_unit_key(x) for x in allowed}


def _norm(value):
    text = unicodedata.normalize('NFKD', str(value or '').lower())
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in text if not unicodedata.combining(c))).split())


def _loads(value, fallback):
    try:
        return json.loads(value or '')
    except Exception:
        return fallback


def _approved_health_template(repo, tenant, kind='INFORME'):
    """Return only an approved tenant/global template; never infer one from a filled acta."""
    code=f'{str(kind).strip().upper()}_SALUD_NUTRICION'
    try:
        return repo.fetch_one('''SELECT v.id plantilla_version_id,v.version,p.codigo,p.nombre,p.tipo_documento
          FROM doc_plantilla_versiones v JOIN doc_plantillas p ON p.id=v.plantilla_id
          JOIN doc_mapeos m ON m.plantilla_version_id=v.id AND m.estado='APROBADO' AND m.fundacion_id=?
          WHERE (v.fundacion_id=? OR (v.fundacion_id IS NULL AND p.scope='GLOBAL'))
            AND v.estado IN ('APROBADA','ACTIVA')
            AND (UPPER(p.tipo_documento)=? OR UPPER(p.codigo)=?)
          ORDER BY CASE WHEN v.fundacion_id=? THEN 0 ELSE 1 END,v.id DESC,m.version DESC LIMIT 1''',(tenant,tenant,code,code,tenant))
    except Exception:
        return None


def _institutional_product(product, kind='INFORME'):
    expected=f'{str(kind).strip().upper()}_SALUD_NUTRICION'
    return bool(product and str(product.get('plantilla_codigo') or '').upper()==expected and product.get('plantilla_version') and str(product.get('nombre_archivo') or '').lower().endswith('.docx'))


def _audit(repo, action, entity, entity_id, user=None, details=None):
    if hasattr(repo,'log'):
        try: trace_id=str(request.headers.get('X-Request-ID') or request.headers.get('X-Trace-Id') or uuid.uuid4().hex)[:80]
        except RuntimeError: trace_id=uuid.uuid4().hex
        payload=dict(details or {}); payload['trace_id']=trace_id
        repo.log(action,entity,entity_id,usuario=str((user or {}).get('username') or 'sistema'),nuevos=payload)


def _serialize_theme(row):
    item = dict(row)
    for key, fallback in (('subtemas_json', []), ('localizador_json', {}), ('procedencia_json', {})):
        item[key[:-5]] = _loads(item.pop(key, None), fallback)
    return item


def _theme_candidates(raw):
    text = str(raw.get('texto') or '')
    pages = raw.get('paginas') or []
    lines = [line.strip(' \t\r\n:-') for line in text.splitlines() if 4 <= len(line.strip()) <= 240]
    normalized = _norm(text)
    specs = [
        ('lactancia materna', 'Lactancia materna: técnicas de amamantamiento', 'LACTANCIA_MATERNA'),
        ('contaminacion cruzada', 'Contaminación cruzada: situaciones que la favorecen y prevención', 'INOCUIDAD_ALIMENTARIA'),
        ('codigo de colores', 'Código de colores para la separación de residuos sólidos', 'GESTION_AMBIENTAL'),
    ]
    themes = []
    for needle, proposal, category in specs:
        if needle not in normalized:
            continue
        source = next((line for line in lines if needle in _norm(line)), needle)
        themes.append({'titulo_original': source, 'titulo_normalizado': proposal,
                       'categoria_sugerida': category, 'subtemas': [], 'fragmento_origen': source,
                       'localizador': {'pagina': 1 if pages or raw.get('motor','').startswith(('IMAGEN','TESSERACT','AZURE')) else None},
                       'procedencia': {'titulo_original':'EXTRAIDO','titulo_normalizado':'PROPUESTO_IA','categoria_sugerida':'PROPUESTO_IA','subtemas':'EXTRAIDO'}})
    references = []
    if re.search(r'\b2184\b', text) and re.search(r'\b2019\b', text):
        references.append({'texto':'Resolución 2184 de 2019','tipo':'REFERENCIA_DOCUMENTAL_EXTRAIDA','vigencia_verificada':False})
    return themes, references


def _report_snapshot(repo,tenant,activity_id):
    activity=repo.fetch_one('SELECT * FROM sn_actividades_integrales WHERE id=? AND fundacion_id=?',(activity_id,tenant))
    if not activity:return None
    themes=repo.fetch_all('''SELECT t.id,t.version,t.titulo_original,t.titulo_normalizado,t.categoria_sugerida FROM sn_actividad_temas at JOIN sn_temas t ON t.id=at.tema_id AND t.fundacion_id=at.fundacion_id WHERE at.fundacion_id=? AND at.actividad_id=? ORDER BY t.id''',(tenant,activity_id))
    attendance=repo.fetch_all('SELECT id,documento,nombre_completo,convocado,asistio,firma_estado,observaciones FROM sn_actividad_participantes WHERE fundacion_id=? AND actividad_id=? ORDER BY id',(tenant,activity_id))
    evidences=repo.fetch_all('SELECT id,tipo,titulo,nombre_original,sha256,fecha_carga FROM sn_evidencias_integrales WHERE fundacion_id=? AND actividad_id=? AND activo=1 ORDER BY id',(tenant,activity_id))
    snapshot={'schema_version':'1.0','actividad':dict(activity),'temas':themes,'asistencia':attendance,'evidencias':evidences,'conteos':{'convocados':sum(1 for x in attendance if x.get('convocado')),'asistentes':sum(1 for x in attendance if x.get('asistio')),'personas_registradas':len(attendance),'evidencias':len(evidences)},'criterio_conteo':'personas únicas por registro de participante dentro de la actividad'}
    missing=[]
    for field,label in (('fecha_ejecucion','fecha real de ejecución'),('metodologia','metodología realizada'),('resultados','resultados reportados por el responsable')):
        if not str(activity.get(field) or '').strip():missing.append(label)
    if not themes:missing.append('temáticas vinculadas')
    if not attendance:missing.append('listado de participantes vinculado')
    if int(activity.get('requiere_evidencias') or 0) and not evidences:missing.append('evidencias auténticas')
    snapshot['completitud']={'completo':not missing,'faltantes':missing,'nota':'Los resultados son reportados por el responsable; no equivalen a resultados medidos salvo registro específico.'}
    digest=hashlib.sha256(json.dumps(snapshot,ensure_ascii=False,sort_keys=True,default=str,separators=(',',':')).encode('utf-8')).hexdigest()
    return snapshot,digest,missing


class TematicasService:
    def __init__(self, repo): self.repo = repo
    def init_schema(self):
        self.repo.execute_script(SCHEMA_SQL)
        if hasattr(self.repo,'ensure_column'):
            self.repo.ensure_column('sn_informes_tematicos','plantilla_codigo','TEXT')
            self.repo.ensure_column('sn_informes_tematicos','plantilla_version','TEXT')
            self.repo.ensure_column('sn_informes_tematicos','producto_sha256','TEXT')

    def material(self, material_id, tenant):
        row = self.repo.fetch_one('SELECT * FROM sn_materiales_tematicos WHERE id=? AND fundacion_id=?',(material_id,tenant))
        if not row: return None
        item=dict(row)
        item['resultado_original']=_loads(item.pop('resultado_original_json',None),{})
        item['advertencias']=_loads(item.pop('advertencias_json',None),[])
        item['campos_faltantes']=_loads(item.pop('campos_faltantes_json',None),[])
        item['temas']=[_serialize_theme(x) for x in self.repo.fetch_all('SELECT * FROM sn_temas WHERE material_id=? AND fundacion_id=? ORDER BY id',(material_id,tenant))]
        return item

    def extract(self, document_id, period=None):
        tenant,user_id=_ctx()
        doc=self.repo.fetch_one('SELECT id,nombre_original,resultado_bruto_json,motor_lectura,estado FROM idp_documentos WHERE id=? AND fundacion_id=?',(document_id,tenant))
        if not doc: raise KeyError('Documento fuente no encontrado en el ámbito autorizado.')
        raw=_loads(doc.get('resultado_bruto_json'),{})
        if not raw.get('texto'):
            raise ValueError('El documento aún no contiene texto extraído. Ejecuta o reintenta la lectura OCR en Motor Documental.')
        themes,references=_theme_candidates(raw); now=_now(); extraction_id=f'health-theme-{tenant}-{document_id}-{int(datetime.now().timestamp())}'
        warnings=[]; missing=[]
        if not themes: warnings.append('SIN_CONTENIDO_TEMATICO_IDENTIFICADO')
        if raw.get('calidad',{}).get('requiere_revision'): warnings.append('CALIDAD_REQUIERE_REVISION')
        if not period: missing.append('periodo')
        contract={'schema_version':SCHEMA_VERSION,'source_document_id':document_id,'extraction_id':extraction_id,
                  'document_title':doc.get('nombre_original'),'themes':themes,'references':references,
                  'warnings':warnings,'missing_fields':missing,'review_required':True}
        existing=self.repo.fetch_one('SELECT id FROM sn_materiales_tematicos WHERE fundacion_id=? AND idp_documento_id=?',(tenant,document_id))
        if existing: raise ValueError('El material ya tiene una extracción temática. Reprocésalo mediante una nueva versión, no mediante carga duplicada.')
        material_id=self.repo.execute('''INSERT INTO sn_materiales_tematicos
          (fundacion_id,idp_documento_id,periodo,estado,schema_version,extraction_id,titulo_documento,metodo_extraccion,extractor_version,resultado_original_json,advertencias_json,campos_faltantes_json,creado_por,creado_en,actualizado_en)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(tenant,document_id,period,'PENDIENTE_REVISION',SCHEMA_VERSION,extraction_id,doc.get('nombre_original'),raw.get('motor') or doc.get('motor_lectura'),'health-themes-1',json.dumps(contract,ensure_ascii=False),json.dumps(warnings),json.dumps(missing),user_id,now,now))
        for theme in themes:
            self.repo.execute('''INSERT INTO sn_temas(fundacion_id,material_id,titulo_original,titulo_normalizado,categoria_sugerida,subtemas_json,fragmento_origen,localizador_json,procedencia_json,estado,creado_por,actualizado_por,creado_en,actualizado_en)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(tenant,material_id,theme['titulo_original'],theme['titulo_normalizado'],theme['categoria_sugerida'],json.dumps(theme['subtemas'],ensure_ascii=False),theme['fragmento_origen'],json.dumps(theme['localizador']),json.dumps(theme['procedencia']), 'PENDIENTE_REVISION',user_id,user_id,now,now))
        _audit(self.repo,'EXTRAER_TEMATICAS_SALUD','sn_materiales_tematicos',material_id,_user(),{'documento_id':document_id,'temas_detectados':len(themes),'advertencias':warnings})
        return self.material(material_id,tenant)


def register_tematicas_routes(bp, repo, integral_service=None, database_path=None, data_dir=None):
    service=TematicasService(repo); service.init_schema()

    @bp.route('/tematicas/unidades',methods=['GET'])
    @require_roles(*READ_ROLES)
    def thematic_units():
        tenant,_=_ctx(); user=_user(); rows=repo.fetch_all('SELECT id,nombre,codigo_unidad,coordinador FROM master_unidades WHERE fundacion_id=? AND activo=1 ORDER BY nombre',(tenant,))
        rows=[row for row in rows if _can_access_unit(row.get('nombre'),user)]
        return jsonify({'unidades':rows,'fuente':'BASE_MAESTRA'})

    @bp.route('/tematicas/plantilla-informe',methods=['GET'])
    @require_roles(*READ_ROLES)
    def thematic_report_template():
        tenant,_=_ctx(); acta=_approved_health_template(repo,tenant,'ACTA'); report=_approved_health_template(repo,tenant,'INFORME')
        return jsonify({'estado':'APROBADA' if acta and report else 'PENDIENTE','institucional_disponible':bool(report),'plantilla':report,
          'formatos':{'ACTA':{'disponible':bool(acta),'plantilla':acta,'codigo_requerido':'ACTA_SALUD_NUTRICION'},'INFORME':{'disponible':bool(report),'plantilla':report,'codigo_requerido':'INFORME_SALUD_NUTRICION'}},
          'advertencia':None if acta and report else 'Falta registrar, mapear o aprobar una o más plantillas limpias. Las salidas faltantes usarán formato interno.'})

    @bp.route('/tematicas/materiales',methods=['GET'])
    @require_roles(*READ_ROLES)
    def thematic_materials():
        tenant,_=_ctx(); rows=repo.fetch_all('SELECT id FROM sn_materiales_tematicos WHERE fundacion_id=? ORDER BY actualizado_en DESC LIMIT 100',(tenant,))
        return jsonify({'materiales':[service.material(x['id'],tenant) for x in rows]})

    @bp.route('/tematicas/asignaciones',methods=['GET'])
    @require_roles(*READ_ROLES)
    def thematic_assignments():
        tenant,_=_ctx(); user=_user(); period=str(request.args.get('periodo') or '').strip()
        where=['a.fundacion_id=?']; params=[tenant]
        if period: where.append('a.periodo=?'); params.append(period)
        rows=repo.fetch_all(f'''SELECT a.*,u.nombre unidad_nombre,t.titulo_original,t.titulo_normalizado,t.categoria_sugerida
          FROM sn_tema_asignaciones a JOIN sn_temas t ON t.id=a.tema_id AND t.fundacion_id=a.fundacion_id
          JOIN master_unidades u ON u.id=a.unidad_id AND u.fundacion_id=a.fundacion_id
          WHERE {' AND '.join(where)} ORDER BY a.periodo DESC,u.nombre,t.titulo_original LIMIT 1000''',tuple(params))
        return jsonify({'asignaciones':[row for row in rows if _can_access_unit(row.get('unidad_nombre'),user)]})

    @bp.route('/tematicas/extraer',methods=['POST'])
    @require_roles(*EDIT_ROLES)
    def thematic_extract():
        data=request.get_json(silent=True) or {}
        try: result=service.extract(int(data.get('documento_id') or 0),data.get('periodo') or None)
        except KeyError as exc: return jsonify({'error':str(exc)}),404
        except (ValueError,TypeError) as exc: return jsonify({'error':str(exc)}),409
        return jsonify({'message':'Extracción temática creada para revisión humana.','material':result}),201

    @bp.route('/tematicas/materiales/<int:material_id>/temas',methods=['POST'])
    @require_roles(*EDIT_ROLES)
    def thematic_manual_theme(material_id):
        tenant,user_id=_ctx(); data=request.get_json(silent=True) or {}; title=str(data.get('titulo_original') or '').strip()
        if not service.material(material_id,tenant): return jsonify({'error':'Material no encontrado.'}),404
        if not title: return jsonify({'error':'El título original es obligatorio.'}),400
        now=_now(); theme_id=repo.execute('''INSERT INTO sn_temas(fundacion_id,material_id,titulo_original,titulo_normalizado,categoria_sugerida,subtemas_json,fragmento_origen,localizador_json,procedencia_json,estado,creado_por,actualizado_por,creado_en,actualizado_en) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(tenant,material_id,title,data.get('titulo_normalizado'),data.get('categoria_sugerida'),json.dumps(data.get('subtemas') or [],ensure_ascii=False),data.get('fragmento_origen'),json.dumps(data.get('localizador') or {}),json.dumps({'titulo_original':'EDITADO_USUARIO','titulo_normalizado':'EDITADO_USUARIO','subtemas':'EDITADO_USUARIO'}),'PENDIENTE_REVISION',user_id,user_id,now,now))
        _audit(repo,'AGREGAR_TEMATICA_MANUAL','sn_temas',theme_id,_user(),{'material_id':material_id,'procedencia':'EDITADO_USUARIO'})
        return jsonify({'message':'Tema manual agregado con procedencia registrada.','tema_id':theme_id}),201

    @bp.route('/tematicas/temas/<int:theme_id>',methods=['PATCH'])
    @require_roles(*EDIT_ROLES)
    def thematic_update(theme_id):
        tenant,user_id=_ctx(); data=request.get_json(silent=True) or {}; current=repo.fetch_one('SELECT * FROM sn_temas WHERE id=? AND fundacion_id=?',(theme_id,tenant))
        if not current:return jsonify({'error':'Tema no encontrado.'}),404
        expected=int(data.get('revision') or 0)
        if expected != int(current.get('revision') or 1): return jsonify({'error':'El tema fue modificado por otro revisor. Recarga antes de guardar.','codigo':'VERSION_CONFLICT'}),409
        allowed=('titulo_original','titulo_normalizado','categoria_sugerida','fragmento_origen'); updated=dict(current)
        for key in allowed:
            if key in data: updated[key]=data.get(key)
        if 'subtemas' in data: updated['subtemas_json']=json.dumps(data.get('subtemas') or [],ensure_ascii=False)
        provenance=_loads(current.get('procedencia_json'),{})
        for key in list(data):
            if key in allowed or key=='subtemas': provenance[key]='EDITADO_USUARIO'
        revision=expected+1; now=_now()
        repo.execute('''UPDATE sn_temas SET titulo_original=?,titulo_normalizado=?,categoria_sugerida=?,subtemas_json=?,fragmento_origen=?,procedencia_json=?,revision=?,actualizado_por=?,actualizado_en=? WHERE id=? AND fundacion_id=? AND revision=?''',(updated['titulo_original'],updated.get('titulo_normalizado'),updated.get('categoria_sugerida'),updated.get('subtemas_json') or '[]',updated.get('fragmento_origen'),json.dumps(provenance),revision,user_id,now,theme_id,tenant,expected))
        repo.execute('INSERT INTO sn_tema_correcciones(fundacion_id,tema_id,revision_anterior,valor_anterior_json,valor_nuevo_json,motivo,usuario_id,creado_en) VALUES(?,?,?,?,?,?,?,?)',(tenant,theme_id,expected,json.dumps(dict(current),ensure_ascii=False,default=str),json.dumps(updated,ensure_ascii=False,default=str),data.get('motivo'),user_id,now))
        _audit(repo,'CORREGIR_TEMATICA_SALUD','sn_temas',theme_id,_user(),{'revision_anterior':expected,'revision_nueva':revision,'campos':[key for key in data if key in allowed or key=='subtemas']})
        return jsonify({'message':'Corrección guardada sin borrar la lectura anterior.','tema':_serialize_theme(repo.fetch_one('SELECT * FROM sn_temas WHERE id=? AND fundacion_id=?',(theme_id,tenant)))})

    @bp.route('/tematicas/materiales/<int:material_id>/publicar',methods=['POST'])
    @require_roles(*EDIT_ROLES)
    def thematic_publish(material_id):
        tenant,user_id=_ctx(); user=_user(); data=request.get_json(silent=True) or {}; material=service.material(material_id,tenant)
        if not material:return jsonify({'error':'Material no encontrado.'}),404
        if data.get('confirmar') is not True:return jsonify({'error':'La publicación requiere confirmación explícita.'}),400
        period=str(data.get('periodo') or material.get('periodo') or '').strip()
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',period):return jsonify({'error':'Confirma un periodo con formato AAAA-MM.'}),400
        unit_ids=sorted({int(x) for x in (data.get('unidad_ids') or []) if str(x).isdigit()})
        if not unit_ids:return jsonify({'error':'Selecciona al menos una unidad autorizada.'}),400
        placeholders=','.join('?' for _ in unit_ids); units=repo.fetch_all(f'SELECT id FROM master_unidades WHERE fundacion_id=? AND activo=1 AND id IN ({placeholders})',(tenant,*unit_ids))
        if len(units)!=len(unit_ids):return jsonify({'error':'Una o más unidades no pertenecen al ámbito autorizado.'}),403
        unit_rows=repo.fetch_all(f'SELECT id,nombre FROM master_unidades WHERE fundacion_id=? AND activo=1 AND id IN ({placeholders})',(tenant,*unit_ids))
        if any(not _can_access_unit(row.get('nombre'),user) for row in unit_rows):return jsonify({'error':'Una o más unidades no están asignadas al usuario.'}),403
        themes=material.get('temas') or []
        if not themes:return jsonify({'error':'No hay temáticas revisables para publicar.'}),409
        now=_now(); created=0
        for theme in themes:
            repo.execute("UPDATE sn_temas SET estado='PUBLICADO',actualizado_por=?,actualizado_en=? WHERE id=? AND fundacion_id=?",(user_id,now,theme['id'],tenant))
            for unit_id in unit_ids:
                existing=repo.fetch_one('SELECT id FROM sn_tema_asignaciones WHERE fundacion_id=? AND tema_id=? AND tema_version=? AND periodo=? AND unidad_id=?',(tenant,theme['id'],theme['version'],period,unit_id))
                if not existing:
                    repo.execute('INSERT INTO sn_tema_asignaciones(fundacion_id,tema_id,tema_version,periodo,unidad_id,responsable_id,estado,creado_por,creado_en,actualizado_en) VALUES(?,?,?,?,?,?,?,?,?,?)',(tenant,theme['id'],theme['version'],period,unit_id,data.get('responsable_id'),'PUBLICADA',user_id,now,now)); created+=1
        repo.execute("UPDATE sn_materiales_tematicos SET periodo=?,estado='PUBLICADO',revisado_por=?,revisado_en=?,publicado_en=?,actualizado_en=? WHERE id=? AND fundacion_id=?",(period,user_id,now,now,now,material_id,tenant))
        _audit(repo,'PUBLICAR_TEMATICAS_SALUD','sn_materiales_tematicos',material_id,user,{'periodo':period,'unidad_ids':unit_ids,'asignaciones_creadas':created})
        return jsonify({'message':'Temáticas publicadas. No se crearon actividades, fechas, asistentes ni resultados.','asignaciones_creadas':created,'material':service.material(material_id,tenant)})

    @bp.route('/tematicas/actividades/<int:activity_id>/vincular',methods=['POST'])
    @require_roles(*EDIT_ROLES)
    def thematic_link_activity(activity_id):
        tenant,user_id=_ctx(); user=_user(); data=request.get_json(silent=True) or {}
        activity=repo.fetch_one('SELECT id,unidad_nombre,fecha_programada,fecha_ejecucion FROM sn_actividades_integrales WHERE id=? AND fundacion_id=?',(activity_id,tenant))
        if not activity:return jsonify({'error':'Actividad no encontrada.'}),404
        if not _can_access_unit(activity.get('unidad_nombre'),user):return jsonify({'error':'No tienes permiso sobre esta unidad.'}),403
        theme_ids=sorted({int(x) for x in (data.get('tema_ids') or []) if str(x).isdigit()})
        if not theme_ids:return jsonify({'error':'Selecciona al menos una temática publicada.'}),400
        placeholders=','.join('?' for _ in theme_ids)
        rows=repo.fetch_all(f'''SELECT DISTINCT t.id,t.version FROM sn_temas t JOIN sn_tema_asignaciones a ON a.tema_id=t.id AND a.tema_version=t.version AND a.fundacion_id=t.fundacion_id JOIN master_unidades u ON u.id=a.unidad_id AND u.fundacion_id=a.fundacion_id WHERE t.fundacion_id=? AND t.id IN ({placeholders}) AND t.estado='PUBLICADO' AND UPPER(TRIM(u.nombre))=UPPER(TRIM(?))''',(tenant,*theme_ids,activity.get('unidad_nombre')))
        if len(rows)!=len(theme_ids):return jsonify({'error':'Alguna temática no está publicada para la unidad de la actividad.'}),409
        now=_now(); created=0
        for row in rows:
            exists=repo.fetch_one('SELECT tema_id FROM sn_actividad_temas WHERE fundacion_id=? AND actividad_id=? AND tema_id=? AND tema_version=?',(tenant,activity_id,row['id'],row['version']))
            if not exists:
                repo.execute('INSERT INTO sn_actividad_temas(fundacion_id,actividad_id,tema_id,tema_version,creado_por,creado_en) VALUES(?,?,?,?,?,?)',(tenant,activity_id,row['id'],row['version'],user_id,now)); created+=1
        total=repo.fetch_one('SELECT COUNT(*) total FROM sn_actividad_temas WHERE fundacion_id=? AND actividad_id=?',(tenant,activity_id))
        _audit(repo,'VINCULAR_TEMATICAS_ACTIVIDAD','sn_actividades_integrales',activity_id,user,{'tema_ids':theme_ids,'vinculos_creados':created})
        return jsonify({'message':'Temáticas vinculadas. La asistencia existente no fue modificada.','vinculos_creados':created,'temas_vinculados':int((total or {}).get('total') or 0)})

    @bp.route('/tematicas/planificar',methods=['POST'])
    @require_roles(*EDIT_ROLES)
    def thematic_plan():
        if integral_service is None:return jsonify({'error':'El motor de actividades no está disponible.'}),503
        tenant,user_id=_ctx(); user=_user(); data=request.get_json(silent=True) or {}
        unit_id=int(data.get('unidad_id') or 0); unit=repo.fetch_one('SELECT id,nombre FROM master_unidades WHERE id=? AND fundacion_id=? AND activo=1',(unit_id,tenant))
        if not unit:return jsonify({'error':'Unidad no encontrada en Base Maestra.'}),404
        if not _can_access_unit(unit.get('nombre'),user):return jsonify({'error':'No tienes permiso sobre esta unidad.'}),403
        period=str(data.get('periodo') or '').strip()
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',period):return jsonify({'error':'El periodo debe tener formato AAAA-MM.'}),400
        theme_ids=sorted({int(x) for x in (data.get('tema_ids') or []) if str(x).isdigit()})
        if not theme_ids:return jsonify({'error':'Selecciona al menos una temática publicada.'}),400
        placeholders=','.join('?' for _ in theme_ids)
        themes=repo.fetch_all(f'''SELECT DISTINCT t.id,t.version,t.titulo_original,t.titulo_normalizado FROM sn_temas t JOIN sn_tema_asignaciones a ON a.tema_id=t.id AND a.tema_version=t.version AND a.fundacion_id=t.fundacion_id WHERE t.fundacion_id=? AND t.id IN ({placeholders}) AND a.periodo=? AND a.unidad_id=? AND a.estado='PUBLICADA' ''',(tenant,*theme_ids,period,unit_id))
        if len(themes)!=len(theme_ids):return jsonify({'error':'Alguna temática no está publicada para esa unidad y periodo.'}),409
        date=str(data.get('fecha_programada') or '').strip() or None
        if date and (not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date) or not date.startswith(period+'-')):return jsonify({'error':'La fecha debe ser válida y pertenecer al periodo confirmado.'}),400
        title=str(data.get('titulo') or '').strip()
        if not title:return jsonify({'error':'El título de la actividad es obligatorio.'}),400
        payload={'unidad_nombre':unit['nombre'],'linea_componente':data.get('linea_componente'),'tipo_actividad':data.get('tipo_actividad') or 'ENCUENTRO_EDUCATIVO','titulo':title,'objetivo':data.get('objetivo'),'metodologia':data.get('metodologia'),'fecha_programada':date,'estado':'PROGRAMADA' if date else 'SIN_PROGRAMAR','requiere_acta':data.get('requiere_acta',True),'requiere_listado':data.get('requiere_listado',True),'requiere_evidencias':data.get('requiere_evidencias',True),'responsable_id':data.get('responsable_id'),'responsable_nombre':data.get('responsable_nombre')}
        try: result=integral_service.create_activity(tenant,payload,user)
        except PermissionError as exc:return jsonify({'error':str(exc)}),403
        except Exception as exc:return jsonify({'error':str(exc)}),400
        activity=(result or {}).get('actividad') or {}; activity_id=int(activity.get('id') or 0); now=_now()
        for theme in themes:
            repo.execute('INSERT INTO sn_actividad_temas(fundacion_id,actividad_id,tema_id,tema_version,creado_por,creado_en) VALUES(?,?,?,?,?,?)',(tenant,activity_id,theme['id'],theme['version'],user_id,now))
        calendar_item=None; calendar_warning=None
        if date and database_path:
            try:
                from modules.calendario_inteligente.repository import CalendarioInteligenteRepository
                calendar=CalendarioInteligenteRepository(database_path,data_dir)
                calendar_item=calendar.create_entregable({'titulo':title,'descripcion':'Actividad planificada desde temáticas publicadas de Salud y Nutrición.','fecha_inicio':date,'fecha_limite':date,'modulo':'Salud y Nutrición','tipo_formato':'ACTIVIDAD_SALUD_NUTRICION','unidad':unit['nombre'],'responsable_id':data.get('responsable_id') or user_id,'responsable_nombre':data.get('responsable_nombre') or user.get('username'),'usuario_creador_id':user_id,'creado_por':user.get('username') or 'sistema','requiere_evidencia':False,'clave_unica':f'SN_ACTIVIDAD:{tenant}:{activity_id}'},origen='salud_tematicas')
                repo.execute('INSERT INTO sn_actividad_calendario(fundacion_id,actividad_id,calendario_entregable_id,fecha_sincronizada,creado_por,creado_en,actualizado_en) VALUES(?,?,?,?,?,?,?)',(tenant,activity_id,calendar_item['id'],date,user_id,now,now))
            except Exception:
                calendar_warning='La actividad quedó creada, pero la sincronización con Calendario está pendiente de reintento.'
        message='Actividad planificada. No se registraron asistentes, ejecución ni resultados.'
        _audit(repo,'PLANIFICAR_ACTIVIDAD_DESDE_TEMATICAS','sn_actividades_integrales',activity_id,user,{'tema_ids':theme_ids,'periodo':period,'unidad_id':unit_id,'fecha_programada':date,'estado_sincronizacion':'PENDIENTE_REINTENTO' if calendar_warning else ('SINCRONIZADO' if date else 'SIN_FECHA')})
        status=202 if calendar_warning else 201
        return jsonify({'message':message,'actividad':result,'temas':themes,'calendario':calendar_item,'estado_sincronizacion':'PENDIENTE_REINTENTO' if calendar_warning else ('SINCRONIZADO' if date else 'SIN_FECHA'),'advertencias':[calendar_warning] if calendar_warning else []}),status

    @bp.route('/tematicas/actividades/<int:activity_id>/completitud',methods=['GET'])
    @require_roles(*READ_ROLES)
    def thematic_completeness(activity_id):
        tenant,_=_ctx(); user=_user(); built=_report_snapshot(repo,tenant,activity_id)
        if not built:return jsonify({'error':'Actividad no encontrada.'}),404
        snapshot,digest,missing=built
        if not _can_access_unit(snapshot['actividad'].get('unidad_nombre'),user):return jsonify({'error':'No tienes permiso sobre esta unidad.'}),403
        return jsonify({'actividad_id':activity_id,'completo':not missing,'faltantes':missing,'snapshot_hash':digest,'conteos':snapshot['conteos'],'temas':snapshot['temas']})

    @bp.route('/tematicas/actividades/<int:activity_id>/informe',methods=['POST'])
    @require_roles(*EDIT_ROLES)
    def thematic_report(activity_id):
        if integral_service is None:return jsonify({'error':'El generador documental no está disponible.'}),503
        tenant,user_id=_ctx(); user=_user(); data=request.get_json(silent=True) or {}; built=_report_snapshot(repo,tenant,activity_id)
        if not built:return jsonify({'error':'Actividad no encontrada.'}),404
        snapshot,digest,missing=built
        if not _can_access_unit(snapshot['actividad'].get('unidad_nombre'),user):return jsonify({'error':'No tienes permiso sobre esta unidad.'}),403
        existing=repo.fetch_one('SELECT * FROM sn_informes_tematicos WHERE fundacion_id=? AND actividad_id=? AND snapshot_hash=?',(tenant,activity_id,digest))
        if existing:return jsonify({'message':'Ya existe un borrador para esta misma versión de datos; no se duplicó.','informe':existing,'faltantes':_loads(existing.get('faltantes_json'),[]),'idempotente':True})
        template=_approved_health_template(repo,tenant)
        generated=integral_service.prepare_activity_documents(tenant,activity_id,user,['INFORME']); product=((generated or {}).get('documentos') or [None])[0]
        if not product:return jsonify({'error':'El generador no produjo un archivo verificable.'}),500
        latest=repo.fetch_one('SELECT COALESCE(MAX(version),0) version FROM sn_informes_tematicos WHERE fundacion_id=? AND actividad_id=?',(tenant,activity_id)); version=int((latest or {}).get('version') or 0)+1; now=_now(); state='BORRADOR_INCOMPLETO' if missing else 'BORRADOR'
        report_id=repo.execute('''INSERT INTO sn_informes_tematicos(fundacion_id,actividad_id,version,snapshot_hash,snapshot_json,faltantes_json,estado,producto_id,plantilla_codigo,plantilla_version,producto_sha256,disparador,creado_por,creado_en,actualizado_en) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(tenant,activity_id,version,digest,json.dumps(snapshot,ensure_ascii=False,default=str),json.dumps(missing,ensure_ascii=False),state,product['id'],product.get('plantilla_codigo'),product.get('plantilla_version'),product.get('sha256'),str(data.get('disparador') or 'MANUAL').upper(),user_id,now,now))
        _audit(repo,'GENERAR_BORRADOR_TEMATICO','sn_informes_tematicos',report_id,user,{'actividad_id':activity_id,'version':version,'estado':state,'snapshot_hash':digest,'plantilla_codigo':product.get('plantilla_codigo'),'plantilla_version':product.get('plantilla_version')})
        institutional=_institutional_product(product,'INFORME')
        format_status={'institucional':institutional,'estado':'PLANTILLA_INSTITUCIONAL' if institutional else 'FORMATO_INTERNO','plantilla_aprobada':template,'advertencia':None if institutional else 'No hay una plantilla limpia y un mapeo aprobados con código INFORME_SALUD_NUTRICION.'}
        return jsonify({'message':'Borrador generado desde hechos registrados.' if not missing else 'BORRADOR INCOMPLETO generado sin inventar los campos faltantes.','informe':{'id':report_id,'version':version,'estado':state,'producto':product,'formato':format_status},'faltantes':missing}),201

    @bp.route('/tematicas/informes',methods=['GET'])
    @require_roles(*READ_ROLES)
    def thematic_reports():
        tenant,_=_ctx(); user=_user(); activity_id=request.args.get('actividad_id',type=int); where=['i.fundacion_id=?']; params=[tenant]
        if activity_id:where.append('i.actividad_id=?');params.append(activity_id)
        rows=repo.fetch_all(f'''SELECT i.id,i.actividad_id,i.version,i.snapshot_hash,i.faltantes_json,i.estado,i.producto_id,i.plantilla_codigo,i.plantilla_version,i.producto_sha256,i.disparador,i.observaciones_revision,i.creado_en,i.revisado_en,i.aprobado_en,a.unidad_nombre,a.titulo FROM sn_informes_tematicos i JOIN sn_actividades_integrales a ON a.id=i.actividad_id AND a.fundacion_id=i.fundacion_id WHERE {' AND '.join(where)} ORDER BY i.id DESC LIMIT 500''',tuple(params))
        result=[]
        for row in rows:
            if _can_access_unit(row.get('unidad_nombre'),user):
                item=dict(row);item['faltantes']=_loads(item.pop('faltantes_json',None),[]);result.append(item)
        return jsonify({'informes':result})

    @bp.route('/tematicas/informes/<int:report_id>/estado',methods=['POST'])
    @require_roles(*EDIT_ROLES)
    def thematic_report_state(report_id):
        tenant,user_id=_ctx(); user=_user(); data=request.get_json(silent=True) or {}; report=repo.fetch_one('SELECT * FROM sn_informes_tematicos WHERE id=? AND fundacion_id=?',(report_id,tenant))
        if not report:return jsonify({'error':'Informe no encontrado.'}),404
        activity=repo.fetch_one('SELECT unidad_nombre FROM sn_actividades_integrales WHERE id=? AND fundacion_id=?',(report['actividad_id'],tenant)) or {}
        if not _can_access_unit(activity.get('unidad_nombre'),user):return jsonify({'error':'No tienes permiso sobre esta unidad.'}),403
        target=str(data.get('estado') or '').upper(); allowed={'EN_REVISION','DEVUELTO','APROBADO'}
        if target not in allowed:return jsonify({'error':'Estado de revisión no permitido.'}),400
        missing=_loads(report.get('faltantes_json'),[])
        if target=='APROBADO' and missing:return jsonify({'error':'No se puede aprobar un borrador incompleto.','faltantes':missing}),409
        if target=='APROBADO' and user.get('rol') not in {'SUPERADMIN','GERENTE','COORDINADOR'}:return jsonify({'error':'La aprobación requiere un rol de coordinación autorizado.'}),403
        if target=='APROBADO':
            product=repo.fetch_one('SELECT plantilla_codigo,plantilla_version,nombre_archivo FROM sn_productos_actividad WHERE id=? AND fundacion_id=? AND activo=1',(report.get('producto_id'),tenant))
            if not _institutional_product(product,'INFORME'):
                return jsonify({'error':'El borrador usa formato interno. Registra y aprueba la plantilla INFORME_SALUD_NUTRICION, genera una nueva versión y revísala antes de aprobar.','codigo':'PLANTILLA_INSTITUCIONAL_REQUIRED'}),409
        if str(report.get('estado'))=='APROBADO':return jsonify({'error':'El informe aprobado está congelado; genera una nueva versión para cambios posteriores.'}),409
        now=_now(); reviewer=user_id if target in {'EN_REVISION','DEVUELTO','APROBADO'} else None; approver=user_id if target=='APROBADO' else None
        repo.execute('UPDATE sn_informes_tematicos SET estado=?,observaciones_revision=?,revisado_por=?,revisado_en=?,aprobado_por=?,aprobado_en=?,actualizado_en=? WHERE id=? AND fundacion_id=?',(target,data.get('observaciones'),reviewer,now,approver,now if approver else None,now,report_id,tenant))
        repo.execute('UPDATE sn_productos_actividad SET estado=?,revisado_por=?,fecha_revision=?,aprobado_por=?,fecha_aprobacion=?,observaciones=? WHERE id=? AND fundacion_id=?',(target,reviewer,now,approver,now if approver else None,data.get('observaciones'),report.get('producto_id'),tenant))
        _audit(repo,'CAMBIAR_ESTADO_INFORME_TEMATICO','sn_informes_tematicos',report_id,user,{'estado_anterior':report.get('estado'),'estado_nuevo':target,'producto_id':report.get('producto_id')})
        return jsonify({'message':'Estado actualizado mediante acción profesional explícita.','estado':target,'informe_id':report_id})

    return service
