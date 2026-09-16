from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime

from flask import jsonify, request
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
CREATE INDEX IF NOT EXISTS idx_sn_material_tenant_estado ON sn_materiales_tematicos(fundacion_id,estado,periodo);
CREATE INDEX IF NOT EXISTS idx_sn_tema_material ON sn_temas(fundacion_id,material_id,estado);
CREATE INDEX IF NOT EXISTS idx_sn_asignacion_periodo ON sn_tema_asignaciones(fundacion_id,periodo,unidad_id,estado);
"""


def _now():
    return datetime.now().isoformat(timespec='seconds')


def _ctx():
    raw = get_request_user_context()
    return int(raw.get('fundacion_id') or 1), raw.get('usuario_id') or raw.get('id')


def _norm(value):
    text = unicodedata.normalize('NFKD', str(value or '').lower())
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in text if not unicodedata.combining(c))).split())


def _loads(value, fallback):
    try:
        return json.loads(value or '')
    except Exception:
        return fallback


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


class TematicasService:
    def __init__(self, repo): self.repo = repo
    def init_schema(self): self.repo.execute_script(SCHEMA_SQL)

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
        return self.material(material_id,tenant)


def register_tematicas_routes(bp, repo):
    service=TematicasService(repo); service.init_schema()

    @bp.route('/tematicas/unidades',methods=['GET'])
    @require_roles(*READ_ROLES)
    def thematic_units():
        tenant,_=_ctx(); rows=repo.fetch_all('SELECT id,nombre,codigo_unidad,coordinador FROM master_unidades WHERE fundacion_id=? AND activo=1 ORDER BY nombre',(tenant,))
        return jsonify({'unidades':rows,'fuente':'BASE_MAESTRA'})

    @bp.route('/tematicas/materiales',methods=['GET'])
    @require_roles(*READ_ROLES)
    def thematic_materials():
        tenant,_=_ctx(); rows=repo.fetch_all('SELECT id FROM sn_materiales_tematicos WHERE fundacion_id=? ORDER BY actualizado_en DESC LIMIT 100',(tenant,))
        return jsonify({'materiales':[service.material(x['id'],tenant) for x in rows]})

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
        return jsonify({'message':'Corrección guardada sin borrar la lectura anterior.','tema':_serialize_theme(repo.fetch_one('SELECT * FROM sn_temas WHERE id=? AND fundacion_id=?',(theme_id,tenant)))})

    @bp.route('/tematicas/materiales/<int:material_id>/publicar',methods=['POST'])
    @require_roles(*EDIT_ROLES)
    def thematic_publish(material_id):
        tenant,user_id=_ctx(); data=request.get_json(silent=True) or {}; material=service.material(material_id,tenant)
        if not material:return jsonify({'error':'Material no encontrado.'}),404
        if data.get('confirmar') is not True:return jsonify({'error':'La publicación requiere confirmación explícita.'}),400
        period=str(data.get('periodo') or material.get('periodo') or '').strip()
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',period):return jsonify({'error':'Confirma un periodo con formato AAAA-MM.'}),400
        unit_ids=sorted({int(x) for x in (data.get('unidad_ids') or []) if str(x).isdigit()})
        if not unit_ids:return jsonify({'error':'Selecciona al menos una unidad autorizada.'}),400
        placeholders=','.join('?' for _ in unit_ids); units=repo.fetch_all(f'SELECT id FROM master_unidades WHERE fundacion_id=? AND activo=1 AND id IN ({placeholders})',(tenant,*unit_ids))
        if len(units)!=len(unit_ids):return jsonify({'error':'Una o más unidades no pertenecen al ámbito autorizado.'}),403
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
        return jsonify({'message':'Temáticas publicadas. No se crearon actividades, fechas, asistentes ni resultados.','asignaciones_creadas':created,'material':service.material(material_id,tenant)})

    return service
