# Control de cambio — indexación pública de Primera Infancia

## Alcance autorizado

- Objetivo: preparar `https://primerainfancia.pro/` para descubrimiento e indexación en buscadores.
- Revisión de partida: `7906c7c98273357d47dd99a4675d0dfb9ddfbe67`.
- Archivos permitidos: metadatos y descripción pública del acceso en `frontend/index.html`; archivos públicos `robots.txt` y `sitemap.xml`; rutas explícitas de solo lectura; prueba de contrato SEO.
- Exclusiones: menú, Liam, autenticación, API funcional, permisos, datos, módulos privados, plantillas y banderas multiprograma.

## Resultado esperado

La portada declara título, descripción, canonical, Open Graph y datos estructurados; `robots.txt` permite la portada y bloquea rutas privadas; el sitemap contiene únicamente la portada.

## Riesgos y reversión

- La indexación y posición dependen de Google y no pueden garantizarse ni ser inmediatas.
- Search Console necesita acceso humano a una cuenta de Google y verificación de propiedad.
- Reversión: revertir exclusivamente el commit de esta entrega; no restaurar carpetas ni datos.

## Pruebas

- Contrato estático SEO y XML válido: `PASS`.
- Acceso público con Playwright en 320×640, 390×844, 768×1024 y 1366×768: `PASS`; sin desbordamiento horizontal ni tarjeta fuera del viewport.
- Regresión visual del bloque multiprograma en diez viewports: `PASS`.
- Sintaxis Python del servidor y prueba: `PASS`.
- Sintaxis del controlador Liam: `PASS`; el archivo no fue modificado.
- `git diff --check`: `PASS` con avisos informativos de finales de línea.
- Prueba heredada `test_responsive_device_stability.py`: `FAIL` preexistente porque exige el marcador `2.3.4-responsive-stability`, mientras la revisión de partida ya utiliza `2.3.5-responsive-conservation`. No se modificó ni debilitó esa prueba dentro de este alcance.
- Revisión funcional publicada: `1ce6fc9`.
- Despliegue Railway: `1f7b7248-7557-4f1a-8f29-e2db7ae71fcc`, estado `Online`.
- Healthcheck, portada, favicon, `robots.txt` y `sitemap.xml`: `200 PASS`.
- Tipos públicos: robots `text/plain`, sitemap `application/xml`, favicon `image/vnd.microsoft.icon`.
- Sitemap analizado como XML: raíz `urlset`, una URL canónica, `https://primerainfancia.pro/`.
- Solicitud con agente `Googlebot` a la portada: `200 PASS`.
- Metadatos productivos: título, descripción, robots, canonical, Open Graph y JSON-LD presentes.
- Registro y envío en Google Search Console: `NO EJECUTADO`; requiere acceso del propietario a una cuenta Google y no puede acreditarse desde el servidor.
