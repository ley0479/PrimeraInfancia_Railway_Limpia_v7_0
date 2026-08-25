# Herramientas de LÍA

La primera versión contiene exclusivamente herramientas de lectura:

- `get_pending_activities_summary`: resumen y máximo cinco actividades del usuario.
- `get_document_processing_status`: estado y diagnóstico de un documento del tenant.
- `get_format_generation_status`: confirma estado, archivo y disponibilidad de descarga.
- `get_structured_error`: explica únicamente códigos del catálogo.

El registro rechaza cualquier nombre no incluido. Los IDs se validan y las
consultas filtran por la fundación obtenida de la sesión. No existen SQL libre,
comandos, URLs arbitrarias ni herramientas de escritura.
