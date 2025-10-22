import socket
import numpy as np

# ===== Parámetros =====
HOST = "10.0.0.203"   # IP de la receptora (cambiar por su IP real en LAN)
PORT = 5000
MENSAJE = "Hola Compañera"

# ===== PAM5 =====
PAM5_LEVELS = np.array([-2, -1, 0, 1, 2], dtype=float)

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
        bits = np.append(bits, 0)
    symbols = []
    for i in range(0, len(bits), 2):
        pair = (int(bits[i]), int(bits[i+1]))
        symbols.append(ENC_MAP[pair])
    return np.array(symbols)

def split_4d(symbols):
    return symbols[0::4], symbols[1::4], symbols[2::4], symbols[3::4]

# ===== Transmisión =====
bits = np.array([int(b) for b in string_to_bits(MENSAJE)])
symbols = encode_pam5(bits)
A, B, C, D = split_4d(symbols)

# Agrupamos todo en una matriz (4 filas = 4 pares UTP)
matrix = np.vstack([A, B, C, D])

# Socket TCP cliente
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    print("[Tx] Conectado a la receptora")

    # Enviamos la matriz como bytes
    s.sendall(matrix.tobytes())
    print("[Tx] Mensaje transmitido:", MENSAJE)
