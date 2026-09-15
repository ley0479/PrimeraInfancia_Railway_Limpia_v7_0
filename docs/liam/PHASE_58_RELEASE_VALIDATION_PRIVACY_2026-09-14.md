# Fase 58 · Validación de distribución y privacidad

Se corrigió la portabilidad del validador para que Bash o Node presentes pero no ejecutables en Windows queden como comprobación omitida, sin abortar el resto. La cobertura de autorización ahora reconoce las excepciones públicas declaradas en `seguridad.services`, junto con las familias protegidas.

Se sincronizaron las expectativas del validador con los contratos vigentes: versión `2.7.2-document-center`, healthcheck Railway `/api/health` y cliente PostgreSQL 18 copiado desde una etapa Docker dedicada. También se reparó el checksum del manifiesto de plantillas sanitizadas.

## Corrección de privacidad

Se retiraron del paquete tres artefactos operativos que estaban versionados por error bajo `backend/data/tenants/1`: un RAM generado, el registro de formatos y un log de trabajo. Contenían rutas locales, nombre de usuario y metadatos operativos; no eran semillas ni código. También se retiró `deploy/verificacion_entorno_python.log` y se agregó una regla de exclusión para impedir futuras incorporaciones de datos tenant. Todos los archivos eliminados son recuperables desde la historia Git anterior a esta fase.

## Rollback

Revertir el commit restaura el validador y los artefactos eliminados. No se modificó ninguna base de datos, plantilla oficial ni dato del entorno productivo.

## Resultado

`python -B tools/validate_release.py`: **16 PASS, 0 FAIL, 1 SKIP**. Bash quedó omitido porque el ejecutable detectado no puede iniciarse en este host Windows; la sintaxis Python de 503 archivos y JavaScript de 79 archivos sí fue validada. El manifiesto raíz cubre 993 archivos distribuibles.
