# Visualizador PAM4 - Comparador de Mensajes

## Descripción del Proyecto

Este proyecto es una **herramienta de visualización y comparación de mensajes transmitidos mediante modulación PAM4**. Su propósito principal es recibir dos flujos de datos:

1. **Mensaje original**: proveniente del transmisor (TX), codificado en **PAM4**.
2. **Mensaje recibido**: proveniente del receptor (RX), que puede haber pasado por **demodulación** y estar sujeto a **ruido o pérdidas de información**.

El sistema decodifica ambos mensajes y permite compararlos **carácter por carácter**, mostrando tanto los aciertos como los errores en un **gráfico horizontal interactivo** dentro de una interfaz gráfica (GUI) en Python.

Esta herramienta es útil para:

- Verificar la integridad de la transmisión de datos.
- Analizar el impacto de ruido y errores de demodulación.
- Probar sistemas de comunicación digital basados en PAM4 de manera visual y rápida.

---

## Funcionalidad del Código

### 1. Recepción de Datos

- **TX (Transmisor)**: recibe datos PAM4, los decodifica a texto mediante la función `pam4_to_text()`.
- **RX (Receptor)**: recibe datos ya demodulados en formato texto (ASCII).

```python
mensaje_tx = recibir_desde_tx(conn_tx)
mensaje_rx = recibir_desde_rx(conn_rx)
```

### 2. Comparación de Mensajes

- La función `comparar_mensajes()` compara ambos mensajes **carácter por carácter**.
- Calcula:
  - Total de caracteres.
  - Cantidad de errores.
  - Porcentaje de coincidencia/error.
- Genera un **gráfico horizontal** donde:
  - Verde = coincidencia correcta.
  - Rojo = error (diferencia entre TX y RX).
- Las etiquetas del eje vertical muestran directamente qué carácter se compara: `"TX | RX"`.

```python
ax.barh(posiciones, [1]*total, color=colores)
ax.set_yticklabels(etiquetas)
```

### 3. Interfaz Gráfica (GUI)

- Construida con **Tkinter** y **Matplotlib** embebido.
- Permite:
  - Ingresar la cantidad de pares de mensajes a comparar.
  - Iniciar el servidor directamente desde la GUI.
  - Visualizar los gráficos de comparación de manera clara y accesible.

```python
root = tk.Tk()
root.title("Visualizador PAM4 - Comparador de Mensajes")
```

---

## Cómo Usar el Proyecto

1. **Ejecutar la aplicación**:
```bash
python tu_archivo.py
```

2. **Interfaz GUI**:
   - Ingresa la cantidad de mensajes a comparar (por defecto `2`).
   - Haz clic en **"Iniciar servidor"**.

3. **Recepción de mensajes**:
   - Conecta el transmisor (TX) enviando datos PAM4.
   - Conecta el receptor (RX) enviando datos en texto plano.

4. **Visualización**:
   - Cada par de mensajes recibidos se compara y se genera un gráfico horizontal mostrando coincidencias y errores.
   - El porcentaje de error se muestra en el título del gráfico.

---

## Requisitos

- Python 3.8 o superior
- Librerías:
  - `socket` (incluida en Python estándar)
  - `tkinter` (GUI estándar)
  - `matplotlib` (para gráficos)

Instalación de Matplotlib si no la tenés:

```bash
pip install matplotlib
```

---

## Beneficios y Aplicaciones

- Permite **visualizar y validar transmisiones PAM4** de manera interactiva.
- Ayuda a **detectar errores de demodulación y pérdida de datos**.
- Es una herramienta **educativa y de diagnóstico** para sistemas de comunicación digital.

---

## Notas

- Actualmente, el script espera que siempre llegue **un mensaje PAM4** (TX) y **uno ya demodulado** (RX).
- La interfaz permite modificar la cantidad de pares de mensajes a comparar según se necesite.
- Los gráficos se generan dentro de la misma ventana para facilidad de análisis.