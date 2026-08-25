# Voz de LÍA

La fase inicial usa voz encadenada y está apagada con `LIA_VOICE_ENABLED=false`.
El usuario inicia el micrófono; la transcripción queda visible y editable antes
de enviarse. Al cerrar el panel se cancela la escucha y la reproducción.

`speechSynthesis` es el respaldo local. Silencio y velocidad se guardan como
preferencias. Realtime/WebRTC permanece apagado y no se activará hasta validar
proveedor, sesión efímera, límites, auditoría y fallback escrito.
