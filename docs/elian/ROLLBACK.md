# Rollback seguro de ELIAN

1. Definir `ENABLE_ELIAN_ASSISTANT=false` para desactivar la identidad ampliada.
2. Si no existe esa variable, `ENABLE_LIAM_ASSISTANT=false` conserva el apagado compatible anterior.
3. No eliminar las tablas `elian_platform_tour_progress` ni `elian_visual_configuration`; son aditivas y no afectan la operación.
4. Restaurar el recurso anterior solo cambiando `avatar_asset_path`; no se modifica ninguna plantilla oficial.
5. Los módulos, descargas, formatos, login y PostgreSQL siguen funcionando porque ELIAN no reemplaza sus servicios.

