"""Política única de lectura de la Base Maestra publicada.

Los módulos operativos conservan sus propias transacciones, pero cualquier dato
institucional compartido (participante, unidad o talento humano) debe resolverse
desde las tablas ``master_*`` cuando existe una versión publicada. Las tablas
históricas solo son compatibles con instalaciones que aún no han publicado una
Base Maestra.
"""

from __future__ import annotations

from typing import Any


class MasterDataProvider:
    PARTICIPANT_TABLE = "master_ninos"
    LEGACY_PARTICIPANT_TABLES = frozenset({"beneficiarios", "usuarios"})

    @staticmethod
    def _table_exists(conn: Any, table: str) -> bool:
        try:
            conn.execute(f'SELECT 1 FROM "{table}" WHERE 1=0')
            return True
        except Exception:
            return False

    @classmethod
    def has_published_version(cls, conn: Any, foundation_id: int) -> bool:
        if not cls._table_exists(conn, "master_versiones"):
            return False
        return bool(
            conn.execute(
                "SELECT 1 FROM master_versiones WHERE fundacion_id=? AND activa=1 LIMIT 1",
                (int(foundation_id),),
            ).fetchone()
        )

    @classmethod
    def allowed_participant_source(cls, conn: Any, foundation_id: int, requested: str | None) -> str | None:
        """Devuelve la fuente permitida bajo la política institucional.

        Con una versión publicada nunca autoriza una lectura nueva desde tablas
        heredadas. Estas referencias solo pueden utilizarse para obtener el
        documento y promoverlo inmediatamente al registro maestro vigente.
        """
        source = str(requested or cls.PARTICIPANT_TABLE).strip().lower()
        if source == cls.PARTICIPANT_TABLE:
            return source if cls._table_exists(conn, source) else None
        if source in cls.LEGACY_PARTICIPANT_TABLES:
            if cls.has_published_version(conn, foundation_id):
                return None
            return source if cls._table_exists(conn, source) else None
        return None

    @classmethod
    def participant_by_document(cls, conn: Any, foundation_id: int, document: Any) -> dict[str, Any] | None:
        value = str(document or "").strip()
        if not value or not cls._table_exists(conn, cls.PARTICIPANT_TABLE):
            return None
        row = conn.execute(
            """SELECT * FROM master_ninos
               WHERE fundacion_id=? AND activo=1 AND TRIM(COALESCE(documento,''))=?
               ORDER BY id DESC LIMIT 1""",
            (int(foundation_id), value),
        ).fetchone()
        return dict(row) if row else None

    @classmethod
    def participant_by_id(cls, conn: Any, foundation_id: int, participant_id: int) -> dict[str, Any] | None:
        if not cls._table_exists(conn, cls.PARTICIPANT_TABLE):
            return None
        row = conn.execute(
            "SELECT * FROM master_ninos WHERE fundacion_id=? AND activo=1 AND id=? LIMIT 1",
            (int(foundation_id), int(participant_id)),
        ).fetchone()
        return dict(row) if row else None

    @classmethod
    def resolve_historical_participant(
        cls,
        conn: Any,
        foundation_id: int,
        source: str | None,
        participant_id: int,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Resuelve referencias históricas sin mostrar datos heredados obsoletos."""
        requested = str(source or cls.PARTICIPANT_TABLE).strip().lower()
        if requested == cls.PARTICIPANT_TABLE:
            return cls.participant_by_id(conn, foundation_id, participant_id), cls.PARTICIPANT_TABLE

        if requested not in cls.LEGACY_PARTICIPANT_TABLES or not cls._table_exists(conn, requested):
            return None, None

        row = conn.execute(
            f'SELECT * FROM "{requested}" WHERE id=? AND COALESCE(fundacion_id,1)=? LIMIT 1',
            (int(participant_id), int(foundation_id)),
        ).fetchone()
        legacy = dict(row) if row else None
        if not legacy:
            return None, None
        document = next(
            (legacy.get(key) for key in ("documento", "numero_documento", "identificacion", "num_documento") if legacy.get(key)),
            None,
        )
        canonical = cls.participant_by_document(conn, foundation_id, document)
        if canonical:
            return canonical, cls.PARTICIPANT_TABLE
        if cls.has_published_version(conn, foundation_id):
            return None, None
        return legacy, requested
