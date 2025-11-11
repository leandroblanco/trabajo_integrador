
[README (Tx).md](https://github.com/user-attachments/files/23473636/README.Tx.md)

# Proyecto de Análisis y Transmisión de Frecuencias

Este proyecto consta de dos componentes principales:

1. **FFT.c**: Código embebido para el microcontrolador dsPIC30F4013.
2. **PF_transmisor_pam4_serial_hola_1.py**: Código en Python para recepción, codificación y visualización de datos.

---

## 1. FFT.c

### Objetivo
Capturar una señal analógica, realizar una Transformada Rápida de Fourier (FFT) de 128 puntos, identificar la frecuencia dominante y transmitir las magnitudes de 64 componentes de frecuencia por UART.

### Funcionalidades
- **Muestreo ADC**: Captura 128 pares de muestras (Re, Im) desde el canal AN7.
- **FFT**: Utiliza memoria especial `ydata` para acelerar el cálculo FFT.
- **Análisis espectral**: Calcula la magnitud de cada componente de frecuencia (100 Hz a 6300 Hz).
- **Identificación de frecuencia dominante**: Determina la frecuencia con mayor potencia y la publica en los puertos RB0–RB5.
- **Transmisión UART**: Envía los 64 valores de magnitud precedidos por "Inicio" y seguidos por "Fin".

### Flujo de ejecución
1. Configura UART, ADC, Timer2 y puertos.
2. Toma muestras periódicas con Timer2.
3. Al completar 128 muestras, realiza FFT.
4. Calcula magnitudes y frecuencia dominante.
5. Publica resultados por UART y puertos digitales.

---

## 2. PF_transmisor_pam4_serial_hola_1.py

### Objetivo
Recibir los datos de magnitudes por UART, codificarlos en PAM4, enviarlos por TCP a múltiples destinos y visualizarlos gráficamente.

### Funcionalidades
- **Recepción UART**: Detecta las palabras "Inicio" y "Fin" para capturar 64 bytes de magnitudes.
- **Cabecera personalizada**: Agrega la palabra "hola" al inicio del vector (total 68 bytes).
- **Modulación PAM4**: Convierte los datos en símbolos PAM4 (2 bits por símbolo) y los empaqueta en bytes.
- **Transmisión TCP**: Envía los datos codificados a múltiples IPs y puertos.
- **Reconstrucción de señal**: Simula la señal original mediante IFFT.
- **Visualización**:
  - Gráfico de barras de magnitudes por frecuencia.
  - Histograma de símbolos PAM4.
  - Señal reconstruida (zoom de 10 ms).

### Flujo de ejecución
1. Abre el puerto serie y espera "Inicio".
2. Captura 64 bytes de datos y espera "Fin".
3. Agrega cabecera "hola".
4. Codifica en PAM4.
5. Envía por TCP.
6. Visualiza los datos en tiempo real.

---

## Aplicaciones
- **Análisis espectral distribuido**: Ideal para monitoreo remoto de señales.
- **Codificación eficiente**: PAM4 permite transmitir más información por símbolo.
- **Visualización en tiempo real**: Útil para diagnóstico y análisis de señales acústicas, vibraciones, etc.

