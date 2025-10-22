import socket
import numpy as np

# ===== Parámetros =====
HOST = "10.0.0.203"   # IP de la receptora
PORT = 5000
MENSAJE = "Hola Candela"
FS = 1000            # Frecuencia de muestreo
T = 1                # Duración de símbolo (en segundos simulados)
ALPHA = 0.25         # Roll-off del filtro sinc

# ===== PAM5 =====
ENC_MAP = {
    (0, 0): -2.0,
    (0, 1): -1.0,
    (1, 0): +1.0,
    (1, 1): +2.0,
}

def string_to_bits(msg):
    return ''.join(format(ord(c), '08b') for c in msg)

def encode_pam5(bits):
    if len(bits) % 2 != 0:
        bits += '0'
    symbols = []
    for i in range(0, len(bits), 2):
        pair = (int(bits[i]), int(bits[i+1]))
        symbols.append(ENC_MAP[pair])
    return np.array(symbols, dtype=np.float64)

def raised_cosine_sinc(t, T, alpha):
    sinc = np.sinc(t / T)
    cos = np.cos(np.pi * alpha * t / T)
    denom = 1 - (2 * alpha * t / T)**2
    pulse = sinc * cos / denom
    pulse[np.isnan(pulse)] = 0
    return pulse

def generar_senal(symbols, fs, T, alpha):
    t = np.linspace(-5*T, 5*T, int(fs*T*10))
    pulse = raised_cosine_sinc(t, T, alpha)
    upsampled = np.zeros(len(symbols) * int(fs*T))
    upsampled[::int(fs*T)] = symbols
    señal = np.convolve(upsampled, pulse, mode='same')
    return señal

# ===== Transmisión =====
bits = string_to_bits(MENSAJE)
symbols = encode_pam5(bits)
señal = generar_senal(symbols, FS, T, ALPHA)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    print("[Tx] Conectado a la receptora")
    s.sendall(señal.astype(np.float64).tobytes())
    print("[Tx] Señal sinc transmitida con mensaje:", MENSAJE)