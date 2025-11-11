# Proyecto Final – Cadena de Comunicación PAM4 con ESP32 y PC

Este proyecto implementa el **receptor digital** de una cadena de comunicación basada en **PAM4** (Pulse Amplitude Modulation 4 niveles).  
La parte transmisora y el “canal” ya están resueltos por otros compañeros; aquí se describe **qué hace el código de la ESP32 receptora** y el **código de la PC**.

El objetivo principal es:

- Recibir, a través de la red, los datos modulados en PAM4.  
- Reensamblarlos y entregarlos a una PC.  
- En la PC:  
  - **Demodular lógicamente** (recuperar los símbolos PAM4 0–3).  
  - Mostrar por consola lo que está recibiendo.  
  - Reenviar los datos a un programa visualizador (gráficos de barras, etc.).

---

## 1. Visión general del sistema

Flujo de datos completo:

**Transmisor → Canal ESP32 (compañero) → ESP32 Receptora (este proyecto) → PC → Visualizador**

A grandes rasgos:

1. El **transmisor** genera 64 amplitudes (valores de 0 a 255) y les antepone la palabra `"hola"` como cabecera.
2. Esas 68 bytes (`"hola"` + 64 amplitudes) se **modulan en PAM4** (2 bits por símbolo, 4 niveles) y se envían por la red hasta el **canal**.
3. El **canal** puede introducir errores (ruido) a los símbolos PAM4, y luego vuelve a empaquetarlos en bytes y los reenvía a:
   - La **ESP32 receptora** (este proyecto).  
   - Un **monitor/visualizador** para el profesor.
4. La **ESP32 receptora** recibe estos bytes desde el canal y los reenvía a la **PC**, en bloques de 68 bytes.
5. La **PC**:
   - Comprueba la cabecera `"hola"`.  
   - Demodula los bytes a símbolos PAM4 (0, 1, 2, 3).  
   - Muestra la información por consola.  
   - Reenvía los mismos 68 bytes al programa visualizador.

---

## 2. Formato de los datos

Cada bloque de datos (“frame”) que maneja el receptor tiene exactamente **68 bytes**:

- **Bytes 0 a 3**: texto `"hola"` (cabecera de sincronismo / marca de inicio).  
- **Bytes 4 a 67**: **64 amplitudes** (valores entre 0 y 255) que representan el espectro / magnitudes originales.

Estos 68 bytes, antes de llegar al receptor, pasan por una etapa de modulación PAM4:

- Cada byte (8 bits) se convierte en **4 símbolos PAM4** de 2 bits cada uno.
- Un símbolo de 2 bits puede ser:  
  `00 → 0`, `01 → 1`, `10 → 2`, `11 → 3`  
- Esos símbolos viajan por la cadena y el canal puede introducir errores sobre ellos.

---

## 3. Rol de la ESP32 Receptora

Archivo: `main.py` (MicroPython, ESP32)

La ESP32 **no demodula**; su tarea es actuar como un **nodo de paso inteligente**:

1. **Conexión WiFi**  
   - Se conecta a la red WiFi configurada (`SSID = "UBP"`, `PASS = "pascal25"`).  
   - Obtiene una IP dentro de la red local.

2. **Servidor TCP frente al canal**  
   - Abre un socket servidor en la ESP32 en `PORT_RX = 5052`.  
   - El **canal** se conecta a este puerto y le envía continuamente los bytes PAM4 ya reempaquetados.

3. **Recepción en streaming**  
   - La ESP32 lee los datos que van llegando del canal en trozos (`recv(1024)`), sin saber a priori dónde termina cada paquete.  
   - Va acumulando todo en un **buffer interno** (`buf`).

4. **Reconstrucción de frames de 68 bytes**  
   - Mientras el buffer tenga al menos 68 bytes, se extrae un bloque:  
     - `frame = buf[0:68]`  
     - Se descartan esos 68 bytes del buffer.  
   - Cada `frame` corresponde a `"hola" + 64 amplitudes` que ya han pasado por el transmisor y el canal.

5. **Reenvío a la PC**  
   - Por cada frame, la ESP32 abre una **conexión TCP cliente** hacia la IP de la PC (`PC_IP`, puerto `PC_PORT_TX = 9100`).  
   - Envía exactamente esos 68 bytes a la PC.  
   - Cierra esa conexión (modelo conexión corta por frame).

En resumen:  
> **ESP32 = puente entre el canal y la PC.**  
> Recibe streaming de bytes del canal, los agrupa en bloques de 68 bytes y los reenvía, tal cual, a la PC.

---

## 4. Rol de la PC

Archivo: script Python en la PC (por ejemplo `pc_receptor.py`)

La PC es donde se hace la parte más “inteligente” del receptor:

1. **Servidor TCP frente a la ESP32**  
   - Abre un servidor en `HOST = "0.0.0.0"`, `PORT = 9100`.  
   - Queda a la espera de que la **ESP32** se conecte y le mande datos.

2. **Recepción y armado de frames**  
   - Igual que en la ESP32, la PC recibe datos en “trozos” y los acumula en un buffer.  
   - Cada vez que el buffer tiene 68 bytes o más, extrae un `frame` completo para procesarlo.

3. **Separación de cabecera y datos**  
   - De cada `frame`:
     - `header = frame[0:4]` → debería ser el texto `"hola"`.  
     - `data_bytes = frame[4:68]` → 64 amplitudes 0–255.
   - La cabecera se imprime por consola para verificar que el sincronismo se mantiene.

4. **Demodulación lógica PAM4 (función `decodificar_pam4`)**  
   - Aquí ocurre la **demodulación**, pero de forma lógica/digital.  
   - Por cada byte del frame:
     - Se extraen 4 símbolos PAM4:  
       - bits 7–6 → símbolo 1  
       - bits 5–4 → símbolo 2  
       - bits 3–2 → símbolo 3  
       - bits 1–0 → símbolo 4  
     - Cada símbolo se convierte en un número entre 0 y 3.  
   - Al final se obtiene un vector con todos los **símbolos PAM4** que llegaron en ese frame.

5. **Visualización por consola**  
   - Se muestra por consola:
     - La cabecera (`'hola'`) para comprobar el inicio correcto.  
     - La lista de símbolos PAM4 decodificados (0, 1, 2, 3), que representan los niveles de la modulación.

6. **Reenvío al visualizador**  
   - La PC abre (o mantiene) una conexión TCP con el **visualizador** (`VIS_IP`, `VIS_PORT = 8100`).  
   - Le envía **exactamente los mismos 68 bytes** del frame.  
   - El visualizador, preparado por otro compañero, se encargará de:
     - Interpretar los 64 bytes de amplitud.  
     - Dibujar 64 barras o la representación que él tenga programada.

En resumen:  
> **PC = receptor demodulador + pasarela al visualizador.**  
> Toma los 68 bytes, separa la cabecera, demodula PAM4 a símbolos 0–3, lo muestra y reenvía el bloque bruto al programa gráfico.

---

## 5. ¿Dónde se hace la demodulación PAM4?

Es importante aclarar:

- **La ESP32 NO demodula**. Solo recibe bytes y los reenvía.
- **La PC sí demodula**, con la función `decodificar_pam4`.

La demodulación que se hace es **digital/lógica**:

1. Se parte de bytes donde cada uno contiene 4 símbolos PAM4 (porque 4×2 bits = 8 bits).  
2. Se “desempaquetan” los bits de cada byte en grupos de 2.  
3. Cada grupo de 2 bits se interpreta como un símbolo PAM4:  
   - `00 → 0`  
   - `01 → 1`  
   - `10 → 2`  
   - `11 → 3`  
4. El resultado es la **secuencia de niveles de PAM4** que viajaron por el canal.

Esto permite, por ejemplo, detectar si el canal introdujo errores en los símbolos.

---

## 6. Cómo ejecutar todo (resumen práctico)

1. **Configurar IPs y puertos**
   - En la ESP32:  
     - `PC_IP` debe ser la IP real de la PC en la red WiFi.  
   - En la PC:  
     - El script debe escuchar en el mismo puerto (`9100`) que la ESP32 usa para enviar.

2. **Arrancar el sistema en orden**
   1. Encender la red WiFi (`UBP`).  
   2. Levantar el código del **canal** (ESP32 intermedia del compañero).  
   3. Ejecutar el script de la **PC receptora**.  
   4. Ejecutar el **visualizador** en la PC correspondiente.  
   5. Ejecutar el **transmisor** (puerto serie + envío PAM4).

3. **Verificación**
   - En la ESP32 receptora: se ven logs de frames de 68 bytes reenviados a la PC.  
   - En la PC receptora: se ve la cabecera `'hola'` y los símbolos PAM4 decodificados.  
   - En el visualizador: se observan las 64 barras correspondientes a las amplitudes recibidas.

---

## 7. Conclusión

Este proyecto implementa un **receptor digital en dos etapas**:

- La **ESP32** actúa como puente entre el canal y la PC, manteniendo el formato binario y agrupando los datos en frames de 68 bytes.  
- La **PC** realiza la **demodulación PAM4**, la visualización textual y el reenvío de los datos al software gráfico del visualizador.

De esta forma se completa la cadena: **modulación PAM4 → canal con errores → receptor digital (ESP32 + PC) → visualización del resultado**.
