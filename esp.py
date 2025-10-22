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

# --- Función de error solo para dígitos 0-7 ---
def introducir_error(data):
    if len(data) == 0:
        return data
    PROB = 0.10
    try:
        if all(b < 128 for b in data):
            s = data.decode('ascii')
            s_list = list(s)
            for i, ch in enumerate(s_list):
                if ch in '01234567' and random.random() < PROB:
                    choices = [c for c in '01234567' if c != ch]
                    new_ch = random.choice(choices)
                    s_list[i] = new_ch
                    print(f"⚠️ [ERROR] Dígito modificado posición {i}: {ch} -> {new_ch}")
            return ''.join(s_list).encode('ascii')
    except:
        return data
    return data

# --- Comunicación con PC ---
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
        except:
            pass
        finally:
            try: s.close()
            except: pass
            with pc_lock: pc_sock = None
            time.sleep(5)

# --- Reenvío a receptor/monitor ---
def reenviar_a_esp(msg_bytes, ip, port):
    try:
        c = socket.socket()
        c.connect((ip, port))
        c.sendall(msg_bytes)
        c.close()
        print(f"[➡️] Reenviado a {ip}:{port}")
        with pc_lock:
            if pc_sock: pc_sock.sendall(f"[OK] Reenviado a {ip}:{port}\n".encode())
    except Exception as e:
        print(f"[⚠️] No se pudo reenviar a {ip}:{port}: {e}")
        with pc_lock:
            if pc_sock: pc_sock.sendall(f"[ERROR] {e}\n".encode())

# --- Servidor canal ---
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
                if not data: continue
                msg_modulado = introducir_error(data) if modo_error else data
                # Reenvío
                reenviar_a_esp(msg_modulado, RECEIVER_IP, RECEIVER_PORT)
                reenviar_a_esp(msg_modulado, MONITOR_IP, MONITOR_PORT)
                # Enviar a PC admin ambos
                with pc_lock:
                    if pc_sock:
                        pc_sock.sendall(b"CANAL (original): " + data + b"\n")
                        pc_sock.sendall(b"CANAL (modulado): " + msg_modulado + b"\n")
            finally:
                conn.close()
        except:
            pass
        time.sleep(0.05)

# --- Lanzar hilos ---
_thread.start_new_thread(pc_control_client, ())
_thread.start_new_thread(canal_server, ())

# --- Mantener vivo ---
while True:
    time.sleep(1)
