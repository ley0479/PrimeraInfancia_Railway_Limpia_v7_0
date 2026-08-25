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
CREATE TABLE IF NOT EXISTS lia_user_preferences (id INTEGER PRIMARY KEY AUTOINCREMENT,fundacion_id INTEGER NOT NULL,usuario_id INTEGER NOT NULL,voice_enabled INTEGER DEFAULT 0,auto_speak_enabled INTEGER DEFAULT 0,muted INTEGER DEFAULT 0,speech_rate REAL DEFAULT 0.95,reduced_motion INTEGER DEFAULT 0,language TEXT DEFAULT 'es-CO',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(fundacion_id,usuario_id));
CREATE TABLE IF NOT EXISTS lia_feedback (id INTEGER PRIMARY KEY AUTOINCREMENT,fundacion_id INTEGER NOT NULL,usuario_id INTEGER NOT NULL,request_id TEXT,rating INTEGER NOT NULL,reason TEXT,module TEXT,created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_lia_feedback_tenant_date ON lia_feedback(fundacion_id, created_at);
CREATE TABLE IF NOT EXISTS elian_platform_tour_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    tour_id TEXT NOT NULL,
    tour_version INTEGER NOT NULL DEFAULT 1,
    current_module_id TEXT,
    current_step INTEGER NOT NULL DEFAULT 0,
    completed_modules_json TEXT NOT NULL DEFAULT '[]',
    skipped_modules_json TEXT NOT NULL DEFAULT '[]',
    pending_modules_json TEXT NOT NULL DEFAULT '[]',
    mode TEXT NOT NULL DEFAULT 'automatic',
    status TEXT NOT NULL DEFAULT 'not_started',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE(fundacion_id, usuario_id, tour_id)
);
CREATE INDEX IF NOT EXISTS idx_elian_tour_tenant_user
ON elian_platform_tour_progress(fundacion_id, usuario_id, updated_at);
CREATE TABLE IF NOT EXISTS elian_visual_configuration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fundacion_id INTEGER NOT NULL,
    assistant_name TEXT NOT NULL DEFAULT 'ELIAN',
    avatar_gender TEXT NOT NULL DEFAULT 'male',
    avatar_variant TEXT NOT NULL DEFAULT 'afro_colombian_institutional',
    skin_tone TEXT NOT NULL DEFAULT 'dark',
    hair_style TEXT NOT NULL DEFAULT 'short_coily',
    clothing_style TEXT NOT NULL DEFAULT 'institutional_vest',
    primary_color TEXT NOT NULL DEFAULT '#123A63',
    secondary_color TEXT NOT NULL DEFAULT '#16C6D8',
    voice_gender TEXT NOT NULL DEFAULT 'male',
    voice_speed REAL NOT NULL DEFAULT 0.95,
    headset_enabled INTEGER NOT NULL DEFAULT 1,
    tablet_enabled INTEGER NOT NULL DEFAULT 1,
    hologram_enabled INTEGER NOT NULL DEFAULT 1,
    animation_enabled INTEGER NOT NULL DEFAULT 1,
    walk_enabled INTEGER NOT NULL DEFAULT 0,
    lip_sync_enabled INTEGER NOT NULL DEFAULT 0,
    motion_level TEXT NOT NULL DEFAULT 'light',
    avatar_asset_path TEXT NOT NULL,
    updated_by INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(fundacion_id)
);
"""
