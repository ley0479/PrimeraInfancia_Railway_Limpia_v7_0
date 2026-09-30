from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

from openpyxl import load_workbook

from modules.componente_psicosocial.f23_service import F23Service
from modules.dbapi_compat import sqlite3


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        database = root / "f23.sqlite3"
        with sqlite3.connect(str(database)) as conn:
            conn.executescript("""
            CREATE TABLE master_ninos(
              id INTEGER PRIMARY KEY, fundacion_id INTEGER, activo INTEGER,
              documento TEXT,tipo_documento TEXT,nombres TEXT,apellidos TEXT,
              nombre_completo TEXT,fecha_nacimiento TEXT,sexo TEXT,
              unidad_servicio TEXT,codigo_unidad TEXT,modalidad TEXT,
              vacunas TEXT,control_crecimiento TEXT,peso REAL,talla REAL,datos_json TEXT
            );
            """)
            conn.execute("INSERT INTO master_ninos VALUES(1,1,1,'001234','RC','ANA','PRUEBA','ANA PRUEBA','2022-03-02','F','UDS PRUEBA','00077','INSTITUCIONAL','SI','SI',15.5,96.2,'{}')")
            conn.execute("INSERT INTO master_ninos VALUES(2,1,1,'009999','RC','LUIS','PRUEBA','LUIS PRUEBA',NULL,'M','UDS PRUEBA','00077','INSTITUCIONAL',NULL,NULL,NULL,NULL,'{}')")
            conn.execute("INSERT INTO master_ninos VALUES(3,2,1,'OTRO','RC','OTRA','FUNDACION','OTRA FUNDACION','2021-01-01','F','UDS PRUEBA','00077','INSTITUCIONAL',NULL,NULL,NULL,NULL,'{}')")
            conn.commit()
        service = F23Service(str(database), str(root / "outputs"))
        service.init_schema()
        config = service.configuration(1)
        require(config["template"]["disponible"] and config["template"]["sha256"] == "5340d3e6bfa9f03a09b1400d89c74d5120a81f76a4aa4ea65bae72688dd64319", "No preservó la plantilla oficial")
        require(config["mapeo"]["campos"] == 283, "No cargó los 283 destinos mapeados")
        session = service.create_session(1, "UDS PRUEBA", "2026-09-30", 7)
        require(session["total_participantes"] == 2 and len(session["participantes"]) == 2, "Mezcló otra fundación o perdió participantes")
        ana = next(item for item in session["participantes"] if item["documento"] == "001234")
        require(service.participant_context(1, ana["id"])["unidad"] == "UDS PRUEBA", "No resolvió el ámbito de unidad del participante")
        try:
            service.participant_context(2, ana["id"])
            raise AssertionError("Otra fundación accedió al participante")
        except LookupError:
            pass
        require(ana["pendientes_total"] > 0, "Inventó respuestas para completar la ficha")
        first_pending = ana["pendientes"][0]
        updated = service.update_participant(1, ana["id"], {"respuestas": {first_pending: "RESPUESTA CONFIRMADA"}, "estados": {first_pending: "CONFIRMADO"}}, 7)
        require(updated["pendientes_total"] == ana["pendientes_total"] - 1, "El guardado parcial no actualizó pendientes")
        blocked = False
        try:
            service.update_participant(1, ana["id"], {"integrantes": [{}] * 11}, 7)
        except ValueError:
            blocked = True
        require(blocked, "Truncó o aceptó silenciosamente más de diez integrantes")
        consolidated = service.generate(1, session["id"], 7)
        individual = service.generate(1, session["id"], 7, ana["id"])
        for generated, expected in ((consolidated, 2), (individual, 1)):
            row = service.generation(1, generated["id"])
            path = Path(row["ruta_archivo"])
            require(path.is_file() and generated["participantes"] == expected, "No generó la salida esperada")
            workbook = load_workbook(path, read_only=True, keep_vba=True)
            require(set(F23Service.REGISTER_SHEETS).issubset(workbook.sheetnames), "La salida perdió hojas oficiales")
            require(str(workbook["BD-M1"]["Q2"].value or "") == "001234", "El documento no llegó al registro como texto")
            if expected == 1:
                require(str(workbook["MODULO 1"]["F18"].value or "") == "001234", "La ficha individual no recibió el documento")
            workbook.close()
            try:
                service.generation(2, generated["id"])
                raise AssertionError("Otra fundación accedió a la generación")
            except LookupError:
                pass
            with zipfile.ZipFile(service.template) as original, zipfile.ZipFile(path) as result:
                require(set(original.namelist()) == set(result.namelist()), "La salida perdió componentes del XLSM")
                for name in original.namelist():
                    if not name.startswith("xl/worksheets/"):
                        require(original.read(name) == result.read(name), f"La salida alteró el componente protegido {name}")
        print("PASS test_caracterizacion_f23_v1")


if __name__ == "__main__":
    main()
