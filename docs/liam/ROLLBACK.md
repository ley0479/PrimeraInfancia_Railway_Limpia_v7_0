# Rollback

Rollback inmediato: establecer `ENABLE_LIAM_ASSISTANT=false`. Si `ENABLE_LIA_ASSISTANT=true`, reaparece la interfaz anterior de LÍA sin cambiar rutas ni datos.

Para revertir código, retirar únicamente enlaces `liam-*`, archivos `frontend/js/liam`, CSS y póster, y las banderas LIAM. No borrar tablas `lia_*`, preferencias, progreso ni auditoría.

