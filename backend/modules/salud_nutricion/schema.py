"""
Esquema aislado del módulo Salud y Nutrición Inteligente.

Todas las tablas usan prefijo sn_ para evitar conflictos con las tablas existentes.
Fase 2C.8 formaliza historial nutricional, BOA, diagnósticos, alertas,
seguimientos trimestrales y calendario nutricional.
"""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sn_valoraciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER DEFAULT 1,
    usuario_creador_id INTEGER,
    tipo_documento TEXT,
    documento TEXT NOT NULL,
    nui TEXT,
    nombre_completo TEXT,
    fecha_nacimiento TEXT,
    edad_meses INTEGER DEFAULT 0,
    edad_texto TEXT,
    sexo TEXT,
    unidad TEXT,
    docente TEXT,
    acudiente TEXT,
    telefono TEXT,
    direccion TEXT,
    fecha_valoracion TEXT,
    peso_kg REAL,
    talla_cm REAL,
    imc REAL,
    perimetro_braquial_cm REAL,
    perimetro_cefalico_cm REAL,
    z_peso_edad REAL,
    z_talla_edad REAL,
    z_peso_talla REAL,
    z_imc_edad REAL,
    z_braquial_edad REAL,
    diag_peso_edad TEXT,
    diag_talla_edad TEXT,
    diag_peso_talla TEXT,
    diag_imc_edad TEXT,
    diag_braquial_edad TEXT,
    diagnostico_global TEXT,
    nivel_alerta TEXT DEFAULT 'VERDE',
    estado_control TEXT,
    trimestre TEXT,
    periodo TEXT,
    proximo_control TEXT,
    fuente_archivo TEXT,
    observaciones TEXT,
    activo INTEGER DEFAULT 1,
    fecha_carga TEXT NOT NULL,
    fecha_actualizacion TEXT,
    usuario_carga TEXT DEFAULT 'sistema'
);

CREATE INDEX IF NOT EXISTS idx_sn_valoraciones_documento ON sn_valoraciones(documento);
CREATE INDEX IF NOT EXISTS idx_sn_valoraciones_periodo ON sn_valoraciones(periodo);
CREATE INDEX IF NOT EXISTS idx_sn_valoraciones_unidad ON sn_valoraciones(unidad);
CREATE INDEX IF NOT EXISTS idx_sn_valoraciones_diagnostico ON sn_valoraciones(diagnostico_global);
CREATE INDEX IF NOT EXISTS idx_sn_valoraciones_fundacion ON sn_valoraciones(fundacion_id);

CREATE TABLE IF NOT EXISTS sn_alertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER DEFAULT 1,
    usuario_creador_id INTEGER,
    documento TEXT,
    valoracion_id INTEGER,
    tipo TEXT NOT NULL,
    nivel TEXT DEFAULT 'AMARILLO',
    mensaje TEXT NOT NULL,
    unidad TEXT,
    fecha_alerta TEXT NOT NULL,
    atendida INTEGER DEFAULT 0,
    observaciones TEXT,
    fecha_creacion TEXT NOT NULL,
    fecha_actualizacion TEXT,
    FOREIGN KEY (valoracion_id) REFERENCES sn_valoraciones(id)
);

CREATE INDEX IF NOT EXISTS idx_sn_alertas_documento ON sn_alertas(documento);
CREATE INDEX IF NOT EXISTS idx_sn_alertas_nivel ON sn_alertas(nivel);
CREATE INDEX IF NOT EXISTS idx_sn_alertas_fundacion ON sn_alertas(fundacion_id);

CREATE TABLE IF NOT EXISTS sn_cargas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER DEFAULT 1,
    usuario_creador_id INTEGER,
    tipo TEXT NOT NULL,
    archivo_original TEXT,
    archivo_guardado TEXT,
    total_registros INTEGER DEFAULT 0,
    registros_validos INTEGER DEFAULT 0,
    registros_con_alerta INTEGER DEFAULT 0,
    errores_json TEXT,
    fecha_carga TEXT NOT NULL,
    fecha_actualizacion TEXT,
    usuario TEXT DEFAULT 'sistema'
);

CREATE TABLE IF NOT EXISTS sn_comparaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER DEFAULT 1,
    usuario_creador_id INTEGER,
    archivo_anterior TEXT,
    archivo_actual TEXT,
    total_anterior INTEGER DEFAULT 0,
    total_actual INTEGER DEFAULT 0,
    nuevos INTEGER DEFAULT 0,
    retirados INTEGER DEFAULT 0,
    trasladados INTEGER DEFAULT 0,
    cambios INTEGER DEFAULT 0,
    resumen_json TEXT,
    reporte_excel TEXT,
    reporte_pdf TEXT,
    fecha_comparacion TEXT NOT NULL,
    fecha_actualizacion TEXT,
    usuario TEXT DEFAULT 'sistema'
);

CREATE TABLE IF NOT EXISTS sn_calendario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER DEFAULT 1,
    usuario_creador_id INTEGER,
    documento TEXT,
    valoracion_id INTEGER,
    tipo_evento TEXT NOT NULL,
    fecha_programada TEXT NOT NULL,
    estado TEXT DEFAULT 'PROGRAMADO',
    nivel TEXT DEFAULT 'VERDE',
    unidad TEXT,
    responsable TEXT,
    descripcion TEXT,
    fecha_creacion TEXT NOT NULL,
    fecha_actualizacion TEXT,
    FOREIGN KEY (valoracion_id) REFERENCES sn_valoraciones(id)
);

CREATE INDEX IF NOT EXISTS idx_sn_calendario_fecha ON sn_calendario(fecha_programada);
CREATE INDEX IF NOT EXISTS idx_sn_calendario_documento ON sn_calendario(documento);
CREATE INDEX IF NOT EXISTS idx_sn_calendario_fundacion ON sn_calendario(fundacion_id);

CREATE TABLE IF NOT EXISTS sn_adjuntos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER DEFAULT 1,
    usuario_creador_id INTEGER,
    documento TEXT,
    valoracion_id INTEGER,
    nombre_original TEXT,
    nombre_guardado TEXT,
    ruta_archivo TEXT,
    tipo TEXT,
    estado TEXT DEFAULT 'ACTIVO',
    fecha_carga TEXT NOT NULL,
    fecha_actualizacion TEXT,
    FOREIGN KEY (valoracion_id) REFERENCES sn_valoraciones(id)
);

CREATE TABLE IF NOT EXISTS sn_historial_acciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER DEFAULT 1,
    usuario_creador_id INTEGER,
    usuario TEXT,
    accion TEXT NOT NULL,
    entidad_tipo TEXT,
    entidad_id INTEGER,
    documento TEXT,
    datos_anteriores TEXT,
    datos_nuevos TEXT,
    fecha_accion TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sn_referencias_oms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER DEFAULT 1,
    indicador TEXT NOT NULL,
    sexo TEXT,
    edad_meses INTEGER,
    talla_cm REAL,
    medida REAL,
    sd3neg REAL,
    sd2neg REAL,
    sd1neg REAL,
    mediana REAL,
    sd1 REAL,
    sd2 REAL,
    sd3 REAL,
    fuente TEXT,
    fecha_carga TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sn_referencias_indicador ON sn_referencias_oms(indicador, sexo, edad_meses);
"""

# Esquema integral 2.6.0. Se mantiene separado para que las instalaciones
# existentes puedan evolucionar sin recrear las tablas históricas.
INTEGRAL_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sn_expedientes_integrales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL DEFAULT 1,
    beneficiario_id INTEGER,
    documento TEXT NOT NULL,
    tipo_participante TEXT DEFAULT 'NINO_NINA',
    unidad_nombre TEXT,
    expediente_uca_id INTEGER,
    responsable_id INTEGER,
    responsable_nombre TEXT,
    estado TEXT DEFAULT 'ACTIVO',
    observaciones TEXT,
    creado_por INTEGER,
    fecha_creacion TEXT NOT NULL,
    actualizado_por INTEGER,
    fecha_actualizacion TEXT,
    UNIQUE(fundacion_id, documento)
);
CREATE INDEX IF NOT EXISTS idx_sn_exp_integral_fundacion ON sn_expedientes_integrales(fundacion_id);
CREATE INDEX IF NOT EXISTS idx_sn_exp_integral_unidad ON sn_expedientes_integrales(fundacion_id, unidad_nombre);
CREATE INDEX IF NOT EXISTS idx_sn_exp_integral_documento ON sn_expedientes_integrales(fundacion_id, documento);

CREATE TABLE IF NOT EXISTS sn_documentos_salud (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL DEFAULT 1,
    expediente_id INTEGER NOT NULL,
    tipo_documento TEXT NOT NULL,
    estado TEXT DEFAULT 'PENDIENTE',
    entidad_emisora TEXT,
    numero_referencia TEXT,
    fecha_documento TEXT,
    fecha_verificacion TEXT,
    fecha_vencimiento TEXT,
    soporte_modulo TEXT,
    soporte_id INTEGER,
    soporte_ruta TEXT,
    observaciones TEXT,
    validado_por INTEGER,
    fecha_validacion TEXT,
    activo INTEGER DEFAULT 1,
    creado_por INTEGER,
    fecha_creacion TEXT NOT NULL,
    actualizado_por INTEGER,
    fecha_actualizacion TEXT,
    FOREIGN KEY (expediente_id) REFERENCES sn_expedientes_integrales(id),
    UNIQUE(fundacion_id, expediente_id, tipo_documento, activo)
);
CREATE INDEX IF NOT EXISTS idx_sn_doc_salud_expediente ON sn_documentos_salud(fundacion_id, expediente_id);
CREATE INDEX IF NOT EXISTS idx_sn_doc_salud_estado ON sn_documentos_salud(fundacion_id, tipo_documento, estado);
CREATE INDEX IF NOT EXISTS idx_sn_doc_salud_vencimiento ON sn_documentos_salud(fundacion_id, fecha_vencimiento);

CREATE TABLE IF NOT EXISTS sn_valoracion_validaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL DEFAULT 1,
    valoracion_id INTEGER NOT NULL,
    clasificacion_automatica TEXT,
    reglas_version TEXT,
    estado_validacion TEXT DEFAULT 'PENDIENTE',
    clasificacion_profesional TEXT,
    observacion_profesional TEXT,
    profesional_id INTEGER,
    profesional_nombre TEXT,
    fecha_validacion TEXT,
    version INTEGER DEFAULT 1,
    activo INTEGER DEFAULT 1,
    creado_por INTEGER,
    fecha_creacion TEXT NOT NULL,
    actualizado_por INTEGER,
    fecha_actualizacion TEXT,
    FOREIGN KEY (valoracion_id) REFERENCES sn_valoraciones(id)
);
CREATE INDEX IF NOT EXISTS idx_sn_val_validacion ON sn_valoracion_validaciones(fundacion_id, valoracion_id, activo);
CREATE INDEX IF NOT EXISTS idx_sn_val_estado ON sn_valoracion_validaciones(fundacion_id, estado_validacion);

CREATE TABLE IF NOT EXISTS sn_actividades_integrales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL DEFAULT 1,
    expediente_uca_id INTEGER,
    unidad_nombre TEXT,
    linea_componente TEXT NOT NULL,
    tipo_actividad TEXT NOT NULL,
    titulo TEXT NOT NULL,
    objetivo TEXT,
    metodologia TEXT,
    fecha_programada TEXT,
    fecha_ejecucion TEXT,
    hora_inicio TEXT,
    hora_fin TEXT,
    lugar TEXT,
    responsable_id INTEGER,
    responsable_nombre TEXT,
    estado TEXT DEFAULT 'PROGRAMADA',
    resultados TEXT,
    conclusiones_profesionales TEXT,
    compromisos_generales TEXT,
    requiere_acta INTEGER DEFAULT 1,
    requiere_listado INTEGER DEFAULT 1,
    requiere_evidencias INTEGER DEFAULT 1,
    motor_fuente TEXT,
    motor_tarea_id INTEGER,
    creado_por INTEGER,
    fecha_creacion TEXT NOT NULL,
    actualizado_por INTEGER,
    fecha_actualizacion TEXT
);
CREATE INDEX IF NOT EXISTS idx_sn_act_integral_unidad ON sn_actividades_integrales(fundacion_id, unidad_nombre);
CREATE INDEX IF NOT EXISTS idx_sn_act_integral_fecha ON sn_actividades_integrales(fundacion_id, fecha_programada);
CREATE INDEX IF NOT EXISTS idx_sn_act_integral_estado ON sn_actividades_integrales(fundacion_id, estado);

CREATE TABLE IF NOT EXISTS sn_actividad_participantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL DEFAULT 1,
    actividad_id INTEGER NOT NULL,
    expediente_id INTEGER,
    documento TEXT,
    nombre_completo TEXT,
    convocado INTEGER DEFAULT 1,
    asistio INTEGER DEFAULT 0,
    firma_estado TEXT DEFAULT 'PENDIENTE',
    observaciones TEXT,
    creado_por INTEGER,
    fecha_creacion TEXT NOT NULL,
    actualizado_por INTEGER,
    fecha_actualizacion TEXT,
    FOREIGN KEY (actividad_id) REFERENCES sn_actividades_integrales(id),
    FOREIGN KEY (expediente_id) REFERENCES sn_expedientes_integrales(id),
    UNIQUE(fundacion_id, actividad_id, documento)
);
CREATE INDEX IF NOT EXISTS idx_sn_act_part_actividad ON sn_actividad_participantes(fundacion_id, actividad_id);

CREATE TABLE IF NOT EXISTS sn_productos_actividad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL DEFAULT 1,
    actividad_id INTEGER,
    expediente_id INTEGER,
    tipo_producto TEXT NOT NULL,
    nombre_archivo TEXT NOT NULL,
    ruta_archivo TEXT NOT NULL,
    mime_type TEXT,
    tamano_bytes INTEGER DEFAULT 0,
    sha256 TEXT,
    plantilla_codigo TEXT,
    plantilla_version TEXT,
    estado TEXT DEFAULT 'BORRADOR',
    generado_por INTEGER,
    fecha_generacion TEXT NOT NULL,
    revisado_por INTEGER,
    fecha_revision TEXT,
    aprobado_por INTEGER,
    fecha_aprobacion TEXT,
    observaciones TEXT,
    activo INTEGER DEFAULT 1,
    FOREIGN KEY (actividad_id) REFERENCES sn_actividades_integrales(id),
    FOREIGN KEY (expediente_id) REFERENCES sn_expedientes_integrales(id)
);
CREATE INDEX IF NOT EXISTS idx_sn_producto_actividad ON sn_productos_actividad(fundacion_id, actividad_id, activo);
CREATE INDEX IF NOT EXISTS idx_sn_producto_expediente ON sn_productos_actividad(fundacion_id, expediente_id, activo);

CREATE TABLE IF NOT EXISTS sn_canalizaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL DEFAULT 1,
    expediente_id INTEGER NOT NULL,
    valoracion_id INTEGER,
    alerta_id INTEGER,
    unidad_nombre TEXT,
    tipo_ruta TEXT NOT NULL,
    motivo TEXT NOT NULL,
    prioridad TEXT DEFAULT 'MEDIA',
    entidad_destino TEXT,
    contacto_entidad TEXT,
    fecha_activacion TEXT NOT NULL,
    fecha_limite TEXT,
    estado TEXT DEFAULT 'ABIERTA',
    responsable_id INTEGER,
    responsable_nombre TEXT,
    resultado_cierre TEXT,
    evidencia_cierre TEXT,
    fecha_cierre TEXT,
    cerrado_por INTEGER,
    creado_por INTEGER,
    fecha_creacion TEXT NOT NULL,
    actualizado_por INTEGER,
    fecha_actualizacion TEXT,
    FOREIGN KEY (expediente_id) REFERENCES sn_expedientes_integrales(id),
    FOREIGN KEY (valoracion_id) REFERENCES sn_valoraciones(id),
    FOREIGN KEY (alerta_id) REFERENCES sn_alertas(id)
);
CREATE INDEX IF NOT EXISTS idx_sn_canalizacion_estado ON sn_canalizaciones(fundacion_id, estado, prioridad);
CREATE INDEX IF NOT EXISTS idx_sn_canalizacion_expediente ON sn_canalizaciones(fundacion_id, expediente_id);

CREATE TABLE IF NOT EXISTS sn_seguimientos_integrales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL DEFAULT 1,
    entidad_tipo TEXT NOT NULL,
    entidad_id INTEGER NOT NULL,
    fecha_seguimiento TEXT NOT NULL,
    actuacion TEXT NOT NULL,
    resultado TEXT,
    proximo_seguimiento TEXT,
    responsable_id INTEGER,
    responsable_nombre TEXT,
    evidencia_referencia TEXT,
    creado_por INTEGER,
    fecha_creacion TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sn_seg_integral_entidad ON sn_seguimientos_integrales(fundacion_id, entidad_tipo, entidad_id);
CREATE INDEX IF NOT EXISTS idx_sn_seg_integral_proximo ON sn_seguimientos_integrales(fundacion_id, proximo_seguimiento);

CREATE TABLE IF NOT EXISTS sn_evidencias_integrales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL DEFAULT 1,
    actividad_id INTEGER,
    canalizacion_id INTEGER,
    expediente_id INTEGER,
    tipo TEXT DEFAULT 'SOPORTE',
    titulo TEXT,
    nombre_original TEXT NOT NULL,
    nombre_guardado TEXT NOT NULL,
    ruta_archivo TEXT NOT NULL,
    mime_type TEXT,
    tamano_bytes INTEGER DEFAULT 0,
    sha256 TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    activo INTEGER DEFAULT 1,
    cargado_por INTEGER,
    fecha_carga TEXT NOT NULL,
    FOREIGN KEY (actividad_id) REFERENCES sn_actividades_integrales(id),
    FOREIGN KEY (canalizacion_id) REFERENCES sn_canalizaciones(id),
    FOREIGN KEY (expediente_id) REFERENCES sn_expedientes_integrales(id)
);
CREATE INDEX IF NOT EXISTS idx_sn_evidencia_actividad ON sn_evidencias_integrales(fundacion_id, actividad_id, activo);
CREATE INDEX IF NOT EXISTS idx_sn_evidencia_canalizacion ON sn_evidencias_integrales(fundacion_id, canalizacion_id, activo);

CREATE TABLE IF NOT EXISTS sn_periodos_mensuales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    anio_mes TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'BORRADOR',
    temas_json TEXT NOT NULL DEFAULT '[]',
    variables_json TEXT NOT NULL DEFAULT '{}',
    observaciones TEXT,
    creado_por INTEGER,
    fecha_creacion TEXT NOT NULL,
    actualizado_por INTEGER,
    fecha_actualizacion TEXT NOT NULL,
    aprobado_por INTEGER,
    fecha_aprobacion TEXT,
    bloqueado_en TEXT,
    integridad_sha256 TEXT,
    UNIQUE(fundacion_id, anio_mes)
);
CREATE INDEX IF NOT EXISTS idx_sn_periodos_scope ON sn_periodos_mensuales(fundacion_id, anio_mes, estado);

CREATE TABLE IF NOT EXISTS sn_informes_mensuales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    periodo_id INTEGER NOT NULL,
    formato TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    nombre_archivo TEXT NOT NULL,
    ruta_archivo TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    tamano_bytes INTEGER NOT NULL DEFAULT 0,
    sha256 TEXT NOT NULL,
    plantilla_codigo TEXT NOT NULL DEFAULT 'SN-MENSUAL',
    plantilla_version TEXT NOT NULL DEFAULT 'INTERNA-1',
    estado TEXT NOT NULL DEFAULT 'GENERADO',
    generado_por INTEGER,
    fecha_generacion TEXT NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (periodo_id) REFERENCES sn_periodos_mensuales(id),
    UNIQUE(fundacion_id, periodo_id, formato, version)
);
CREATE INDEX IF NOT EXISTS idx_sn_informes_scope ON sn_informes_mensuales(fundacion_id, periodo_id, activo);

CREATE TABLE IF NOT EXISTS sn_actas_institucionales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    actividad_id INTEGER,
    anio INTEGER NOT NULL,
    consecutivo INTEGER NOT NULL,
    numero_acta TEXT NOT NULL,
    fecha TEXT NOT NULL,
    lugar TEXT,
    tema TEXT NOT NULL,
    puntos_json TEXT NOT NULL DEFAULT '[]',
    decisiones_json TEXT NOT NULL DEFAULT '[]',
    estado TEXT NOT NULL DEFAULT 'BORRADOR',
    creado_por INTEGER,
    fecha_creacion TEXT NOT NULL,
    actualizado_por INTEGER,
    fecha_actualizacion TEXT NOT NULL,
    cerrado_por INTEGER,
    fecha_cierre TEXT,
    integridad_sha256 TEXT,
    producto_id INTEGER,
    FOREIGN KEY (actividad_id) REFERENCES sn_actividades_integrales(id),
    FOREIGN KEY (producto_id) REFERENCES sn_productos_actividad(id),
    UNIQUE(fundacion_id, anio, consecutivo),
    UNIQUE(fundacion_id, numero_acta)
);
CREATE INDEX IF NOT EXISTS idx_sn_actas_scope ON sn_actas_institucionales(fundacion_id, anio, estado);

CREATE TABLE IF NOT EXISTS sn_acta_tareas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    acta_id INTEGER NOT NULL,
    descripcion TEXT NOT NULL,
    responsable_id INTEGER,
    responsable_nombre TEXT NOT NULL,
    fecha_limite TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'PENDIENTE',
    creado_por INTEGER,
    fecha_creacion TEXT NOT NULL,
    actualizado_por INTEGER,
    fecha_actualizacion TEXT NOT NULL,
    FOREIGN KEY (acta_id) REFERENCES sn_actas_institucionales(id)
);
CREATE INDEX IF NOT EXISTS idx_sn_acta_tareas_scope ON sn_acta_tareas(fundacion_id, acta_id, estado, fecha_limite);
"""
