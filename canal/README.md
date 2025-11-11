# README

## Descripción general

El canal implementa un sistema de retransmisión y administración de señales PAM4 utilizando una ESP32 como nodo intermedio. 
El módulo recibe paquetes PAM4 desde un transmisor, decodifica los símbolos, aplica opcionalmente errores aleatorios, vuelve a modular los datos y los reenvía de manera persistente al receptor y a un monitor. 
Además, mantiene comunicación con una PC administradora que puede activar o desactivar el modo de error y recibir información del sistema.

El rol incluye dos componentes principales:

* **ESP32 (MicroPython):** nodo intermedio encargado del procesamiento PAM4, inserción de errores y envío persistente.
* **PC Administradora (Python):** servidor de control que recibe información, visualiza histogramas y gestiona el modo de error.

## Funcionalidad del nodo ESP32

La ESP32 realiza las siguientes tareas:

1. Conexión WiFi y establecimiento de sockets persistentes con receptor, monitor y PC administradora.
2. Recepción de paquetes del transmisor en el puerto **5051**.
3. Decodificación PAM4 extrayendo 4 símbolos por byte.
4. Visualización en consola de los primeros 16 símbolos (prefijo hola) y cálculo del histograma.
5. Inserción opcional de errores aleatorios (modo error).
6. Reempaquetado PAM4 a bytes.
7. Reenvío persistente al receptor y al monitor.
8. Notificación a la PC administradora sobre el procesamiento de cada paquete.

## Modo error

El modo error permite alterar aleatoriamente símbolos PAM4 después del prefijo de 16 símbolos del paquete. 
La probabilidad de error aplicada es del 5%. La PC administradora puede activar o desactivar este modo enviando los comandos correspondientes:

* `MODO_ERROR_ON`
* `MODO_ERROR_OFF`

## Funcionalidad de la PC Administradora

El programa en Python para PC realiza:

1. Aceptación de conexión entrante desde la ESP (puerto 5050).
2. Recepción de información cruda o modulada enviada por la ESP.
3. Decodificación PAM4 y generación de histogramas.
4. Visualización de eventos, errores e información del nodo.
5. Envío de comandos a la ESP, especialmente el control del modo error.
6. Menú interactivo para el usuario.

## Estructura general del flujo de datos

1. El **transmisor** envía un paquete PAM4 al nodo por el puerto 5051.
2. La **ESP32** decodifica, procesa, remodula y reenvía.
3. El **receptor** y el **monitor** reciben la señal ya procesada.
4. La **PC administradora** puede supervisar la actividad y activar o desactivar perturbaciones.

## Archivos incluidos

### `esp_intermedia_monitor_persistente.py` (MicroPython)

* Conexión a WiFi.
* Manejo de sockets persistentes para receptor, monitor y PC administradora.
* Recepción y decodificación de PAM4.
* Histograma de símbolo.
* Modo error.
* Reenvío persistente.
* Hilos para cada conexión.

### Script Python administrador

* Acepta conexión de la ESP.
* Decodifica símbolos PAM4.
* Muestra histogramas.
* Procesa mensajes de estado.
* Controla el modo error.
* Incluye un menú interactivo.

## Requisitos

* ESP32 con MicroPython instalado.
* Red local con IPs configuradas en el script.
* PC con Python 3.
* Conexiones abiertas en los puertos 5050, 5051 y 5052.

## Ejecución

### 1. Iniciar la PC administradora

```
python pc_admin.py
```

Esto habilita la espera de conexiones y el menú.

### 2. Encender la ESP32

El dispositivo se conectará al WiFi y luego a los sockets persistentes.

### 3. Enviar paquetes desde el transmisor

La ESP recibirá, procesará y reenviará.

## Notas

* Los primeros 16 símbolos del paquete nunca son alterados cuando el modo error está activo.
* El sistema mantiene todas las conexiones abiertas de forma persistente, incluso sin tráfico.

