from __future__ import annotations

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS corporaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER,
    nombre TEXT NOT NULL,
    nit TEXT,
    representante TEXT,
    estado TEXT DEFAULT 'ACTIVA',
    fecha_creacion TEXT NOT NULL,
    fecha_actualizacion TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_corporaciones_fundacion ON corporaciones(fundacion_id) WHERE fundacion_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_corporaciones_estado ON corporaciones(estado);

CREATE TABLE IF NOT EXISTS cargas_archivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_fuente TEXT NOT NULL,
    nombre_archivo_original TEXT,
    nombre_archivo_guardado TEXT,
    ruta_archivo TEXT,
    extension TEXT,
    fecha_carga TEXT NOT NULL,
    usuario_id INTEGER,
    usuario TEXT,
    corporacion_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    total_registros INTEGER DEFAULT 0,
    registros_validos INTEGER DEFAULT 0,
    registros_error INTEGER DEFAULT 0,
    estado TEXT DEFAULT 'cargado',
    columnas_json TEXT,
    errores_json TEXT,
    metadata_json TEXT,
    fecha_actualizacion TEXT
);

CREATE INDEX IF NOT EXISTS idx_cargas_archivos_fuente ON cargas_archivos(tipo_fuente, fundacion_id, fecha_carga);
CREATE INDEX IF NOT EXISTS idx_cargas_archivos_estado ON cargas_archivos(estado);

CREATE TABLE IF NOT EXISTS staging_cuentame (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    carga_id INTEGER NOT NULL,
    fila INTEGER,
    documento TEXT,
    tipo_documento TEXT,
    nombres TEXT,
    apellidos TEXT,
    nombre_completo TEXT,
    fecha_nacimiento TEXT,
    edad_meses INTEGER,
    grupo_etario TEXT,
    sexo TEXT,
    estado TEXT,
    fecha_ingreso TEXT,
    fecha_retiro TEXT,
    unidad_servicio TEXT,
    codigo_unidad TEXT,
    coordinador TEXT,
    docente TEXT,
    modalidad TEXT,
    corporacion_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    datos_json TEXT,
    errores_json TEXT,
    fecha_creacion TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_staging_cuentame_carga ON staging_cuentame(carga_id);
CREATE INDEX IF NOT EXISTS idx_staging_cuentame_doc ON staging_cuentame(fundacion_id, documento);
CREATE INDEX IF NOT EXISTS idx_staging_cuentame_unidad ON staging_cuentame(fundacion_id, unidad_servicio);

CREATE TABLE IF NOT EXISTS staging_talento_humano (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    carga_id INTEGER NOT NULL,
    fila INTEGER,
    documento TEXT,
    tipo_documento TEXT,
    nombres TEXT,
    apellidos TEXT,
    nombre_completo TEXT,
    cargo TEXT,
    rol_normalizado TEXT,
    unidad_servicio TEXT,
    coordinador TEXT,
    telefono TEXT,
    correo TEXT,
    estado TEXT,
    corporacion_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    datos_json TEXT,
    errores_json TEXT,
    fecha_creacion TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_staging_th_carga ON staging_talento_humano(carga_id);
CREATE INDEX IF NOT EXISTS idx_staging_th_doc ON staging_talento_humano(fundacion_id, documento);
CREATE INDEX IF NOT EXISTS idx_staging_th_unidad ON staging_talento_humano(fundacion_id, unidad_servicio);

CREATE TABLE IF NOT EXISTS staging_salud_nutricion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    carga_id INTEGER NOT NULL,
    fila INTEGER,
    documento TEXT,
    tipo_documento TEXT,
    nombres TEXT,
    apellidos TEXT,
    nombre_completo TEXT,
    unidad_servicio TEXT,
    coordinador TEXT,
    peso REAL,
    talla REAL,
    perimetro_braquial REAL,
    diagnostico_nutricional TEXT,
    estado_nutricional TEXT,
    carne_salud TEXT,
    control_crecimiento TEXT,
    carne_crecimiento TEXT,
    vacunas TEXT,
    fecha_toma TEXT,
    observaciones TEXT,
    alertas_json TEXT,
    corporacion_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    datos_json TEXT,
    errores_json TEXT,
    fecha_creacion TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_staging_sn_carga ON staging_salud_nutricion(carga_id);
CREATE INDEX IF NOT EXISTS idx_staging_sn_doc ON staging_salud_nutricion(fundacion_id, documento);
CREATE INDEX IF NOT EXISTS idx_staging_sn_unidad ON staging_salud_nutricion(fundacion_id, unidad_servicio);

CREATE TABLE IF NOT EXISTS validaciones_cargas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    carga_id INTEGER,
    tipo_fuente TEXT,
    fundacion_id INTEGER DEFAULT 1,
    corporacion_id INTEGER,
    estado TEXT DEFAULT 'pendiente',
    semaforo TEXT DEFAULT 'ROJO',
    total_registros INTEGER DEFAULT 0,
    registros_validos INTEGER DEFAULT 0,
    registros_error INTEGER DEFAULT 0,
    errores_criticos INTEGER DEFAULT 0,
    advertencias INTEGER DEFAULT 0,
    duplicados INTEGER DEFAULT 0,
    calidad_porcentaje REAL DEFAULT 0,
    reporte_json TEXT,
    recomendaciones_json TEXT,
    fecha_validacion TEXT NOT NULL,
    usuario_id INTEGER,
    usuario TEXT
);

CREATE INDEX IF NOT EXISTS idx_validaciones_carga ON validaciones_cargas(carga_id);
CREATE INDEX IF NOT EXISTS idx_validaciones_fundacion ON validaciones_cargas(fundacion_id, fecha_validacion);

CREATE TABLE IF NOT EXISTS master_versiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_numero INTEGER NOT NULL,
    corporacion_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    estado TEXT DEFAULT 'BORRADOR',
    activa INTEGER DEFAULT 0,
    fecha_creacion TEXT NOT NULL,
    fecha_publicacion TEXT,
    usuario_id INTEGER,
    usuario TEXT,
    cargas_json TEXT,
    resumen_json TEXT,
    errores_criticos INTEGER DEFAULT 0,
    advertencias INTEGER DEFAULT 0,
    calidad_porcentaje REAL DEFAULT 0,
    observaciones TEXT
);

CREATE INDEX IF NOT EXISTS idx_master_versiones_fundacion ON master_versiones(fundacion_id, estado, activa);
CREATE UNIQUE INDEX IF NOT EXISTS idx_master_version_activa ON master_versiones(fundacion_id, activa) WHERE activa = 1;

CREATE TABLE IF NOT EXISTS master_ninos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL,
    activo INTEGER DEFAULT 0,
    documento TEXT NOT NULL,
    tipo_documento TEXT,
    nombres TEXT,
    apellidos TEXT,
    nombre_completo TEXT,
    fecha_nacimiento TEXT,
    edad_meses INTEGER,
    grupo_etario TEXT,
    sexo TEXT,
    estado TEXT,
    fecha_ingreso TEXT,
    fecha_retiro TEXT,
    unidad_servicio TEXT,
    codigo_unidad TEXT,
    coordinador TEXT,
    docente TEXT,
    modalidad TEXT,
    peso REAL,
    talla REAL,
    perimetro_braquial REAL,
    diagnostico_nutricional TEXT,
    estado_nutricional TEXT,
    carne_salud TEXT,
    control_crecimiento TEXT,
    carne_crecimiento TEXT,
    vacunas TEXT,
    alertas_json TEXT,
    fuente_cuentame_carga_id INTEGER,
    fuente_nutricion_carga_id INTEGER,
    fuente_talento_carga_id INTEGER,
    fuente_original TEXT,
    archivo_origen TEXT,
    corporacion_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    estado_validacion TEXT DEFAULT 'VALIDADO',
    fecha_carga TEXT,
    fecha_consolidacion TEXT NOT NULL,
    usuario_consolida TEXT,
    datos_json TEXT,
    fecha_actualizacion TEXT
);

CREATE INDEX IF NOT EXISTS idx_master_ninos_version ON master_ninos(version_id, activo);
CREATE INDEX IF NOT EXISTS idx_master_ninos_doc ON master_ninos(fundacion_id, documento, activo);
CREATE INDEX IF NOT EXISTS idx_master_ninos_unidad ON master_ninos(fundacion_id, unidad_servicio, activo);
CREATE INDEX IF NOT EXISTS idx_master_ninos_coord ON master_ninos(fundacion_id, coordinador, activo);
CREATE UNIQUE INDEX IF NOT EXISTS idx_master_ninos_unique_version_doc ON master_ninos(version_id, fundacion_id, documento);

CREATE TABLE IF NOT EXISTS master_salud_nutricion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL,
    activo INTEGER DEFAULT 0,
    documento TEXT NOT NULL,
    peso REAL,
    talla REAL,
    perimetro_braquial REAL,
    diagnostico_nutricional TEXT,
    estado_nutricional TEXT,
    carne_salud TEXT,
    control_crecimiento TEXT,
    carne_crecimiento TEXT,
    vacunas TEXT,
    fecha_toma TEXT,
    observaciones TEXT,
    alertas_json TEXT,
    fuente_carga_id INTEGER,
    corporacion_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    fecha_consolidacion TEXT NOT NULL,
    datos_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_master_salud_doc ON master_salud_nutricion(fundacion_id, documento, activo);

CREATE TABLE IF NOT EXISTS master_talento_humano (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL,
    activo INTEGER DEFAULT 0,
    documento TEXT,
    tipo_documento TEXT,
    nombres TEXT,
    apellidos TEXT,
    nombre_completo TEXT,
    cargo TEXT,
    rol_normalizado TEXT,
    unidad_servicio TEXT,
    coordinador TEXT,
    telefono TEXT,
    correo TEXT,
    estado TEXT,
    fuente_carga_id INTEGER,
    corporacion_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    fecha_consolidacion TEXT NOT NULL,
    datos_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_master_th_unidad ON master_talento_humano(fundacion_id, unidad_servicio, activo);
CREATE INDEX IF NOT EXISTS idx_master_th_doc ON master_talento_humano(fundacion_id, documento, activo);

CREATE TABLE IF NOT EXISTS master_unidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL,
    activo INTEGER DEFAULT 0,
    nombre TEXT NOT NULL,
    codigo_unidad TEXT,
    coordinador TEXT,
    total_ninos INTEGER DEFAULT 0,
    total_talento INTEGER DEFAULT 0,
    modalidad TEXT,
    corporacion_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    fecha_consolidacion TEXT NOT NULL,
    datos_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_master_unidades_nombre ON master_unidades(fundacion_id, nombre, activo);
CREATE UNIQUE INDEX IF NOT EXISTS idx_master_unidades_unique_version_nombre ON master_unidades(version_id, fundacion_id, nombre);

CREATE TABLE IF NOT EXISTS master_inconsistencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER,
    carga_id INTEGER,
    tipo_fuente TEXT,
    severidad TEXT DEFAULT 'ADVERTENCIA',
    tipo TEXT,
    documento TEXT,
    nombre TEXT,
    unidad_servicio TEXT,
    campo TEXT,
    descripcion TEXT NOT NULL,
    valor_1 TEXT,
    valor_2 TEXT,
    resuelta INTEGER DEFAULT 0,
    usuario_resuelve TEXT,
    fecha_resuelve TEXT,
    datos_json TEXT,
    corporacion_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    fecha_creacion TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_master_incons_version ON master_inconsistencias(version_id, severidad, resuelta);
CREATE INDEX IF NOT EXISTS idx_master_incons_carga ON master_inconsistencias(carga_id, severidad, resuelta);

CREATE TABLE IF NOT EXISTS master_historial_cambios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER,
    documento TEXT,
    campo TEXT NOT NULL,
    valor_anterior TEXT,
    valor_nuevo TEXT,
    tipo_movimiento TEXT,
    fuente_cambio TEXT,
    archivo_origen TEXT,
    usuario TEXT,
    corporacion_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    fecha_cambio TEXT NOT NULL,
    datos_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_master_historial_doc ON master_historial_cambios(fundacion_id, documento, fecha_cambio);
CREATE INDEX IF NOT EXISTS idx_master_historial_version ON master_historial_cambios(version_id, tipo_movimiento);

CREATE TABLE IF NOT EXISTS master_movimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER,
    tipo_movimiento TEXT NOT NULL,
    documento TEXT,
    nombre TEXT,
    unidad_anterior TEXT,
    unidad_nueva TEXT,
    coordinador_anterior TEXT,
    coordinador_nuevo TEXT,
    estado_anterior TEXT,
    estado_nuevo TEXT,
    diagnostico_anterior TEXT,
    diagnostico_nuevo TEXT,
    detalle TEXT,
    corporacion_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    fecha_movimiento TEXT NOT NULL,
    datos_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_master_movimientos_version ON master_movimientos(version_id, tipo_movimiento);
CREATE INDEX IF NOT EXISTS idx_master_movimientos_doc ON master_movimientos(fundacion_id, documento);

CREATE TABLE IF NOT EXISTS master_publicaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL,
    version_anterior_id INTEGER,
    corporacion_id INTEGER,
    fundacion_id INTEGER DEFAULT 1,
    usuario_id INTEGER,
    usuario TEXT,
    estado TEXT DEFAULT 'PUBLICADA',
    resumen_json TEXT,
    fecha_publicacion TEXT NOT NULL,
    observaciones TEXT
);

CREATE INDEX IF NOT EXISTS idx_master_publicaciones_fundacion ON master_publicaciones(fundacion_id, fecha_publicacion);

CREATE TABLE IF NOT EXISTS master_projection_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    version_id INTEGER NOT NULL,
    modulo TEXT NOT NULL,
    estado TEXT NOT NULL,
    total_registros INTEGER DEFAULT 0,
    detalle_json TEXT,
    error TEXT,
    fecha_actualizacion TEXT NOT NULL,
    UNIQUE(fundacion_id, version_id, modulo)
);

CREATE INDEX IF NOT EXISTS idx_master_projection_status_version
ON master_projection_status(fundacion_id, version_id, estado);
"""
