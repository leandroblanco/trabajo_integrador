
# 📡 Monitor Triple PAM4 — GUI de Recepción, Decodificación y Comparación

Este repositorio contiene **solo el monitor**: una aplicación PyQt6 que **escucha conexiones TCP**, recibe **símbolos PAM4** de **hasta tres transmisores (TX1, TX2, TX3)**, **detecta tramas**, **decodifica bins (0–255)**, y **visualiza** en tiempo real:
- Señal temporal (opcionalmente demodulada para TX1),
- **Barras de magnitud (64 bins)**,
- Datos **RAW**, **bitstream**, **sincronismo de cabecera** y **bins decodificados**.


---

## 🚀 Características principales

- **Servidor TCP embebido**, configurable (por defecto `8100`), con asignación automática de etiquetas **TX1–TX3** por IP.   
- **Decodificación de 256 símbolos PAM4 → 64 bytes (0–255)** por trama, a partir de una **cabecera fija de 16 símbolos**.   
- **Gráfico de barras comparativo** de 64 bins (original, canal con ruido, demodulado) con **desfase horizontal** y **colores/visibilidad** por TX.   
- **Ventanas auxiliares**: Chat/Log, Layers (capas), y pestañas de Raw/Bitstream/Magnitudes/Sync/Decoded. 

---

## 🧱 Arquitectura del monitor

### 1) Hilo de servidor (`ServerThread`)
- **Escucha TCP** en `0.0.0.0:<puerto>`, admite múltiples clientes, **timeout** y cierre seguro.  
- **Asigna TX por IP** (`TX1`→`TX3`) y emite señales Qt a la GUI:  
  - `status` (logs), `ip_assigned`, `buffer_update`, etc. fileciteturn0file0
- **Empaquetado/Desempaquetado**: cada **byte entrante** se separa en **4 símbolos PAM4 de 2 bits** (`b7..b6`, `b5..b4`, `b3..b2`, `b1..b0`). 

### 2) Flujo de datos y buffer
- Los símbolos recibidos se acumulan en un **`deque(maxlen=10000)`** por cliente.  
- La GUI escucha `buffer_update(tx, ip, symbols)` y actualiza todas las vistas. 

### 3) Sincronización y decodificación de tramas
- Cabecera fija `HEADER_SYMBOLS` de **16 símbolos**.  
- Se busca la **última cabecera válida** en el buffer (`find_latest_valid_frame`) y, si se encuentra, se toman los **256 símbolos siguientes** como **cuerpo de trama**. fileciteturn0file0  
- Esos 256 símbolos (2 bits c/u) → **512 bits** → **64 bytes (0–255)**. 

### 4) Reconstrucción temporal (IFFT)
- A partir de los **64 bins** decodificados, se crea un espectro discreto y se aplica **IFFT** para 0.1 s (**fs = 44.1 kHz**, **dur = 100 ms**).  
- Se asigna la **frecuencia `f = (i+1)*100 Hz`** al bin `i` (1..64), indexando en el vector espectral. 

---

## 🔌 Protocolo de entrada (para clientes)

Para que el monitor interprete correctamente:

1. **Símbolos PAM4** codificados como **valores de 2 bits** (0..3).  
2. **Empaquetado**: enviar bytes donde **cada byte contiene 4 símbolos** (2 bits c/u) en este orden:  
   `S0=b7..b6, S1=b5..b4, S2=b3..b2, S3=b1..b0`. 
3. **Trama**:
   - **Cabecera**: 16 símbolos fijos `HEADER_SYMBOLS` (ver valores en el código).  
   - **Payload**: 256 símbolos (→ 64 bytes 0..255). 

> El monitor **no exige** que el envío comience exactamente en cabecera; buscará **la última cabecera** válida en el buffer para **re-sincronizarse**. fileciteturn0file0

### Ejemplo minimal de cliente (Python)
```python
import socket

HOST, PORT = "127.0.0.1", 8100
HEADER = [1,2,2,0,1,2,3,3,1,2,3,0,1,2,0,1]  # igual al del monitor
payload_symbols = [0,1,2,3] * 64  # 256 símbolos de 2 bits (demo simple)
symbols = HEADER + payload_symbols

def pack_4sym_to_byte(s0, s1, s2, s3):
    return ((s0 & 3) << 6) | ((s1 & 3) << 4) | ((s2 & 3) << 2) | (s3 & 3)

packed = bytearray()
for i in range(0, len(symbols), 4):
    chunk = symbols[i:i+4]
    while len(chunk) < 4:
        chunk.append(0)
    packed.append(pack_4sym_to_byte(*chunk))

with socket.create_connection((HOST, PORT)) as s:
    s.sendall(packed)
```

---

## 🖥️ Interfaz y pestañas
[![Magnitudes.png](https://i.postimg.cc/vTmSN3Jb/Magnitudes.png)](https://postimg.cc/47r5Kb4S)
[![Bit-Stream.png](https://i.postimg.cc/KjYsHJ6X/Bit-Stream.png)](https://postimg.cc/sQtcB9fK)
[Decoded.png](https://postimg.cc/TLZ9yqY8)
[![Header.png](https://i.postimg.cc/wMBbG0Cj/Header.png)](https://postimg.cc/bDKTGHY7)
[![Raw-Data.png](https://i.postimg.cc/5ytkRnhN/Raw-Data.png)](https://postimg.cc/vgpz1L8p)

### Controles superiores
- **Nombre / Color / Ver** por cada TX.  
- **Puerto**, **Inicio/Stop** del servidor.  
- **Demod TX1**: convierte símbolos PAM4 (0..3) a **niveles de voltaje** `{-3,-1,1,3}` solo para el gráfico **Tiempo**.   
- **IGNORAR 'hola'**: filtro auxiliar (para pruebas).  
- Botones para abrir **Chat/Log** y **Layers** (activar/desactivar capas). 

### Pestañas principales

- **Tiempo**: muestra los últimos ~1000 símbolos por TX; si `Demod TX1` está activo, mapea 0..3 → −3, −1, 1, 3 para TX1.   
- **PAM4 Values**:  
  - **Secuencia** (scatter de últimos valores 0..7)  
  - **Histograma** por TX. 
- **Magnitudes 64**: barras de 0..63 con **desfase** por TX para comparación clara. 
- **Raw Data**: símbolos PAM4 en **hex** (últimos 400). 
- **Bit Stream**: bits `00/01/10/11` reconstruidos (agrupados de a 8). 
- **Header Sync**: estado por TX (Buscando/¡SYNC OK! + índice) y fragmento de buffer con la cabecera **marcada**. 
- **Decoded Bins**: lista `[64]` con valores **0–255** (último frame válido). 

---

## 🧪 Mapas y conversiones (PAM4/voltaje)

- **`unpack_bytes_to_symbols`**: byte → 4 símbolos de 2 bits.   
- **`pam_symbols_to_voltage`**:  
  - Si los datos están en 0..3 → mapea a **−3, −1, 1, 3**.  
  - Si vienen escalados a 0..7 → los normaliza a **−3..+3**. 

---

## 🔧 Instalación

```bash
git clone https://github.com/usuario/monitor-pam4.git
cd monitor-pam4

python -m venv .venv
# Activar:
#  - Windows: .venv\Scripts\activate
#  - Linux/Mac: source .venv/bin/activate

pip install -r requirements.txt
```

### `requirements.txt` sugerido
```
PyQt6
pyqtgraph
numpy
```
> Versiones exactas pueden fijarse según tu entorno. El monitor fue desarrollado con PyQt6, pyqtgraph y NumPy. 

---

## ▶️ Ejecución

```bash
python Monitor.py
```

- La ventana principal muestra los controles y pestañas.  
- Usá **Puerto** para cambiar el puerto TCP antes de `▶ Inicio`.  
- Abrí **Chat/Log** para ver eventos (conexiones, IP↔TX, estado del servidor).

---

## 📦 Estructura mínima del repo

```
monitor-pam4/
├─ Monitor.py
└─ README.md
```

---

## 🩺 Troubleshooting

- **No hay datos en gráficos**  
  - Verificá que tus clientes se conecten al puerto correcto y **empaquen 4 símbolos por byte**.   
  - Confirmá que envíen **cabecera + 256 símbolos** para cada frame. 

- **SYNC no se logra**  
  - Asegurate de usar **exactamente** la cabecera del monitor (`HEADER_SYMBOLS`). 


---

## 📎 Referencia del código

Todos los detalles descritos provienen del archivo `Monitor.py` incluido en este repo. Consultalo para extender o adaptar comportamientos específicos. 
