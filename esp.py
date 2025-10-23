# esp_intermedia_monitor.py - MicroPython para ESP32 (nodo intermedio)

import network
import socket
import time
import _thread
import random

# --- Config WiFi ---
SSID = "UBP"
PASSWORD = "pascal25"

# --- IPs y puertos ---
PC_ADMIN_IP = "10.0.0.143"
CONTROL_PORT = 5050
CHANNEL_PORT = 5051

RECEIVER_IP = "10.0.0.243"
RECEIVER_PORT = 5052

MONITOR_IP = "10.0.1.255"
MONITOR_PORT = 8100

# --- Estados ---
pc_sock = None
pc_lock = _thread.allocate_lock()
modo_error = False

# --- Conexión WiFi ---
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASSWORD)
print("Conectando a WiFi...")
while not wifi.isconnected():
    time.sleep(0.5)
print("✅ Conectado a WiFi. IP local:", wifi.ifconfig()[0])

# --- Función de error para símbolos PAM4 (0..3) ---
def introducir_error(data):
    # Probabilidad por byte de ser modificado (ajustable)
    PROB = 0.10  # 10%
    try:
        # Trabajamos sobre una copia mutable
        b = bytearray(data)
        for i in range(len(b)):
            if b[i] in (0, 1, 2, 3):  # solo PAM4 válidos
                if random.random() < PROB:
                    original = b[i]
                    opciones = [n for n in (0, 1, 2, 3) if n != original]
                    nuevo = random.choice(opciones)
                    b[i] = nuevo
                    print("⚠️ [ERROR] PAM4 modificado byte", i, ":", original, "->", nuevo)
        return bytes(b)
    except Exception as e:
        print("[WARN] introducir_error fallo:", e)
        return data

# --- Comunicación con PC administradora ---
def pc_control_client():
    global pc_sock, modo_error
    while True:
        try:
            s = socket.socket()
            s.connect((PC_ADMIN_IP, CONTROL_PORT))
            with pc_lock:
                pc_sock = s
            print("🖥️ Conectado con la PC administradora")
            # Avisamos IP
            try:
                s.sendall(("INFO:ESP_IP=" + wifi.ifconfig()[0] + "\n").encode())
            except:
                pass

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

# --- Reenvío a cualquier IP:PORT ---
def reenviar_a_esp(msg_bytes, ip, port):
    try:
        c = socket.socket()
        c.connect((ip, port))
        c.sendall(msg_bytes)
        c.close()
        print(f"[➡️] Reenviado a {ip}:{port}")
        with pc_lock:
            if pc_sock:
                try:
                    pc_sock.sendall(f"[OK] Reenviado a {ip}:{port}\n".encode())
                except:
                    pass
    except Exception as e:
        print(f"[⚠️] No se pudo reenviar a {ip}:{port}: {e}")
        with pc_lock:
            if pc_sock:
                try:
                    pc_sock.sendall(f"[ERROR] No se pudo reenviar a {ip}:{port}: {e}\n".encode())
                except:
                    pass

# --- Servidor del canal (recibe transmisores) ---
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

                # Mostrar crudo en consola ESP
                print("[TX] Mensaje recibido (crudo):", data)

                # Aplicar error (sobre PAM4) si está activado
                msg_modulado = introducir_error(data) if modo_error else data

                # Mostrar modulado en consola ESP
                print("[TX] Mensaje modulado:", msg_modulado)

                # Reenviar modulado a receptor y monitor
                reenviar_a_esp(msg_modulado, RECEIVER_IP, RECEIVER_PORT)
                reenviar_a_esp(msg_modulado, MONITOR_IP, MONITOR_PORT)

                # Enviar ambos a PC administradora (original + modulado)
                with pc_lock:
                    if pc_sock:
                        try:
                            pc_sock.sendall(b"CANAL (original): " + data + b"\n")
                        except:
                            pass
                        try:
                            pc_sock.sendall(b"CANAL (modulado): " + msg_modulado + b"\n")
                        except:
                            pass

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

# --- Mantener vivo ---
while True:
    time.sleep(1)
