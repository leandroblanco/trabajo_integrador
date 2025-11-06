# esp_intermedia_monitor_persistente.py - MicroPython para ESP32 (nodo intermedio con sincronismo PAM4 persistente)

import network
import socket
import time
import _thread
import random

# --- Config WiFi ---
SSID = "UBP"
PASSWORD = "pascal25"

# --- IPs y puertos ---
PC_ADMIN_IP = "10.0.2.209"
CONTROL_PORT = 5050
CHANNEL_PORT = 5051
RECEIVER_IP = "10.0.2.239"
RECEIVER_PORT = 5052
MONITOR_IP = "10.0.2.193"
MONITOR_PORT = 8100

# --- Estados globales ---
pc_sock = None
pc_lock = _thread.allocate_lock()
modo_error = False

# --- Sockets persistentes ---
receiver_sock = None
monitor_sock = None
receiver_lock = _thread.allocate_lock()
monitor_lock = _thread.allocate_lock()

# --- Prefijo "hola" en PAM4 (16 símbolos) ---
PREFIJO_HOLA = [1, 2, 2, 0,
                1, 2, 3, 3,
                1, 2, 3, 0,
                1, 2, 0, 1]

# --- Conexión WiFi ---
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASSWORD)
print("Conectando a WiFi...")
while not wifi.isconnected():
    time.sleep(0.5)
print("✅ Conectado a WiFi. IP local:", wifi.ifconfig()[0])


# --- Decodificación PAM4 ---
def decodificar_pam4(data):
    simbolos = []
    for b in data:
        simbolos.append((b >> 6) & 0b11)
        simbolos.append((b >> 4) & 0b11)
        simbolos.append((b >> 2) & 0b11)
        simbolos.append(b & 0b11)
    return simbolos


# --- Introducir errores aleatorios (protegiendo el prefijo "hola") ---
def introducir_error(simbolos):
    PROB = 0.10
    total = len(simbolos)

    # Verificar si el paquete contiene el prefijo al inicio
    tiene_prefijo = (total >= 16 and simbolos[:16] == PREFIJO_HOLA)

    if tiene_prefijo:
        print("🟢 Prefijo 'hola' detectado — sincronismo correcto.")
        inicio_datos = 16  # después del hola
    else:
        print("⚠️ Prefijo 'hola' NO detectado — se aplican errores a todo.")
        inicio_datos = 0

    for i in range(inicio_datos, total):
        if random.random() < PROB:
            original = simbolos[i]
            opciones = [n for n in (0, 1, 2, 3) if n != original]
            simbolos[i] = random.choice(opciones)
            print(f"⚠️ [ERROR] símbolo {i}: {original} -> {simbolos[i]}")

    return simbolos


# --- Reensamblar símbolos ---
def empaquetar_pam4(simbolos):
    b = bytearray()
    for i in range(0, len(simbolos), 4):
        grupo = simbolos[i:i + 4]
        while len(grupo) < 4:
            grupo.append(0)
        val = (grupo[0] << 6) | (grupo[1] << 4) | (grupo[2] << 2) | grupo[3]
        b.append(val)
    return bytes(b)


# --- Cliente con la PC administradora ---
def pc_control_client():
    global pc_sock, modo_error
    while True:
        try:
            s = socket.socket()
            s.connect((PC_ADMIN_IP, CONTROL_PORT))
            with pc_lock:
                pc_sock = s
            print("🖥️ Conectado con la PC administradora")
            s.sendall(("INFO:ESP_IP=" + wifi.ifconfig()[0] + "\n").encode())

            while True:
                data = s.recv(1024)
                if not data:
                    break
                cmd = data.decode().strip()
                if cmd == "MODO_ERROR_ON":
                    modo_error = True
                    print("[⚠️] Modo error ACTIVADO")
                elif cmd == "MODO_ERROR_OFF":
                    modo_error = False
                    print("[✅] Modo error DESACTIVADO")

        except Exception as e:
            print("[❌] Error conexión con Admin:", e)
        finally:
            try:
                s.close()
            except:
                pass
            with pc_lock:
                pc_sock = None
            time.sleep(5)


# --- Clientes persistentes receptor y monitor ---
def receptor_client():
    global receiver_sock
    while True:
        try:
            print("🔌 Conectando con el receptor...")
            s = socket.socket()
            s.connect((RECEIVER_IP, RECEIVER_PORT))
            with receiver_lock:
                receiver_sock = s
            print("✅ Conectado con el receptor.")
            while True:
                time.sleep(1)
                s.send(b'')  # mantener viva la conexión
        except Exception as e:
            print("[⚠️] Receptor desconectado:", e)
        finally:
            try:
                s.close()
            except:
                pass
            with receiver_lock:
                receiver_sock = None
            time.sleep(3)


def monitor_client():
    global monitor_sock
    while True:
        try:
            print("📡 Conectando con el monitor...")
            s = socket.socket()
            s.connect((MONITOR_IP, MONITOR_PORT))
            with monitor_lock:
                monitor_sock = s
            print("✅ Conectado con el monitor.")
            while True:
                time.sleep(1)
                s.send(b'')
        except Exception as e:
            print("[⚠️] Monitor desconectado:", e)
        finally:
            try:
                s.close()
            except:
                pass
            with monitor_lock:
                monitor_sock = None
            time.sleep(3)


# --- Enviar datos ---
def enviar_datos_persistentes(msg_bytes):
    global receiver_sock, monitor_sock

    with receiver_lock:
        if receiver_sock:
            try:
                receiver_sock.sendall(msg_bytes)
                print(f"[➡️] Enviado al receptor ({len(msg_bytes)} bytes)")
            except Exception as e:
                print("[⚠️] Error enviando al receptor:", e)
                receiver_sock = None
        else:
            print("[⛔] Receptor no conectado")

    with monitor_lock:
        if monitor_sock:
            try:
                monitor_sock.sendall(msg_bytes)
                print(f"[➡️] Enviado al monitor ({len(msg_bytes)} bytes)")
            except Exception as e:
                print("[⚠️] Error enviando al monitor:", e)
                monitor_sock = None
        else:
            print("[⛔] Monitor no conectado")


# --- Calcular histograma ---
def histograma_pam4(simbolos):
    counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for s in simbolos:
        counts[s] += 1
    total = len(simbolos)
    print(f"\n📊 [HISTOGRAMA PAM4] Total: {total} símbolos")
    for nivel in (0, 1, 2, 3):
        print(f"   Nivel {nivel}: {counts[nivel]}")
    print()


# --- Servidor del canal ---
def canal_server():
    s = socket.socket()
    s.bind(('', CHANNEL_PORT))
    s.listen(5)
    print(f"[📡] Esperando transmisores en puerto {CHANNEL_PORT}...")

    while True:
        try:
            conn, addr = s.accept()
            print("[TX] Conexión desde", addr)
            try:
                data = conn.recv(2048)
                if not data:
                    conn.close()
                    continue

                simbolos = decodificar_pam4(data)
                print(f"[TX] Paquete recibido ({len(simbolos)} símbolos).")

                histograma_pam4(simbolos)

                if modo_error:
                    simbolos = introducir_error(simbolos)
                else:
                    print("✅ Modo error desactivado (sin alteraciones).")

                msg_modulado = empaquetar_pam4(simbolos)
                enviar_datos_persistentes(msg_modulado)

                with pc_lock:
                    if pc_sock:
                        pc_sock.sendall(b"[INFO] Paquete PAM4 procesado\n")

            except Exception as e:
                print("[Error canal interno]:", e)
            finally:
                try:
                    conn.close()
                except:
                    pass
        except Exception as e:
            print("[Error aceptando conexión]:", e)
            time.sleep(0.05)


# --- Lanzar hilos ---
_thread.start_new_thread(pc_control_client, ())
_thread.start_new_thread(canal_server, ())
_thread.start_new_thread(receptor_client, ())
_thread.start_new_thread(monitor_client, ())

# --- Mantener vivo ---
while True:
    time.sleep(1)

