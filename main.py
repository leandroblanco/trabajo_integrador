# main.py — ESP32 Receptora: recibe del CANAL (5052), muestra crudo y reenvía a PC
import network, socket, time

# ===== CONFIG WIFI =====
SSID     = "UBP"        # tu red Wi-Fi
PASSWORD = "pascal25"    # reemplazá con tu clave real
USE_STATIC_IP = False         # dejamos que el router asigne IP

# ===== PUERTOS/IP =====
RX_BIND_IP   = "0.0.0.0"
RX_BIND_PORT = 5052           # recibe del CANAL
PC_HOST      = "10.0.1.40"  # IP de tu PC
PC_PORT      = 9000
RECV_CHUNK   = 4096

def ensure_wifi():
    sta = network.WLAN(network.STA_IF)
    if not sta.active():
        sta.active(True)
    if USE_STATIC_IP:
        sta.ifconfig(("192.168.1.50","255.255.255.0","192.168.1.1","8.8.8.8"))
    if not sta.isconnected():
        print("Conectando a Wi-Fi:", SSID)
        sta.connect(SSID, PASSWORD)
        while not sta.isconnected():
            time.sleep_ms(200)
    print("Wi-Fi OK:", sta.ifconfig())

class DestinoPC:
    def __init__(self, host, port):
        self.host, self.port = host, port
        self.sock = None

    def _connect(self):
        while True:
            try:
                s = socket.socket()
                s.connect((self.host, self.port))
                self.sock = s
                print("[PC] conectado →", (self.host, self.port))
                return
            except Exception as e:
                print("[PC] reconectando:", e)
                time.sleep(1.0)

    def send(self, data):
        if not data:
            return
        if self.sock is None:
            self._connect()
        try:
            self.sock.send(data)
        except Exception:
            try: self.sock.close()
            except: pass
            self.sock = None
            self._connect()
            self.sock.send(data)

def run_server():
    ensure_wifi()
    pc = DestinoPC(PC_HOST, PC_PORT)

    ls = socket.socket()
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind((RX_BIND_IP, RX_BIND_PORT))
    ls.listen(5)
    print("Receptora lista. Escuchando en", (RX_BIND_IP, RX_BIND_PORT))

    while True:
        conn, addr = ls.accept()
        print("CANAL conectado:", addr)
        try:
            while True:
                chunk = conn.recv(RECV_CHUNK)
                if not chunk:
                    print("CANAL desconectado")
                    break

                # Mostrar mensaje crudo
                print(f"[CRUDO] {len(chunk)} bytes:", chunk)

                # Reenviar a PC
                pc.send(chunk)
        except Exception as e:
            print("Error:", e)
        finally:
            try: conn.close()
            except: pass

run_server()