# Fase 1 — Laboratorio visual aislado

## Alcance

Esta página independiente compara los temas Institucional y Ejecutivo usando datos ficticios. No importa módulos productivos, no utiliza autenticación, no realiza peticiones de red y no modifica bases de datos.

El selector solo cambia `data-theme` en `.pi-theme-lab`. La preferencia temporal usa exclusivamente `localStorage.pi_theme_lab_preview`. El botón **Restaurar Tema Institucional** elimina esa clave y restablece el tema institucional.

## Ejecución local

Desde la raíz del worktree:

```powershell
python -m http.server 4173 --directory frontend/theme-lab
```

Abrir `http://127.0.0.1:4173`.

No debe usarse Flask ni añadirse una ruta productiva para servir esta página.

## Matriz visual

Revisar los temas Institucional y Ejecutivo en anchos de 1440, 1024, 768 y 390 píxeles. Validar el menú móvil, tarjetas KPI, calendario, lista de chequeo, créditos, tabla desplazable, formulario, variantes de botón, alertas, modal, foco visible y navegación con teclado.

## Decisiones de aislamiento y accesibilidad

- Todos los componentes viven dentro de `.pi-theme-lab`.
- Las variables describen funciones visuales y no módulos operativos.
- No se usa `!important`, código externo, fuentes remotas ni dependencias nuevas.
- Los estados incluyen texto, símbolo y color.
- El modal restaura el foco y mantiene la navegación tabulada dentro del diálogo.
- `Escape` cierra modal y menú móvil.
- Se respeta `prefers-reduced-motion`.

## Verificación

```powershell
python -m py_compile backend/tests/test_theme_lab_isolation_v7.py
python -m pytest backend/tests/test_theme_lab_isolation_v7.py -q
node --check frontend/theme-lab/theme-lab.js
```

La prueba es estática: no importa la aplicación y no abre una base de datos.

## Rollback

Cerrar el servidor local y eliminar los archivos nuevos de `frontend/theme-lab`, `docs/theme-system/FASE_1_LABORATORIO_VISUAL.md` y `backend/tests/test_theme_lab_isolation_v7.py`, o descartar/eliminar este worktree. No existe rollback de datos porque esta fase no los utiliza.

## Revisión Fase 1.1

El Tema Ejecutivo fue refinado con una paleta azul marino, superficies claras y acentos dorados moderados. Se normalizaron menú, encabezado, KPI, botones, tabla, calendario, checklist, consumo de créditos, estados de formulario y modal. El Tema Institucional no fue modificado.

- Revisión visual humana: **APROBADA**.
- Resoluciones revisadas: 1440 px, 1024 px, 768 px y 390 px.
- Tema Ejecutivo: **APROBADO PARA PUNTO DE CONTROL**.
- Integración productiva: **NO REALIZADA**.
- Persistencia: solamente `localStorage` con `pi_theme_lab_preview`.
- Prueba pytest: pendiente de CI.

Lista de revisión humana:

- En 1440 px: cuatro KPI en fila, menú completo y paneles equilibrados.
- En 1024 px: KPI en dos columnas, calendario y checklist apilados sin superposición.
- En 768 px: menú colapsable, información secundaria reducida y controles accesibles.
- En 390 px: una columna, tabla como único desplazamiento horizontal, calendario legible y modal contenido.
- Con teclado: enlace de salto, menú, selector, botones, tabla desplazable, formulario y modal.
- Persistencia: elegir Ejecutivo, recargar, restaurar Institucional y recargar nuevamente.
