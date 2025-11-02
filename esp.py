# esp_intermedia_monitor.py - MicroPython para ESP32 (nodo intermedio)

import network
import socket   # Un socket es como un "enchufe virtual" de red que permite la comunicación entre dispositivos.
import time
import _thread
import random

# --- Config WiFi ---
SSID = "UBP"
PASSWORD = "pascal25"

# --- IPs y puertos ---
PC_ADMIN_IP = "10.0.0.59"    # IP de la PC administradora (control)
CONTROL_PORT = 5050              # Puerto de control con la PC administradora
CHANNEL_PORT = 5051              # Puerto por donde llegan los transmisores

RECEIVER_IP = "10.0.2.240"    # IP del receptor final
RECEIVER_PORT = 5052             # Puerto del receptor

MONITOR_IP = "10.0.0.185"     # IP del monitor (puede ser broadcast)
MONITOR_PORT = 8100              # Puerto del monitor

# --- Estados globales ---
pc_sock = None                    # Socket activo con la PC administradora
pc_lock = _thread.allocate_lock() # Lock para acceso seguro a pc_sock entre hilos
modo_error = False                # Bandera para activar/desactivar errores PAM4

# --- Conexión WiFi ---
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASSWORD)
print("Conectando a WiFi...")
while not wifi.isconnected():
    time.sleep(0.5)
print("✅ Conectado a WiFi. IP local:", wifi.ifconfig()[0])

# --- Función para introducir errores aleatorios en símbolos PAM4 ---
def introducir_error(data):
    PROB = 0.10  # Probabilidad del 10% de error por símbolo
    try:
        b = bytearray(data)  # Convertimos a formato mutable
        for i in range(len(b)):
            # Solo se modifican símbolos válidos PAM4 (0,1,2,3)
            if b[i] in (0, 1, 2, 3):
                if random.random() < PROB:  # Si cae dentro del 10%...
                    original = b[i]
                    # Elegimos un valor distinto al original
                    opciones = [n for n in (0, 1, 2, 3) if n != original]
                    nuevo = random.choice(opciones)
                    b[i] = nuevo
                    print("⚠️ [ERROR] PAM4 modificado byte", i, ":", original, "->", nuevo)
        return bytes(b)  # Devolvemos los datos con posibles errores
    except Exception as e:
        print("[WARN] introducir_error fallo:", e)
        return data  # Si algo falla, devolvemos los datos originales

# --- Hilo cliente que mantiene comunicación con la PC administradora ---
def pc_control_client():
    global pc_sock, modo_error
    while True:
        try:
            # Conexión TCP hacia la PC administradora
            s = socket.socket()
            s.connect((PC_ADMIN_IP, CONTROL_PORT))
            with pc_lock:
                pc_sock = s
            print("🖥️ Conectado con la PC administradora")

            # Enviar información de IP local del ESP32
            try:
                s.sendall(("INFO:ESP_IP=" + wifi.ifconfig()[0] + "\n").encode())
            except:
                pass

            # Escuchar comandos de la PC (activar/desactivar error)
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
            # Si se pierde la conexión, se limpia el socket y se reintenta
            try:
                s.close()
            except:
                pass
            with pc_lock:
                pc_sock = None
            time.sleep(5)  # Esperar antes de reconectar

# --- Función para reenviar datos binarios a otra ESP o dispositivo ---
def reenviar_a_esp(msg_bytes, ip, port):
    try:
        # Conexión TCP con destino
        c = socket.socket()
        c.connect((ip, port))

        # 🔹 Envío directo de bytes (NO texto)
        c.sendall(msg_bytes)
        c.close()
        print(f"[➡️] Reenviado a {ip}:{port} (datos binarios)")

        # Avisar a la PC administradora que se reenviaron los datos
        with pc_lock:
            if pc_sock:
                try:
                    pc_sock.sendall(f"[OK] Reenviado a {ip}:{port}\n".encode())
                except:
                    pass
    except Exception as e:
        print(f"[⚠️] No se pudo reenviar a {ip}:{port}: {e}")
        # Informar error de reenvío a la PC administradora
        with pc_lock:
            if pc_sock:
                try:
                    pc_sock.sendall(f"[ERROR] No se pudo reenviar a {ip}:{port}: {e}\n".encode())
                except:
                    pass

# --- Servidor del canal: recibe datos del transmisor ---
def canal_server():
    s = socket.socket()
    s.bind(('', CHANNEL_PORT))  # Escucha en el puerto del canal
    s.listen(5)
    print(f"[📡] Esperando transmisores en puerto {CHANNEL_PORT}...")

    while True:
        try:
            # Aceptar conexión entrante (transmisor)
            conn, addr = s.accept()
            print("[TX] Conexión desde", addr)
            try:
                data = conn.recv(2048)  # Recibir datos PAM4 en binario
                if not data:
                    conn.close()
                    continue

                # Mostrar mensaje original recibido (en formato hexadecimal)
                print("[TX] Mensaje recibido (crudo):", " ".join(f"{b:02X}" for b in data))

                # Si el modo error está activo, se alteran los símbolos PAM4
                msg_modulado = introducir_error(data) if modo_error else data

                # Mostrar mensaje modificado
                print("[TX] Mensaje modulado:", " ".join(f"{b:02X}" for b in msg_modulado))

                # 🔹 Reenviar el mensaje (modificado o no) en BINARIO al receptor y al monitor
                reenviar_a_esp(msg_modulado, RECEIVER_IP, RECEIVER_PORT)
                reenviar_a_esp(msg_modulado, MONITOR_IP, MONITOR_PORT)

                # También enviar a la PC administradora (solo para log, como texto)
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

# --- Lanzar los hilos principales ---
_thread.start_new_thread(pc_control_client, ())  # Hilo para hablar con la PC admin
_thread.start_new_thread(canal_server, ())       # Hilo servidor que recibe transmisores

# --- Bucle principal para mantener el programa vivo ---
while True:
    time.sleep(1)
