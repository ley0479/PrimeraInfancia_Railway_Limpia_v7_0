SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ayuda_progreso_usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    modulo TEXT NOT NULL,
    recorrido_completado INTEGER DEFAULT 0,
    recorrido_omitido INTEGER DEFAULT 0,
    veces_abierto INTEGER DEFAULT 0,
    ultima_apertura TEXT,
    fecha_creacion TEXT NOT NULL,
    fecha_actualizacion TEXT,
    UNIQUE (fundacion_id, usuario_id, modulo)
);
CREATE INDEX IF NOT EXISTS idx_ayuda_progreso_usuario
ON ayuda_progreso_usuario(fundacion_id, usuario_id, modulo);
CREATE TABLE IF NOT EXISTS lia_audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    modulo TEXT,
    tool_name TEXT,
    success INTEGER DEFAULT 1,
    request_id TEXT,
    metadata_redacted TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lia_audit_tenant_user_date
ON lia_audit_events(fundacion_id, usuario_id, created_at);
"""
