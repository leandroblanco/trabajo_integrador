import socket
import time

# PC <-- ESP32
HOST = "0.0.0.0"
PORT = 9100

FRAME_BYTES = 68

# PC --> VISUALIZADOR
VIS_IP   = "10.0.1.173"
VIS_PORT = 8100

def now():
    return time.strftime("%H:%M:%S")

def decodificar_pam4(data_bytes):  #se decodifica en PAM4 los bloques fijos de datos 
    simbolos = []
    for b in data_bytes:
        simbolos.append((b >> 6) & 0b11)
        simbolos.append((b >> 4) & 0b11)
        simbolos.append((b >> 2) & 0b11)
        simbolos.append(b & 0b11)
    return simbolos

class VisualizadorConn:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None

    def close(self):
        try:
            if self.sock:
                self.sock.close()
        except:
            pass
        self.sock = None

    def _connect(self):
        self.close()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((self.host, self.port))
        s.settimeout(None)
        self.sock = s
        print(f"[{now()}] ✅ conectado al visualizador {self.host}:{self.port}")

    def ensure(self):
        if self.sock is not None:
            return
        backoff = [1, 2, 4, 8, 10]
        for t in backoff:
            try:
                self._connect()
                return
            except Exception as e:
                print(f"[{now()}] ⚠ no se pudo conectar al visualizador: {e} (reintento en {t}s)")
                time.sleep(t)
        while True:
            try:
                self._connect()
                return
            except Exception as e:
                print(f"[{now()}] ⚠ reintento visualizador en 10s: {e}")
                time.sleep(10)

    def send_bytes(self, data: bytes):
        if not data:
            return
        try:
            self.ensure()
            self.sock.sendall(data)
            print(f"[{now()}] ▶ reenviado al visualizador ({len(data)}B)")
        except Exception as e:
            print(f"[{now()}] ⚠ error enviando al visualizador: {e}")
            self.close()

def process_frame(frame_bytes: bytes, frame_idx: int, vis: VisualizadorConn):
    if len(frame_bytes) != FRAME_BYTES:
        print(f"[{now()}] ⚠ frame {frame_idx} con tamaño inesperado: {len(frame_bytes)}B")
        return

    header = frame_bytes[:4]   #toma los primeros 4 bytes del bloque fijo (asumimos que es el hola) 
    try:
        header_txt = header.decode("latin1")
    except Exception:
        header_txt = repr(list(header))

    print(f"[{now()}] Frame {frame_idx}: cabecera = {header_txt!r}")   #Los muestra por pantalla como cabecera:

    simbolos = decodificar_pam4(frame_bytes)
    print(f"[{now()}] 🧠 Símbolos PAM4 decodificados ({len(simbolos)}):")
    print("   ", simbolos)
    print()

    vis.send_bytes(frame_bytes)

def main():
    frame_idx = 0
    vis = VisualizadorConn(VIS_IP, VIS_PORT)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        print(f"[{now()}] PC escuchando a ESP32 en {HOST}:{PORT}")

        while True:
            print(f"[{now()}] ⏳ Esperando conexión de ESP32...")
            conn, addr = s.accept()
            print(f"[{now()}] 🔗 Conectado desde {addr}")

            bin_buf = bytearray()

            with conn:
                conn.settimeout(10)
                while True:
                    try:
                        data = conn.recv(4096)
                    except socket.timeout:
                        print(f"[{now()}] ⏱ Timeout de recepción, cierro conexión y espero otra")
                        break

                    if not data:
                        print(f"[{now()}] ⚠ Conexión cerrada por la ESP32")
                        break

                    bin_buf.extend(data)

                    while len(bin_buf) >= FRAME_BYTES:
                        frame = bytes(bin_buf[:FRAME_BYTES])
                        del bin_buf[:FRAME_BYTES]
                        frame_idx += 1
                        process_frame(frame, frame_idx, vis)

if __name__ == "__main__":
    main()
