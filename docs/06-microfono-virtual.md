# 06 - Microfono virtual para Discord / llamadas

La voz convertida sale por defecto en tus parlantes. Para usarla como
microfono en Discord, Meet, Zoom, etc. se rutea a un **cable virtual**:
la app reproduce ahi y esas programas lo eligen como microfono.

## 1. Instalar VB-CABLE (una sola vez, con admin)

1. Descarga desde https://vb-audio.com/Cable/ (donationware).
2. Descomprime, clic derecho en `VBCABLE_Setup_x64.exe` ->
   **Ejecutar como administrador** -> Install.
3. Reinicia si lo pide. No necesitas abrir nada mas.

## 2. Configurar la app

1. `python main.py` -> grupo **"Salida para Discord / llamadas"**.
2. Si el cable esta instalado veras el aviso verde -> pulsa
   **"Usar cable virtual"** (selecciona `CABLE Input`).
3. Sin el aviso verde: instala el driver (paso 1) y pulsa **Refrescar**.

## 3. Configurar Discord / Windows

- **Discord**: Ajustes -> Voz y video -> Dispositivo de entrada ->
  `CABLE Output (VB-Audio Virtual Cable)`. Usa "Probar microfono".
- **Windows**: Configuracion -> Sonido -> Entrada -> `CABLE Output`.
- OJO: en Discord desactiva "sensibilidad automatica" si la puerta de
  ruido te come inicios de frase; el gate de la app ya filtra el fondo.

## Notas tecnicas

- La app envia mono float32 a 48 kHz; VB-CABLE lo acepta sin conversion.
- Mientras la salida apunte al cable **no te escuchas en parlantes**
  (el medidor de nivel de la app confirma que sale audio).
- Latencia mic->Discord ~= latencia normal de la app (~360ms promedio).
- Si cambias de salida con la conversion corriendo, Deten e Inicia de
  nuevo: el dispositivo se fija al arrancar el hilo.
- `core/audio_devices.py` centraliza la deteccion (`CABLE Input` para
  reproducir, `CABLE Output` como microfono en las otras apps).
