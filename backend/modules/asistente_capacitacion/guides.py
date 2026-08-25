"""Contenido curado: orientación operativa, nunca decisiones automáticas."""

GUIDES = {
    'dashboard': {'titulo':'Panel principal','resumen':'Resume la operación autorizada para tu rol.','necesitas':['Una sesión activa'],'pasos':['Revisa alertas y pendientes.','Abre el módulo relacionado.','Confirma cada acción dentro del módulo fuente.']},
    'base-maestra': {'titulo':'Base Maestra','resumen':'Fuente única de participantes y su vinculación a UCA.','necesitas':['Archivo autorizado o datos verificados','UCA correcta'],'pasos':['Valida el archivo antes de cargar.','Corrige inconsistencias reportadas.','Confirma la UCA y conserva la trazabilidad.']},
    'planeacion-pedagogica': {'titulo':'Planeación pedagógica','resumen':'Gestiona proyectos por UCA, planeaciones, ejecución, evidencias y borradores documentales.','necesitas':['UCA y vigencia','Docente responsable','Objetivos y evidencias esperadas'],'pasos':['Crea o abre el proyecto pedagógico de la UCA.','Registra la planeación y sus actividades.','Vincula evidencias de la ejecución.','Genera borradores y realiza la validación docente final.']},
    'gestion-pedagogica': {'titulo':'Gestión pedagógica','resumen':'Organiza entregables, calendario, documentos y seguimiento pedagógico.','necesitas':['Periodo','UCA','Responsables'],'pasos':['Consulta pendientes del periodo.','Carga el soporte en el entregable correcto.','Envía a revisión y atiende devoluciones.']},
    'talento': {'titulo':'Talento Humano','resumen':'Administra referencias del personal, perfiles y asignaciones autorizadas.','necesitas':['Datos verificados del colaborador','Rol y UCA'],'pasos':['Busca antes de crear para evitar duplicados.','Actualiza la asignación vigente.','Revisa documentos y vencimientos.']},
    'salud-nutricion': {'titulo':'Salud y Nutrición','resumen':'Registra seguimiento nutricional referencial y evidencias autorizadas.','necesitas':['Participante existente','Fecha y profesional responsable'],'pasos':['Localiza al participante en Base Maestra.','Registra la actividad o valoración.','Confirma datos y soportes antes de cerrar.']},
    'familias-redes': {'titulo':'Familias y Redes','resumen':'Gestiona acompañamientos, compromisos, redes y evidencias.','necesitas':['UCA o familia autorizada','Objetivo del acompañamiento'],'pasos':['Selecciona el registro fuente.','Documenta la acción sin emitir diagnósticos.','Define acuerdos y seguimiento verificable.']},
    'componente-psicosocial': {'titulo':'Componente Psicosocial','resumen':'Organiza caracterización, planes y seguimientos sin sustituir criterio profesional.','necesitas':['Acceso autorizado','Consentimientos y fuente verificable'],'pasos':['Consulta la caracterización vigente.','Registra el plan como borrador.','Valida profesionalmente antes de cerrar.']},
    'expediente-operativo-uca': {'titulo':'Expediente Operativo por UCA','resumen':'Consolida referencias de todos los componentes sin copiar sus datos.','necesitas':['UCA autorizada'],'pasos':['Selecciona la UCA.','Revisa semáforos y fuentes.','Corrige cada novedad en su módulo de origen.']},
    'centro-planeacion': {'titulo':'Centro de Planeación','resumen':'Consolida actividades del calendario único y sus dependencias.','necesitas':['Periodo y UCA'],'pasos':['Filtra el periodo.','Revisa responsables y dependencias.','Actualiza la actividad en su módulo fuente.']},
    'manual-operativo': {'titulo':'Manual Operativo','resumen':'Consulta documentos vigentes y su versión institucional.','necesitas':['Documento oficial vigente'],'pasos':['Comprueba código, versión y vigencia.','Consulta la sección aplicable.','No uses documentos históricos como regla vigente.']},
}

DEFAULT_GUIDE = {'titulo':'Ayuda contextual','resumen':'Te orienta en esta vista sin modificar información.','necesitas':['Identificar la tarea que deseas realizar'],'pasos':['Revisa el objetivo de la vista.','Completa únicamente datos verificables.','Confirma el resultado antes de continuar.']}

# Cobertura curada del menú real. Cada pantalla obtiene propósito, insumos,
# resultado y errores; los módulos críticos conservan instrucciones específicas.
MODULE_TITLES = {
    'dashboard':'Centro de control de Primera Infancia', 'buscador-beneficiarios':'Consulta rápida de participantes',
    'calendario-inteligente':'Calendario inteligente', 'administracion':'Administración',
    'panel-comercial':'Panel comercial', 'gerencia-general':'Gerencia general',
    'acceso-compartido':'Acceso compartido', 'configuracion-institucional':'Configuración institucional',
    'manual-operativo':'Manual Operativo', 'ajustes':'Ajustes', 'administrador-disenos':'Administrador de diseños',
    'backups':'Copias de seguridad', 'calidad-datos':'Calidad de datos', 'motor-plantillas':'Motor de plantillas',
    'plantillas-oficiales':'Plantillas oficiales', 'paquete-mensual':'Paquete mensual',
    'reportes-gerenciales':'Reportes gerenciales', 'facturacion':'Facturación y suscripción',
    'formatos':'Formatos institucionales', 'nutricion':'Nutrición', 'cumplimiento':'Cumplimiento',
    'gestion-coordinador':'Gestión del coordinador', 'cuentas-cobro':'Cuentas de cobro',
    'relacion-mes':'Relación del mes', 'biblioteca-icbf':'Biblioteca ICBF',
    'motor-gestion-proyecto':'Motor de Gestión de Proyecto', 'supervision-calidad':'Supervisión y Calidad',
    'ambientes-protectores':'Ambientes protectores', 'integrity-stability':'Integridad y estabilidad',
    'motor-documental':'Motor Universal Documental',
}

for module_key, module_title in MODULE_TITLES.items():
    GUIDES.setdefault(module_key, {
        'titulo': module_title,
        'resumen': f'Esta pantalla permite consultar y gestionar las funciones autorizadas de {module_title}.',
        'necesitas': ['Sesión y fundación correctas', 'Periodo, unidad o registro requerido', 'Información verificable'],
        'pasos': ['Confirma la fundación, el periodo y los filtros visibles.', 'Selecciona la función que necesitas.', 'Revisa los datos y mensajes antes de continuar.', 'Ejecuta personalmente la acción autorizada.', 'Comprueba el resultado confirmado por el sistema.'],
        'resultado': f'Operación de {module_title} consultada o completada con trazabilidad.',
        'errores_frecuentes': ['Trabajar en un periodo o unidad incorrectos', 'Confundir un borrador con un resultado confirmado'],
    })

GUIDES['dashboard'].update({
    'resumen':'Es el centro de control de Primera Infancia: resume indicadores, alertas, pendientes y ofrece accesos a Cuéntame, Talento Humano, Salud y Nutrición y demás fuentes.',
    'necesitas':['Sesión activa', 'Fundación correcta', 'Periodo de consulta'],
    'pasos':['Confirma la fundación visible.', 'Revisa indicadores y alertas.', 'Usa los accesos Cuéntame, Talento Humano o Salud y Nutrición para abrir la fuente.', 'Consulta actividades próximas.', 'Corrige cualquier novedad dentro del módulo de origen.'],
    'resultado':'Una vista general de la operación; el panel no reemplaza las bases fuente.',
    'errores_frecuentes':['Intentar corregir datos desde el resumen', 'Confundir una alerta con un registro individual'],
})

GUIDES['motor-documental'].update({
    'resumen':'Carga, lee, valida y propone mapeos de documentos sin inventar campos faltantes.',
    'necesitas':['Archivo permitido menor al límite', 'Tipo documental', 'Revisión humana'],
    'pasos':['Carga el documento original.', 'Espera el estado de lectura.', 'Revisa campos, fuentes, unidades y participantes detectados.', 'Corrige el mapeo propuesto.', 'Aprueba únicamente información verificada.'],
    'resultado':'Lectura separada por fuente, diagnóstico y mapeo revisable.',
    'errores_frecuentes':['Failed to fetch', 'PARTICIPANTES_REQUERIDOS', 'Aprobar una lectura incompleta'],
})

for module_key, item in GUIDES.items():
    item.setdefault('proposito', item.get('resumen'))
    item.setdefault('resultado', 'La operación queda en el estado confirmado por el sistema.')
    item.setdefault('errores_frecuentes', ['Continuar sin revisar los mensajes y requisitos de la pantalla.'])
    item.setdefault('solo_orientacion', True)
