# trabajo_integrador

# Canal Simulado TCP con Errores PAM4

Este script implementa un **canal de comunicación virtual** para un sistema de transmisión PAM4.  
Recibe datos desde un transmisor (TX), opcionalmente les aplica errores, y los reenvía a un receptor (RX) mediante TCP. Está diseñado para simular distintos tipos de distorsión de señal, permitiendo el análisis de errores y métricas como porcentaje de símbolos incorrectos.

---

## Estructura del Código

### 1. Errores de Canal
Se definen varias funciones que modifican los símbolos PAM4:

- `error_simbolos`: cambia algunos símbolos PAM4 aleatoriamente según una probabilidad.  
- `error_gaussiano`: agrega ruido gaussiano a los símbolos y los redondea a niveles PAM4 válidos.  
- `error_atenuacion`: reduce la amplitud de los símbolos multiplicándolos por un factor.  
- `error_offset`: desplaza los niveles de los símbolos cíclicamente.  
- `error_jitter`: simula jitter duplicando un símbolo y eliminando otro, cambiando el orden.  
- `error_reordenar`: mezcla aleatoriamente los símbolos sin modificar sus valores.

### 2. Gestor de Canal (`aplicar_canal`)
- Recibe los datos PAM4 y aplica el tipo de error definido en `modo_error`.
- Permite elegir entre:
  - `"ideal"` (sin errores)  
  - `"simbolos"`  
  - `"gauss"`  
  - `"atenuacion"`  
  - `"offset"`  
  - `"jitter"`  
  - `"reordenar"`
- Se pueden pasar parámetros adicionales como `prob_error`, `sigma`, `factor` u `offset` usando `kwargs`.

### 3. Recepción y Reenvío TCP
- Se crea un **socket TCP de escucha** en la IP y puerto definidos (`ip_listen` y `port_listen`) para recibir datos desde el TX.
- **Bucle infinito**: permite recibir múltiples mensajes consecutivos sin reiniciar el programa.
- Cada mensaje recibido se convierte en una lista de enteros (`pam4_data`).
- Se aplica el error según `modo_error`.

### 4. Cálculo de Errores
- Para modos distintos de `"ideal"`, se calcula:
  - `errores`: lista con tuplas `(posición, valor_original, valor_modificado)` de símbolos alterados.  
  - `porcentaje`: porcentaje de símbolos que fueron modificados respecto al total.
- Permite medir la **calidad del canal** y analizar la propagación de errores.

### 5. Reenvío al Receptor
- Se crea un **socket TCP cliente** para enviar los datos modificados a la IP y puerto del receptor (`ip_destino`, `port_destino`).
- Manejo de errores con `try/except` para capturar problemas de conexión o envío.

---

## Flujo de Funcionamiento

1. El **TX envía** datos PAM4 a la IP y puerto configurados del canal.  
2. El **canal los recibe** mediante TCP.  
3. Dependiendo de `modo_error`, se pueden aplicar errores:
   - Modificación de símbolos
   - Ruido gaussiano
   - Atenuación
   - Desplazamiento de niveles
   - Jitter (duplica/elimina símbolos)
   - Reordenamiento de símbolos  
4. Se calcula y muestra el **porcentaje de error** y la **posición de los errores**.  
5. Los datos (modificados o no) se **reenvían al RX** mediante TCP.

---

## Configuración

- **IP de escucha (TX → canal)**: `ip_listen = '0.0.0.0'`  
- **Puerto de escucha**: `port_listen = 5000`  
- **IP del receptor (canal → RX)**: `ip_destino`  
- **Puerto del receptor**: `port_destino`  
- **Tipo de error**: `modo_error`  
  Opciones: `"ideal"`, `"simbolos"`, `"gauss"`, `"atenuacion"`, `"offset"`, `"jitter"`, `"reordenar"`  

> Para cambiar parámetros de los errores (como probabilidad de error o factor de atenuación), se pasan mediante `kwargs` en `aplicar_canal`.

---

## Características Destacadas

- Soporta múltiples mensajes consecutivos sin reiniciar (`while True`).  
- Permite simular distintos tipos de distorsión de canal de forma flexible.  
- Proporciona métricas de error instantáneas (porcentaje y posición de símbolos afectados).  
- Compatible con cualquier sistema que transmita datos PAM4 por TCP.

---

## Ejemplo de Uso

1. Configurar IP y puerto del receptor (`ip_destino`, `port_destino`).  
2. Elegir el modo de error (`modo_error`).  
3. Ejecutar el canal:  

```bash
python canal_simulado.py
