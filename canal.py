import socket
import random
import numpy as np

# ------------------------
# Errores de canal
# ------------------------
def error_simbolos(pam4_data, prob_error=0.1):
    """Cambia símbolos PAM4 con cierta probabilidad"""
    pam4_mod = []
    for val in pam4_data:
        if random.random() < prob_error:
            nuevos_valores = [0, 1, 2, 3]
            nuevos_valores.remove(val)
            val = random.choice(nuevos_valores)
        pam4_mod.append(val)
    return pam4_mod

def error_gaussiano(pam4_data, sigma=0.5):
    """Agrega ruido gaussiano y redondea a niveles PAM4"""
    ruido = np.random.normal(0, sigma, len(pam4_data))
    return (np.array(pam4_data) + ruido).clip(0, 3).astype(int).tolist()

def error_atenuacion(pam4_data, factor=0.8):
    """Reduce amplitud de los símbolos"""
    return [min(3, max(0, int(val * factor))) for val in pam4_data]

def error_offset(pam4_data, offset=1):
    """Desplaza los niveles (cíclico)"""
    return [(val + offset) % 4 for val in pam4_data]

def error_jitter(pam4_data):
    """Simula jitter: duplica un símbolo y elimina otro"""
    if len(pam4_data) > 1:
        pam4_data.insert(0, pam4_data[0])  # repite primero
        pam4_data = pam4_data[:-1]         # elimina último
    return pam4_data

def error_reordenar(pam4_data):
    """Reordena aleatoriamente los símbolos sin modificarlos"""
    pam4_mod = pam4_data.copy()
    random.shuffle(pam4_mod)
    return pam4_mod

# ------------------------
# Gestor de canal
# ------------------------
def aplicar_canal(pam4_data, modo="ideal", **kwargs):
    if modo == "ideal":
        return pam4_data
    elif modo == "simbolos":
        return error_simbolos(pam4_data, kwargs.get("prob_error", 0.1))
    elif modo == "gauss":
        return error_gaussiano(pam4_data, kwargs.get("sigma", 0.5))
    elif modo == "atenuacion":
        return error_atenuacion(pam4_data, kwargs.get("factor", 0.8))
    elif modo == "offset":
        return error_offset(pam4_data, kwargs.get("offset", 1))
    elif modo == "jitter":
        return error_jitter(pam4_data)
    elif modo == "reordenar":
        return error_reordenar(pam4_data)
    else:
        return pam4_data

# ------------------------
# Canal TCP con opción de errores (bucle infinito)
# ------------------------
def main():
    # Configuración recepción (TX)
    ip_listen = '0.0.0.0'
    port_listen = 5000

    # Configuración reenvío (RX)
    ip_destino = '10.0.2.156'  # reemplazar por IP del RX
    port_destino = 5000

    # Tipo de error a aplicar
    modo_error = "simbolos"   # opciones: "ideal", "simbolos", "gauss", "atenuacion", "offset", "jitter", "reordenar"

    # Socket para recibir de TX
    sock_rx = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock_rx.bind((ip_listen, port_listen))
    sock_rx.listen(1)
    print(f"[CANAL] Esperando conexión TCP desde TX en {ip_listen}:{port_listen}...")

    while True:
        conn, addr = sock_rx.accept()
        with conn:
            print(f"[CANAL] Conectado desde {addr}")
            data = conn.recv(4096)
            if not data:
                print("[CANAL] No llegaron datos, cerrando conexión con TX.")
                continue

            pam4_data = list(data)
            print(f"[CANAL] Datos recibidos: {pam4_data}")

            # Aplicar error según configuración
            pam4_data_mod = aplicar_canal(pam4_data, modo=modo_error)

            if modo_error != "ideal":
                # Comparar y calcular errores
                errores = [(i, orig, mod) for i, (orig, mod) in enumerate(zip(pam4_data, pam4_data_mod)) if orig != mod]
                porcentaje = (len(errores) / len(pam4_data)) * 100 if pam4_data else 0
                print(f"[CANAL] Datos modificados ({modo_error}): {pam4_data_mod}")
                print(f"[CANAL] Porcentaje de error: {porcentaje:.2f}%")
                print(f"[CANAL] Errores en posiciones: {errores}")

            # Reenvío al RX
            try:
                sock_tx = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock_tx.connect((ip_destino, port_destino))
                sock_tx.sendall(bytes(pam4_data_mod))
                print(f"[CANAL] Datos reenviados a {ip_destino}:{port_destino}")
                sock_tx.close()
            except Exception as e:
                print(f"[CANAL] Error al reenviar: {e}")

if __name__ == "__main__":
    main()


