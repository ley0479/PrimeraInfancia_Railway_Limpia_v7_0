SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS icbf_program_profiles (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 fundacion_id INTEGER NOT NULL,
 codigo TEXT NOT NULL,
 nombre TEXT NOT NULL,
 modalidad TEXT NOT NULL,
 version INTEGER NOT NULL DEFAULT 1,
 estado TEXT NOT NULL DEFAULT 'INACTIVO',
 criterio_orden TEXT,
 configuracion_json TEXT NOT NULL DEFAULT '{}',
 creado_por INTEGER,
 creado_en TEXT NOT NULL,
 actualizado_en TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_icbf_profile_version
 ON icbf_program_profiles(fundacion_id,codigo,version);

CREATE TABLE IF NOT EXISTS icbf_program_loads (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 fundacion_id INTEGER NOT NULL,
 profile_id INTEGER NOT NULL,
 source_import_id INTEGER NOT NULL,
 source_sha256 TEXT NOT NULL,
 snapshot_sha256 TEXT NOT NULL,
 estado TEXT NOT NULL DEFAULT 'BORRADOR',
 total_registros INTEGER NOT NULL DEFAULT 0,
 quality_json TEXT NOT NULL DEFAULT '{}',
 creado_por INTEGER,
 creado_en TEXT NOT NULL,
 actualizado_en TEXT NOT NULL,
 FOREIGN KEY(profile_id) REFERENCES icbf_program_profiles(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_icbf_load_source
 ON icbf_program_loads(fundacion_id,profile_id,source_import_id);

CREATE TABLE IF NOT EXISTS icbf_program_participants (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 fundacion_id INTEGER NOT NULL,
 load_id INTEGER NOT NULL,
 source_row_id INTEGER NOT NULL,
 source_row_number INTEGER NOT NULL,
 participant_key_hash TEXT NOT NULL,
 canonical_json TEXT NOT NULL,
 community_id INTEGER,
 creado_en TEXT NOT NULL,
 actualizado_en TEXT NOT NULL,
 FOREIGN KEY(load_id) REFERENCES icbf_program_loads(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_icbf_participant_source
 ON icbf_program_participants(fundacion_id,load_id,source_row_id);
CREATE INDEX IF NOT EXISTS idx_icbf_participant_community
 ON icbf_program_participants(fundacion_id,load_id,community_id);

CREATE TABLE IF NOT EXISTS icbf_program_communities (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 fundacion_id INTEGER NOT NULL,
 profile_id INTEGER NOT NULL,
 codigo TEXT,
 nombre TEXT NOT NULL,
 nombre_normalizado TEXT NOT NULL,
 version INTEGER NOT NULL DEFAULT 1,
 vigente INTEGER NOT NULL DEFAULT 1,
 creado_por INTEGER,
 creado_en TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_icbf_community_name_version
 ON icbf_program_communities(fundacion_id,profile_id,nombre_normalizado,version);

CREATE TABLE IF NOT EXISTS icbf_program_community_assignments (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 fundacion_id INTEGER NOT NULL,
 load_id INTEGER NOT NULL,
 participant_id INTEGER NOT NULL,
 community_id INTEGER NOT NULL,
 version INTEGER NOT NULL,
 motivo TEXT,
 asignado_por INTEGER,
 creado_en TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_icbf_assignment_version
 ON icbf_program_community_assignments(fundacion_id,load_id,participant_id,version);

CREATE TABLE IF NOT EXISTS icbf_program_audit (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 fundacion_id INTEGER NOT NULL,
 profile_id INTEGER,
 load_id INTEGER,
 usuario_id INTEGER,
 evento TEXT NOT NULL,
 detalle_json TEXT NOT NULL DEFAULT '{}',
 creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS icbf_program_generations (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 fundacion_id INTEGER NOT NULL,
 profile_id INTEGER NOT NULL,
 load_id INTEGER NOT NULL,
 community_id INTEGER NOT NULL,
 formato TEXT NOT NULL,
 periodo TEXT NOT NULL,
 criterio_orden TEXT NOT NULL,
 template_sha256 TEXT NOT NULL,
 request_sha256 TEXT NOT NULL,
 estado TEXT NOT NULL,
 archivos_json TEXT NOT NULL DEFAULT '[]',
 pendientes_json TEXT NOT NULL DEFAULT '[]',
 creado_por INTEGER,
 creado_en TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_icbf_generation_request
 ON icbf_program_generations(fundacion_id,request_sha256);

CREATE TABLE IF NOT EXISTS icbf_program_delivery_points (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 fundacion_id INTEGER NOT NULL,
 profile_id INTEGER NOT NULL,
 codigo TEXT NOT NULL,
 nombre TEXT NOT NULL,
 tipo TEXT NOT NULL,
 direccion TEXT,
 barrio TEXT,
 telefono TEXT,
 responsable TEXT,
 suplente TEXT,
 origen_codigo TEXT,
 origen_nombre TEXT,
 version INTEGER NOT NULL,
 vigente INTEGER NOT NULL DEFAULT 1,
 creado_por INTEGER,
 creado_en TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_icbf_point_version
 ON icbf_program_delivery_points(fundacion_id,profile_id,codigo,version);

CREATE TABLE IF NOT EXISTS icbf_program_activity_links (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 fundacion_id INTEGER NOT NULL,
 profile_id INTEGER NOT NULL,
 load_id INTEGER NOT NULL,
 community_id INTEGER NOT NULL,
 health_activity_id INTEGER NOT NULL,
 delivery_point_id INTEGER,
 periodo TEXT NOT NULL,
 estado TEXT NOT NULL DEFAULT 'VINCULADA',
 creado_por INTEGER,
 creado_en TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_icbf_activity_link
 ON icbf_program_activity_links(fundacion_id,profile_id,health_activity_id,community_id,periodo);

CREATE TABLE IF NOT EXISTS icbf_program_deliveries (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 fundacion_id INTEGER NOT NULL,
 activity_link_id INTEGER NOT NULL,
 participant_id INTEGER NOT NULL,
 modalidad TEXT NOT NULL,
 fecha_entrega TEXT,
 receptor_nombre TEXT,
 receptor_documento TEXT,
 receptor_parentesco TEXT,
 estado TEXT NOT NULL DEFAULT 'BORRADOR',
 request_key TEXT NOT NULL,
 replaces_delivery_id INTEGER,
 confirmado_por INTEGER,
 confirmado_en TEXT,
 creado_por INTEGER,
 creado_en TEXT NOT NULL,
 actualizado_en TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_icbf_delivery_request
 ON icbf_program_deliveries(fundacion_id,request_key);
CREATE INDEX IF NOT EXISTS idx_icbf_delivery_participant
 ON icbf_program_deliveries(fundacion_id,activity_link_id,participant_id,estado);

CREATE TABLE IF NOT EXISTS icbf_program_delivery_items (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 fundacion_id INTEGER NOT NULL,
 delivery_id INTEGER NOT NULL,
 producto TEXT NOT NULL,
 lote TEXT,
 unidades DOUBLE PRECISION,
 unidad_medida TEXT,
 creado_en TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_icbf_delivery_items
 ON icbf_program_delivery_items(fundacion_id,delivery_id);
"""
