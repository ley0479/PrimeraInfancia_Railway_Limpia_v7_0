"""Esquema del módulo Reportes Gerenciales Profesionales.

Tablas con prefijo rg_ para no interferir con módulos previos.
"""

RG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS rg_reportes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER DEFAULT 1,
    usuario_id INTEGER,
    periodo TEXT NOT NULL,
    mes INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    tipo TEXT DEFAULT 'MENSUAL',
    titulo TEXT,
    estado TEXT DEFAULT 'GENERADO',
    resumen_ejecutivo TEXT,
    indicadores_json TEXT,
    hallazgos_json TEXT,
    alertas_json TEXT,
    recomendaciones_json TEXT,
    pendientes_json TEXT,
    responsables_json TEXT,
    conclusion TEXT,
    ruta_pdf TEXT,
    ruta_excel TEXT,
    nombre_pdf TEXT,
    nombre_excel TEXT,
    total_indicadores INTEGER DEFAULT 0,
    total_hallazgos INTEGER DEFAULT 0,
    total_alertas INTEGER DEFAULT 0,
    total_pendientes INTEGER DEFAULT 0,
    fecha_generacion TEXT NOT NULL,
    fecha_actualizacion TEXT
);

CREATE TABLE IF NOT EXISTS rg_auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporte_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    usuario_id INTEGER,
    accion TEXT NOT NULL,
    detalle TEXT,
    datos_json TEXT,
    fecha TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rg_configuracion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER DEFAULT 1,
    clave TEXT NOT NULL,
    valor TEXT,
    fecha_creacion TEXT NOT NULL,
    fecha_actualizacion TEXT,
    UNIQUE(fundacion_id, clave)
);

CREATE TABLE IF NOT EXISTS rg9_informes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    contrato TEXT,
    periodo TEXT NOT NULL,
    mes INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    fecha_corte TEXT,
    cobertura_contratada INTEGER DEFAULT 0,
    modalidad TEXT,
    estado TEXT DEFAULT 'BORRADOR',
    version INTEGER DEFAULT 1,
    responsable_id INTEGER,
    creado_en TEXT NOT NULL,
    actualizado_en TEXT,
    aprobado_en TEXT,
    UNIQUE(fundacion_id, contrato, periodo, version)
);

CREATE TABLE IF NOT EXISTS rg9_resultados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    informe_id INTEGER NOT NULL,
    atencion_codigo TEXT NOT NULL,
    numerador INTEGER DEFAULT 0,
    denominador INTEGER DEFAULT 0,
    porcentaje REAL DEFAULT 0,
    estado TEXT DEFAULT 'PENDIENTE',
    fuente TEXT,
    fecha_actualizacion TEXT,
    observacion TEXT,
    datos_json TEXT,
    responsable TEXT,
    UNIQUE(informe_id, atencion_codigo)
);

CREATE TABLE IF NOT EXISTS rg9_hallazgos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    informe_id INTEGER NOT NULL,
    atencion_codigo TEXT,
    codigo TEXT NOT NULL,
    nivel TEXT DEFAULT 'ADVERTENCIA',
    mensaje TEXT NOT NULL,
    accion TEXT,
    responsable TEXT,
    fecha_limite TEXT,
    estado TEXT DEFAULT 'ABIERTO',
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rg9_evidencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    informe_id INTEGER NOT NULL,
    atencion_codigo TEXT NOT NULL,
    unidad TEXT,
    nombre_archivo TEXT NOT NULL,
    ruta_archivo TEXT NOT NULL,
    fecha_evidencia TEXT,
    responsable TEXT,
    estado_revision TEXT DEFAULT 'PENDIENTE',
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rg9_plantillas_pptx (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    nombre_original TEXT NOT NULL,
    ruta_archivo TEXT NOT NULL,
    version TEXT,
    fecha_vigencia TEXT,
    estado TEXT DEFAULT 'ACTIVA',
    hash_sha256 TEXT NOT NULL,
    cargado_por INTEGER,
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rg9_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    informe_id INTEGER NOT NULL,
    fundacion_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    datos_json TEXT NOT NULL,
    hash_sha256 TEXT NOT NULL,
    creado_en TEXT NOT NULL,
    UNIQUE(informe_id, version)
);

CREATE INDEX IF NOT EXISTS idx_rg9_informes_tenant_periodo
ON rg9_informes(fundacion_id, periodo);
CREATE INDEX IF NOT EXISTS idx_rg9_resultados_informe
ON rg9_resultados(informe_id, atencion_codigo);
CREATE INDEX IF NOT EXISTS idx_rg9_evidencias_informe
ON rg9_evidencias(informe_id, atencion_codigo);
CREATE INDEX IF NOT EXISTS idx_rg9_plantillas_tenant_estado
ON rg9_plantillas_pptx(fundacion_id, estado);
"""
