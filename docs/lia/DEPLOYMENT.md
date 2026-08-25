# Despliegue gradual de LÍA

1. Desplegar código con `ENABLE_LIA_ASSISTANT=false`.
2. Ejecutar regresión, multi-tenant, roles y responsive.
3. Activar `ENABLE_LIA_ASSISTANT=true` únicamente para interfaz y ayuda estática.
4. Mantener `LIA_AI_ENABLED=false`, `LIA_VOICE_ENABLED=false` y
   `LIA_REALTIME_ENABLED=false` durante el piloto.
5. Validar un tenant piloto, métricas, feedback y rollback.
6. Activar voz encadenada después de validar permisos de micrófono.
7. Realtime requiere una fase posterior independiente.

La aplicación inicia sin proveedor externo. El health de LÍA informa
`provider_ready=false` y usa `institutional_static`.
