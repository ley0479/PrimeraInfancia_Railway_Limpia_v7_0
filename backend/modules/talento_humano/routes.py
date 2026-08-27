from __future__ import annotations

from flask import Blueprint, jsonify, request
from modules.seguridad.services import require_roles

from .services import TalentoHumanoService, normalizar_registro

bp = Blueprint('talento_humano_core', __name__, url_prefix='/api/talento-core')


@bp.get('/estado')
def estado():
    service = TalentoHumanoService()
    return jsonify({'integracion': service.resumen_integracion()})


@bp.get('/fuente-maestra')
def fuente_maestra():
    return jsonify(TalentoHumanoService().fuente_maestra())


@bp.post('/sincronizar')
@require_roles('SUPERADMIN','GERENTE','COORDINADOR','AUXILIAR_ADMINISTRATIVO')
def sincronizar():
    service = TalentoHumanoService()
    resultado = service.sincronizar_base_maestra_publicada(origen='talento_core_endpoint')
    return jsonify({'resultado': resultado, 'integracion': service.resumen_integracion()})


@bp.post('/manual')
def manual():
    data = request.get_json(silent=True) or {}
    registro = normalizar_registro(data, archivo='manual')
    if not registro['documento'] or not registro['nombre']:
        return jsonify({'error': 'Nombre y documento son obligatorios.'}), 400
    service = TalentoHumanoService()
    resultado = service.guardar_registros([registro], origen='talento_core_manual')
    return jsonify({'resultado': resultado, 'integracion': service.resumen_integracion()})

@bp.get('/integral/dashboard')
@require_roles('SUPERADMIN','GERENTE','COORDINADOR','AUXILIAR_ADMINISTRATIVO')
def integral_dashboard():
    return jsonify(TalentoHumanoService().integral_dashboard())

@bp.get('/integral/personas/<int:persona_id>')
@require_roles('SUPERADMIN','GERENTE','COORDINADOR','AUXILIAR_ADMINISTRATIVO')
def integral_persona(persona_id):
    row=TalentoHumanoService().integral_person(persona_id)
    return (jsonify({'persona':row}),200) if row else (jsonify({'error':'Colaborador no encontrado.'}),404)

@bp.post('/integral/<string:entidad>')
@require_roles('SUPERADMIN','GERENTE','COORDINADOR','AUXILIAR_ADMINISTRATIVO')
def integral_crear(entidad):
    try:return jsonify({'message':'Registro agregado al expediente sin duplicar el colaborador.','dashboard':TalentoHumanoService().integral_add(entidad,request.get_json(silent=True) or {})}),201
    except ValueError as exc:return jsonify({'error':str(exc)}),400
