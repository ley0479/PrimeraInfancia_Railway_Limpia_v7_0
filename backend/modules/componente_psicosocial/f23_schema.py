F23_SCHEMA_VERSION = 1

F23_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS f23_sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    unidad TEXT NOT NULL,
    codigo_unidad TEXT,
    fecha_referencia TEXT NOT NULL,
    template_code TEXT NOT NULL DEFAULT 'F23.MO12.PP',
    template_version TEXT NOT NULL DEFAULT '2',
    estado TEXT NOT NULL DEFAULT 'BORRADOR',
    total_participantes INTEGER NOT NULL DEFAULT 0,
    snapshot_hash TEXT NOT NULL,
    creado_por INTEGER,
    revisado_por INTEGER,
    fecha_creacion TEXT NOT NULL,
    fecha_actualizacion TEXT NOT NULL,
    fecha_revision TEXT
);
CREATE INDEX IF NOT EXISTS idx_f23_sesion_tenant_unidad ON f23_sesiones(fundacion_id,unidad,fecha_referencia);

CREATE TABLE IF NOT EXISTS f23_participantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    sesion_id INTEGER NOT NULL,
    participante_id INTEGER NOT NULL,
    documento TEXT,
    nombre_completo TEXT,
    tipo_ficha TEXT NOT NULL DEFAULT 'NN',
    fuente_snapshot_json TEXT NOT NULL,
    respuestas_json TEXT NOT NULL,
    estados_json TEXT NOT NULL,
    pendientes_json TEXT NOT NULL,
    integrantes_json TEXT NOT NULL DEFAULT '[]',
    estado TEXT NOT NULL DEFAULT 'BORRADOR',
    fecha_actualizacion TEXT NOT NULL,
    UNIQUE(fundacion_id,sesion_id,participante_id),
    FOREIGN KEY(sesion_id) REFERENCES f23_sesiones(id)
);
CREATE INDEX IF NOT EXISTS idx_f23_participante_sesion ON f23_participantes(fundacion_id,sesion_id,estado);

CREATE TABLE IF NOT EXISTS f23_generaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    sesion_id INTEGER NOT NULL,
    participante_registro_id INTEGER,
    tipo TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'GENERADO',
    nombre_archivo TEXT NOT NULL,
    ruta_archivo TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    detalle_json TEXT NOT NULL,
    creado_por INTEGER,
    fecha_creacion TEXT NOT NULL,
    FOREIGN KEY(sesion_id) REFERENCES f23_sesiones(id)
);

CREATE TABLE IF NOT EXISTS f23_auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    sesion_id INTEGER,
    participante_registro_id INTEGER,
    usuario_id INTEGER,
    accion TEXT NOT NULL,
    detalle_json TEXT NOT NULL,
    fecha TEXT NOT NULL
);
"""
