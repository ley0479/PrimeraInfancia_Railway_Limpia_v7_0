# Fase 50 · Presupuesto cuantitativo de rendimiento

Se fijaron límites verificables para consultas administrativas de LIAM:

- máximo de 100 filas por página;
- payload serializado menor o igual a 128 KiB;
- consulta SQLite local sobre 5.000 eventos menor o igual a 2,5 segundos;
- máximo de 30 filas en tarjetas de perfiles, beneficiarios y búsqueda;
- búsqueda universal limitada a 50 resultados por consulta interna.

La prueba utiliza 4.500 registros del tenant activo y 500 de otro tenant, y confirma total, paginación, tamaño, latencia y aislamiento. No hay migración ni cambio funcional. Para rollback, revertir este commit.
