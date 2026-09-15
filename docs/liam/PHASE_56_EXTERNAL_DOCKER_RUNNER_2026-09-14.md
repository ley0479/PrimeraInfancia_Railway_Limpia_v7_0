# Fase 56 · Runner Docker externo ADMIN/DEV

`tools/liam_dev_sandbox_runner.py` implementa la parte externa del flujo técnico. Recibe plan, parche, repositorio e imagen local; valida checksum y rutas; crea un `git worktree` efímero; aplica el parche; ejecuta exactamente todas las pruebas del plan dentro de Docker; recoge `git diff --check` y el diff binario; y genera el JSON y la firma HMAC que acepta la fase 54.

## Aislamiento

El contenedor se inicia con red deshabilitada, sistema base de solo lectura, `/tmp` efímero, límites de memoria/CPU/procesos y `no-new-privileges`. Solo se monta el worktree temporal. La clave HMAC permanece en el proceso anfitrión y nunca entra al contenedor. Antes y después de las pruebas se verifican las rutas contra el plan. No existe comando de commit, push, Railway o despliegue.

## Verificación realizada

`test_liam_external_sandbox_runner_v7.py` valida checksum, rutas normalizadas, rechazo de rutas absolutas/traversal y plan alterado. También permanecen verdes las pruebas HTTP de recepción y aprobación.

La ejecución Docker real no pudo realizarse en este equipo porque el ejecutable `docker` no está instalado. Esta limitación queda registrada como evidencia pendiente y no se sustituye con un resultado simulado.

## Uso operacional

La imagen indicada por `--image` debe estar construida previamente en el host; el runner no descarga dependencias porque usa `--network none`. La salida `.json` se envía como cuerpo exacto al endpoint y el archivo `.sig` como `X-Liam-Sandbox-Signature`.

## Rollback

Revertir el commit elimina el runner. Los worktrees temporales se retiran incluso cuando una prueba falla. El runner nunca modifica el worktree principal ni producción.
