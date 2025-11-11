import serial
import matplotlib.pyplot as plt
import time
import socket
import numpy as np

# Configuración del puerto serie
PORT = 'COM3'
BAUDRATE = 9600

# Frecuencias esperadas (100 Hz a 6300 Hz en pasos de 100 Hz)
freqs = [i * 100 for i in range(1, 65)]

# Destinos TCP (IP, puerto)
destinos = [
    ("10.0.0.83", 5051),
    ("10.0.1.173", 8100)
]

# Modulación PAM4 directa desde bytes
def mod_pam4_desde_bytes(byte_list):
    bits = ''.join(f'{b:08b}' for b in byte_list)  # 8 bits por byte
    symbols = [int(bits[i:i+2], 2) for i in range(0, len(bits), 2)]  # 2 bits por símbolo
    packed = []
    print("\nEmpaquetado de símbolos PAM4 en bytes:")
    for i in range(0, len(symbols), 4):
        grupo = symbols[i:i+4]
        byte = (grupo[0] << 6) | (grupo[1] << 4) | (grupo[2] << 2) | grupo[3]
        packed.append(byte)
        print(f"Símbolos: {grupo} → Byte: {byte} (bin: {byte:08b})")
    return packed, symbols

# Envío TCP
def enviar(ip, port, datos):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(bytes(datos))
            print(f"Enviado {len(datos)} bytes a {ip}:{port}")
    except Exception as e:
        print(f"Error al enviar a {ip}:{port} → {e}")

# Reconstrucción de señal compuesta usando IFFT
def reconstruir_senal(amplitudes, freqs, fs=44100, duracion=0.1):
    N = int(fs * duracion)
    espectro = np.zeros(N, dtype=complex)
    for f, A in zip(freqs, amplitudes):
        idx = int(f * duracion)
        if idx < N:
            espectro[idx] = A + 0j
    senal = np.fft.ifft(espectro).real
    t = np.linspace(0, duracion, N, endpoint=False)
    return t, senal

# Inicializar gráfico
plt.ion()

# Abrir puerto serie
with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:
    try:
        while True:
            # Esperar "Inicio"
            buffer = b""
            while b"Inicio" not in buffer:
                buffer += ser.read(1)

            # Leer 64 bytes de datos
            amplitudes = []
            while len(amplitudes) < 64:
                byte = ser.read(1)
                if byte:
                    amplitudes.append(ord(byte))

            # Esperar "Fin"
            buffer = b""
            while b"Fin" not in buffer:
                buffer += ser.read(1)

            # Agregar la palabra "hola" al inicio del vector
            palabra = [ord(c) for c in "hola"]  # [104,111,108,97]
            amplitudes = palabra + amplitudes  # Ahora son 68 bytes

            # Imprimir vector recibido
            print("\nVector enviado (68 valores decimales):")
            print(amplitudes)

            # Modulación PAM4 directa
            datos, symbols = mod_pam4_desde_bytes(amplitudes)

            # Imprimir cantidad y lista de símbolos PAM4
            print(f"\nCantidad de símbolos PAM4: {len(symbols)}")
            #print("Símbolos PAM4:")
            #print(symbols)

            # Enviar a cada destino
            for ip, port in destinos:
                enviar(ip, port, datos)

            # Reconstruir señal compuesta (solo con las 64 amplitudes originales)
            t, senal = reconstruir_senal(amplitudes[4:], freqs)

            # Zoom de 20 ms
            zoom_duracion = 0.010
            N_zoom = int(44100 * zoom_duracion)
            t_zoom = t[:N_zoom]
            s_zoom = senal[:N_zoom]

            # Graficar
            plt.clf()

            # 1. Frecuencias y amplitudes
            plt.subplot(3, 1, 1)
            plt.bar(freqs, amplitudes[4:], width=80)
            plt.title("Magnitudes de Frecuencia recibidas (8 bits)")
            plt.xlabel("Frecuencia [Hz]")
            plt.ylabel("Valor (0–255)")

            # 2. Histograma de símbolos PAM4
            plt.subplot(3, 1, 2)
            counts = [symbols.count(i) for i in range(4)]
            plt.bar(range(4), counts, tick_label=["0", "1", "2", "3"])
            plt.title("Histograma de símbolos PAM4")
            plt.xlabel("Símbolo")
            plt.ylabel("Cantidad")

            # 3. Señal reconstruida (Zoom 10 ms)
            plt.subplot(3, 1, 3)
            plt.plot(t_zoom, s_zoom)
            plt.title("Señal reconstruida Simulada con fase 0 (Zoom 10 ms)")
            plt.xlabel("Tiempo [s]")
            plt.ylabel("Amplitud")

            plt.tight_layout()
            plt.pause(0.01)
            time.sleep(1)

    except KeyboardInterrupt:
        print("Programa finalizado por el usuario.")