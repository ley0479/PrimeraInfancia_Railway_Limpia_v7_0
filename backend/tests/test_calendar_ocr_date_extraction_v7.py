from modules.calendario_inteligente.services import _dataframe_from_plain_text


text = """
Entrega del informe de seguimiento 15 de septiembre de 2026
24/09/2026 Reunión de cierre mensual
Jornada de salud nutricional
30.09.2026
"""
frame = _dataframe_from_plain_text(text)
rows = frame.to_dict("records")

assert [row["Fecha"] for row in rows] == ["2026-09-15", "2026-09-24", "2026-09-30"]
assert "informe de seguimiento" in rows[0]["Actividad"].lower()
assert "reunión de cierre" in rows[1]["Actividad"].lower()
assert rows[2]["Actividad"] == "Jornada de salud nutricional"

print("CALENDAR_OCR_DATE_EXTRACTION_V7_PASS")
