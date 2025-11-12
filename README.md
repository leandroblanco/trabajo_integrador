# Trabajo Integrador

# 📡 Sistema PAM4 — Transmisión, Canal, Recepción y Monitor

Este proyecto implementa un flujo completo para **transmisión de datos codificados en PAM4**, envío por **TCP/IP**, y **visualización en tiempo real**. Incluye:

1. **Transmisor** (Python)
2. **Canal** (TCP con posibilidad de ruido)
3. **Receptor** (decodificación PAM4)
4. **Monitor** (GUI PyQt6 para análisis y comparación)

---

## ✅ 1) Transmisor (`PF_transmisor_pam4_serial_hola_1.py`)

- **Lectura por UART**:
  - Puerto: `COM3`
  - Velocidad: `9600 bps`
  - Recibe 64 magnitudes (0–255) correspondientes a frecuencias **100 Hz a 6300 Hz**.
  - Protocolo: `Inicio` → 64 bytes → `Fin`.

- **Preprocesamiento**:
  - Inserta la palabra `"hola"` (4 bytes) al inicio → total **68 bytes**.

- **Modulación PAM4**:
  - Convierte cada byte (8 bits) en **4 símbolos PAM4** (2 bits por símbolo).
  - Empaqueta 4 símbolos en un byte para transmisión.

- **Envío TCP**:
  - Destinos configurables (ejemplo):
    - `10.0.0.83:5051`
    - `10.0.1.173:8100`


- **Visualización en tiempo real**:
  - Barras de magnitudes, histograma PAM4 y señal reconstruida.

---

## ✅ 2) Canal (`Canal_pc_admin.py` + `Canal_esp.py`)

### 🔹 ESP32 — `Canal_esp.py`
- Actúa como **relay persistente** entre transmisor, receptor y monitor.
- **Modo error opcional**: introduce errores aleatorios (5%) en símbolos, protegiendo la cabecera.
- Reempaqueta símbolos → bytes para reenvío.

### 🔹 PC Administradora — `Canal_pc_admin.py`
- Controla el canal y permite activar/desactivar el modo error.
- Muestra mensajes y genera histogramas PAM4.

**Flujo**:
1. Transmisor → ESP → Receptor + Monitor.
2. PC Admin ↔ ESP para control.

---

## ✅ 3) Receptor (`Receptor_esp.py` + `Receptor_pc.py`)

### 🔹 ESP32 Receptor
- Recibe datos del canal y los agrupa en frames de 68 bytes.
- Envía cada frame a la PC por TCP.

### 🔹 PC Receptora
- Decodifica símbolos PAM4.
- Reenvía datos al monitor para análisis.

---

## ✅ 4) Monitor (`Monitor.py`)

- Aplicación **PyQt6** para visualizar datos en tiempo real.
- **Funciones**:
  - Decodificación PAM4.
  - Reconstrucción de señal con IFFT.
  - Pestañas: Tiempo, PAM4 Values, Magnitudes, Reconstrucción, Raw Data, Bit Stream, Header Sync, Decoded Bins.

**Flujo completo**:
- Transmisor → Canal → Receptor → Monitor.

---

### 🔗 Protocolo
- **Símbolos PAM4**: valores 0–3.
- **Empaquetado**: 4 símbolos por byte.
- **Trama**: cabecera + payload (256 símbolos → 64 bytes).

