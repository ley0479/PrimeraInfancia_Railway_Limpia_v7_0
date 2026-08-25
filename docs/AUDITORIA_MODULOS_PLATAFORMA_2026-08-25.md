# Auditoría de módulos de la Plataforma Primera Infancia

Fecha de corte: 25 de agosto de 2026  
Alcance: inventario estático, navegación, permisos, rutas, dependencias, pruebas y muestra de registros HTTP de Railway.  
Regla aplicada: esta auditoría no elimina código, datos, rutas ni tablas.

## 1. Resultado ejecutivo

La plataforma no tiene una gran cantidad de módulos completamente inútiles. El problema principal es de organización: hay funciones históricas, técnicas, administrativas y especializadas expuestas al mismo nivel del menú, lo que produce sensación de duplicidad.

Se identificaron:

- 1 elemento de menú inequívocamente inacabado: **Mi espacio de trabajo (pendiente)**.
- 1 paquete backend transicional sin consumidores detectados: `backend/modules/operacion_central`.
- 4 grupos de módulos que deben consolidarse visualmente antes de considerar eliminación física.
- 2 funciones técnicas que deben conservarse, pero no necesitan estar visibles para usuarios operativos.
- 0 módulos funcionales cuya eliminación inmediata sea segura sin una fase previa de migración o medición.

Recomendación central: reducir el menú primero; no borrar todavía servicios, tablas o rutas. Ocultar un acceso es reversible. Eliminar código o datos puede romper procesos indirectos.

## 2. Evidencia revisada

- Menú y secciones reales de `frontend/index.html`.
- Control de navegación `mostrarSeccion()` y permisos de frontend.
- `ROLE_MENU_PERMISSIONS` y `PATH_ROLE_RULES` del backend.
- Blueprints y rutas registrados en `backend/app.py`.
- JavaScript y CSS cargados por la aplicación.
- Referencias cruzadas entre módulos.
- Suite de pruebas existente.
- Registros HTTP recientes de Railway como evidencia auxiliar, no como única fuente.

La muestra de Railway confirmó llamadas reales a Base Maestra, Cruce de Bases, Calendario, Talento Humano, configuración institucional, Theme Manager, documentos, cumplimiento y LÍA. También confirmó que todos los archivos JavaScript se descargan al abrir la página; por eso una descarga de archivo estático no demuestra que el usuario haya usado el módulo.

## 3. Inventario y clasificación

| Área o módulo | Estado técnico | Decisión recomendada | Motivo |
|---|---|---|---|
| Panel principal | Esencial y activo | Conservar | Punto de entrada y resumen institucional. |
| Buscar beneficiario | Esencial y activo | Conservar | Consulta transversal solicitada para cualquier participante. |
| Base Maestra | Esencial y activo | Conservar | Fuente canónica que alimenta el resto de la plataforma. |
| Calidad de Datos | Activo | Conservar | Valida y diagnostica la fuente maestra; no equivale a supervisión contractual. |
| Backups | Activo, técnico | Conservar, solo SUPERADMIN | Protección y recuperación; no debe mostrarse a perfiles operativos. |
| Cruce de Bases | Activo dentro del panel | Conservar integrado | No tiene botón propio, pero el panel y `/api/cruce-bases/*` se ejecutan en el dashboard. No está huérfano. |
| Expediente Operativo UCA | Activo | Conservar | Centraliza actividades, estado y evidencias por UCA. |
| Biblioteca Oficial ICBF | Activo | Conservar | Fuente documental versionada para la operación. |
| Motor de Gestión | Activo, orquestador | Conservar | Coordina fuentes, productos y cierre; puede quedar solo para coordinación/gerencia. |
| Planeación Operativa | Activo | Conservar | Calendario central por componentes; no es la planeación pedagógica detallada. |
| Supervisión y Calidad | Activo | Conservar | Seguimiento operativo y trazabilidad; función distinta de calidad de datos. |
| Integridad y Estabilidad | Crítico | Conservar backend; ocultar a usuarios comunes | El registro en `app.py` es obligatorio y el gate de integridad bloquea despliegues inseguros. Es una consola técnica. |
| Formatos ICBF | Activo, histórico | Consolidar como portada única de formatos | Es acceso operativo directo a formatos. No eliminar mientras existan generadores heredados en `app.py`. |
| Motor de Plantillas | Activo, administrativo | Conservar con acceso restringido | Registra, inspecciona y versiona plantillas; no es el mismo flujo que generar un formato. |
| Motor Documental IDP | Activo | Conservar | Lectura, OCR/extracción, validación y revisión documental. Comparte pantalla con Centro Documental, pero son capas complementarias. |
| Plantillas Oficiales | Activo, administrativo | Integrar bajo “Administrar plantillas” | Catálogo oficial. Puede agruparse con Motor de Plantillas, no borrarse todavía. |
| Paquete Mensual | Activo | Conservar | Generación consolidada de entregables mensuales. |
| Relación del Mes | Activo y especializado | Conservar | Cálculos de usuarios, rangos y alimentos solicitados expresamente. |
| Cuentas de Cobro | Activo | Conservar si la corporación lo usa | Generador independiente con plantillas propias. Ocultar por tenant si no aplica. |
| Cumplimiento ICBF | Activo, con error observado | Conservar y corregir | Railway mostró `POST /api/cumplimiento/evaluar` con 500. Un fallo no convierte el módulo en inútil. |
| Calendario Inteligente | Esencial y activo | Conservar | Actividades, vencimientos, evidencias y conexión con LÍA. |
| Planeación Pedagógica | Activo | Conservar | Construcción pedagógica especializada. |
| Gestión Pedagógica | Activo | Conservar, simplificar navegación | Gestiona entregables/eventos y estados; se relaciona con planeación, pero no es idéntico. |
| Gestión por Coordinador | Activo | Conservar | Equipos, asignaciones y seguimiento por coordinador. |
| Gestión de Familias y Redes | Activo | Conservar | Gestión comunitaria y de redes. |
| Componente Psicosocial | Activo, especializado | Conservar agrupado | Expediente y trabajo psicosocial especializado; agrupar con Familias y Redes. |
| Nutrición (histórico) | Activo, solapado | Migrar funciones y luego ocultar | Conserva carga nutricional y BOA. No eliminar hasta trasladar y probar estas funciones en Salud y Nutrición integral. |
| Salud, Nutrición, Peso y Talla | Activo y probado | Designar módulo principal | Incluye cruces, historial, alertas, calendario y reportes. Debe ser la entrada principal del área. |
| Talento Humano | Esencial y activo | Conservar | Fuente maestra de coordinadores, docentes y equipos. |
| Ambientes Protectores | Activo | Conservar | Componente contractual diferenciado. |
| Administración | Esencial, restringido | Conservar | Usuarios, fundaciones, roles y seguridad. |
| Integraciones y Configuración | Activo, sensible | Conservar solo SUPERADMIN/GERENTE | Incluye operaciones maestras y limpieza controlada; no es para usuarios generales. |
| Administrativo y Financiero | Activo | Conservar según alcance contractual | Operación financiera distinta de facturación de la plataforma. Aplicar bandera por tenant si no se usa. |
| Panel Comercial | Activo, negocio SaaS | Ocultar a corporaciones; conservar para operador | Administra la relación comercial, no la atención de Primera Infancia. |
| Gerencia General | Activo y probado indirectamente | Conservar para gerencia | BI y visión ejecutiva. Puede reemplazar accesos dispersos para GERENTE. |
| Facturación / Suscripción | Activo, negocio SaaS | Ocultar a perfiles operativos | Licencia, créditos y suscripción; necesario para administración de la plataforma. |
| Manual Operativo | Activo | Conservar | Contenido normativo y ayuda institucional. |
| Reportes Gerenciales | Activo | Conservar | Exportación de informes; complementa el tablero de gerencia. |
| Configuración Institucional | Esencial | Conservar como fuente de identidad | Logo, encabezado e información institucional global/tenant. |
| Ajustes / UX-UI | Activo | Conservar para preferencias simples | Colores, densidad, escala, movimiento y accesibilidad. |
| Theme Manager | Activo, solapado | Restringir y fusionar visualmente con Ajustes | Editor avanzado de temas por corporación. No debe competir en el menú con ajustes cotidianos. |
| Configuración de Acceso | Activo, infraestructura | Ocultar en Railway salvo SUPERADMIN | Diagnóstico de URL/túnel/almacenamiento; útil técnicamente, no para operación diaria. |
| LÍA | Activo | Conservar | Ayuda contextual, recorridos, voz y presentación de la plataforma. |
| `operacion_central` | Sin rutas ni consumidores detectados | Candidato a retirar en fase controlada | Es un repositorio transicional documentado como punto futuro de migración. Solo lo referencian su propio paquete y una cadena de migración nominal. |
| Mi espacio de trabajo | Placeholder | Retirar del menú ahora | Está marcado literalmente como “pendiente” y no tiene pantalla ni servicio. |

## 4. Duplicidades aparentes y decisión correcta

### 4.1 Nutrición

Existe una duplicidad real de experiencia:

- `Nutrición` histórico: carga de archivo, peso/talla, alertas y BOA.
- `Salud, Nutrición, Peso y Talla`: solución integral con historial, cruces, alertas, calendario, actividades y reportes.

Decisión: convertir el módulo integral en la única entrada visible. Antes de retirar el histórico se deben migrar la carga y BOA, comparar resultados por tenant y conservar alias de rutas durante una versión.

### 4.2 Configuración visual

Hay tres accesos que el usuario puede percibir como uno:

- Configuración Institucional: identidad, logo, administrador y encabezados.
- Ajustes / UX-UI: preferencias visuales y accesibilidad.
- Theme Manager: creación y administración avanzada de temas.

Decisión: conservar las tres capacidades, pero presentarlas bajo una sola entrada “Configuración” con pestañas: Institución, Apariencia y Temas avanzados. Temas avanzados debe quedar restringido.

### 4.3 Planeación

Los módulos no son equivalentes, pero sus nombres no explican el alcance:

- Calendario Inteligente: fechas y pendientes personales.
- Planeación Pedagógica: contenido pedagógico.
- Gestión Pedagógica: entregables y seguimiento.
- Gestión por Coordinador: equipos y control territorial.
- Planeación Operativa: programación central multicomponente.

Decisión: no borrar. Organizar por rol y renombrar subtítulos para que cada usuario vea solo su flujo.

### 4.4 Documentos y formatos

Formatos ICBF, Motor de Plantillas, Plantillas Oficiales, Paquete Mensual y Motor Documental cumplen etapas distintas. La duplicidad es de navegación, no necesariamente de motor.

Decisión: crear una portada “Documentos y formatos” con cuatro acciones: Generar, Administrar plantillas, Leer/validar y Paquete mensual. Mantener los servicios internos independientes.

## 5. Elementos que no deben eliminarse aunque parezcan técnicos

- `integrity_stability`: es un control crítico de despliegue.
- `cruce_bases`: se ejecuta desde el panel principal y tiene actividad HTTP confirmada.
- `importaciones_universales`: servicio transversal de Base Maestra; no necesita menú propio.
- `centro_documental`: comparte la pantalla del Motor Documental y genera actas/informes.
- `asistente_capacitacion`: backend de LÍA y ayuda contextual.
- `seguridad`: autenticación, permisos y aislamiento multi-tenant.
- `facturacion_suscripcion` y `panel_comercial`: no son operación ICBF, pero pueden ser esenciales para el operador SaaS.

## 6. Hallazgos de calidad que afectan la percepción de “módulo inútil”

1. El menú presenta demasiadas capacidades a roles de gestión; conviene un menú por tarea y no por subsistema técnico.
2. Todos los JavaScript se cargan al inicio, incluso cuando el módulo no se abre. Esto aumenta peso y confunde la medición de uso basada en archivos estáticos.
3. No existe telemetría funcional persistente por apertura de módulo; los logs HTTP solo permiten una aproximación.
4. `Cumplimiento ICBF` está conectado pero produjo un error 500 en la muestra de Railway. Debe diagnosticarse, no eliminarse.
5. Las rutas de branding global devolvieron 404 en la muestra; existe fallback institucional, pero el hallazgo debe tratarse aparte.
6. El pie del menú muestra una versión visual antigua (`v2.3.0-alpha.52`) aunque la plataforma auditada corresponde a una línea posterior. Esto puede inducir a pensar que hay módulos obsoletos.

## 7. Plan de depuración reversible

### Fase A — limpieza segura del menú

1. Retirar el placeholder “Mi espacio de trabajo”.
2. Ocultar Integridad, Acceso, Backups y Temas avanzados a perfiles no técnicos.
3. Ocultar Panel Comercial y Facturación a usuarios de corporaciones que no administran la suscripción.
4. Mostrar Salud y Nutrición integral como entrada principal; mantener temporalmente el histórico bajo “Herramientas anteriores”.
5. Agrupar documentos y formatos bajo una portada única.

No se borran endpoints, tablas ni archivos en esta fase.

### Fase B — telemetría de 30 días

Registrar de forma redactada y por tenant:

- apertura de módulo;
- acción principal ejecutada;
- éxito/error;
- rol;
- fecha;
- sin nombres de niños, documentos ni contenido sensible.

Un módulo solo será candidato a eliminación física si durante 30 días no tiene uso, no es dependencia interna y existe aprobación funcional.

### Fase C — consolidación

1. Migrar carga y BOA del módulo Nutrición histórico al integral.
2. Unificar la entrada visual de configuración.
3. Unificar la entrada visual de documentos/formatos.
4. Corregir permisos y menú por rol desde una única fuente backend.
5. Cargar JavaScript bajo demanda por módulo.

### Fase D — retiro físico controlado

Orden propuesto:

1. `Mi espacio` (solo HTML, sin datos).
2. `operacion_central`, después de una búsqueda final de importaciones dinámicas y prueba completa.
3. Interfaz histórica de Nutrición, solo después de paridad funcional y una versión de compatibilidad.
4. Cualquier otro módulo únicamente con telemetría, respaldo, migración, pruebas y autorización expresa.

## 8. Pruebas ejecutadas durante la auditoría

| Prueba | Resultado |
|---|---|
| Motor Central de Integridad 2.7.0 | PASS |
| Healthcheck predeploy Railway | PASS |
| Release operativo 2.3.7 | PASS |
| Salud y Nutrición Integral | PASS |

Estas pruebas confirman estabilidad básica, no sustituyen las pruebas de regresión completas que deberán ejecutarse antes de cada retiro.

## 9. Decisión final de auditoría

No se recomienda eliminar masivamente módulos. La reducción correcta debe comenzar por el menú y por permisos, porque la mayor parte de los componentes tiene una función real o actúa como servicio interno.

Retiro inmediato de bajo riesgo recomendado: **solo el placeholder “Mi espacio de trabajo”**.

Candidato técnico a eliminación después de validación: **`backend/modules/operacion_central`**.

Candidato a consolidación, no a borrado inmediato: **Nutrición histórico**.

El resto debe conservarse, restringirse por rol/tenant o reagruparse hasta contar con telemetría suficiente.
