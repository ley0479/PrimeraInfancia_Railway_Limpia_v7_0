# Requisitos del recurso animado profesional de LIAM

No existe actualmente un archivo `.riv`, Lottie o Live2D de LIAM. La Fase 1 utiliza un póster PNG provisional y adaptadores desacoplados. El generador visual no produjo alfa real pese a solicitarlo; el póster conserva un fondo oscuro integrado que se mezcla con el panel. El recurso profesional definitivo deberá entregar transparencia real.

## Identidad

- Hombre joven adulto, profesional y cálido.
- Cabello oscuro.
- Camisa blanca y chaleco azul oscuro con detalles turquesa.
- Audífono con micrófono.
- Tablet y placa “LIAM”.
- Medio cuerpo, base holográfica y fondo transparente.
- Estilo 2D moderno, institucional y no infantil.

## Animaciones mínimas solicitadas

`idle`, `blink`, `breathing`, `wave`, `listen`, `think`, `speak`, `read_tablet`, `walk_left`, `walk_right`, `turn_left`, `turn_right`, `point_left`, `point_right`, `point_up`, `point_down`, `teleport_out`, `teleport_in`, `success`, `warning`, `error`, `goodbye`.

## Entradas recomendadas para Rive

- Estado principal enumerado.
- Dirección de mirada X/Y limitada.
- Boca o visema enumerado.
- Nivel de voz normalizado.
- Dirección de señalamiento.
- Modo de movimiento reducido.
- Contenido de tablet gestionado fuera del recurso visual.

## Reglas de entrega

- Fondo transparente.
- Recursos optimizados y sin dependencias remotas.
- Sin fuentes o imágenes con licencias incompatibles.
- Estados con nombres estables.
- Variante ligera o póster de respaldo.
- Ninguna animación debe ejecutar lógica de negocio.
- La sincronización labial completa no se declarará terminada hasta contar con visemas o una interfaz equivalente probada.
