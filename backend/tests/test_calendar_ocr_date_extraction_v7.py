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

poster_text = """
Entrega de cuentas de cobro
Miércoles
16 de septiembre
de 2026
Entrega de informe
Viernes
25 de septiembre
de 2026
Socialización de los servicios
25 de septiembre
de 2026
"""
poster_rows = _dataframe_from_plain_text(poster_text).to_dict("records")
assert [row["Fecha"] for row in poster_rows] == ["2026-09-16", "2026-09-25", "2026-09-25"]
assert poster_rows[0]["Actividad"] == "Entrega de cuentas de cobro"
assert poster_rows[1]["Actividad"] == "Entrega de informe"
assert poster_rows[2]["Actividad"] == "Socialización de los servicios"

noisy_text = """
<< / =— Entrega de informe == A
4 A (Y) 25 de septiembre «iD
de 2026
Socialización
P=X=
de los servicios ha ai sat
A 25 de septiembre |
de 2026
"""
noisy_rows = _dataframe_from_plain_text(noisy_text).to_dict("records")
assert [row["Fecha"] for row in noisy_rows] == ["2026-09-25", "2026-09-25"]
assert "Entrega de informe" in noisy_rows[0]["Actividad"]
assert "Socialización" in noisy_rows[1]["Actividad"]

production_ocr = """
Entrega de cuentas de cobro
e Y - A 16 de septiembre es
E x de2026 A
Entrega de informe
lá 4 — 25 de septiembre Zz ——
a de2026  “», —
Socialización
de los servicios
A 25 de septiembre ES
A de 2026 nines yo
"""
production_rows = _dataframe_from_plain_text(production_ocr).to_dict("records")
assert [row["Fecha"] for row in production_rows] == ["2026-09-16", "2026-09-25", "2026-09-25"]

print("CALENDAR_OCR_DATE_EXTRACTION_V7_PASS")
