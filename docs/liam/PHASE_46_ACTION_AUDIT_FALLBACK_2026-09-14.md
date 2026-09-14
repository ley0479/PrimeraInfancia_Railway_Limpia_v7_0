# Fase 46 · Degradación segura de auditoría auxiliar

La auditoría estructurada de acciones se ejecuta ahora mediante una frontera tolerante a fallos. Si su tabla o almacenamiento auxiliar no está disponible, LIAM registra una advertencia sanitizada y conserva la respuesta real de la operación.

Esto evita el caso peligroso en que una modificación financiera ya aplicada aparezca como fallida solo porque no pudo actualizarse su auditoría, lo que podría inducir una repetición accidental.

No hay migraciones. Se prueba el contrato HTTP eliminando deliberadamente la tabla auxiliar: el evento funcional y la propuesta continúan respondiendo correctamente. Para rollback, revertir este commit.
