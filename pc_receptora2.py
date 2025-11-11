# pc_pam4_server_forward.py — PC: recibe crudo de ESP32, demod PAM4 en streaming con warmup, reenvía a Viewer
import socket, time

LISTEN_IP   = "0.0.0.0"
LISTEN_PORT = 9000         # recibe de la ESP32
VIEW_HOST   = "10.0.1.255" # IP del visualizador (ajustar si es necesario)
VIEW_PORT   = 8100
RECV_CHUNK  = 4096

LEVEL_TO_BITS_PAM4 = {0:(0,0), 1:(0,1), 2:(1,1), 3:(1,0)}

# ----- Demod adaptativa con warmup -----
class PAM4Demod:
    def __init__(self, alpha=0.02, warmup=50):
        self.alpha = alpha
        self.vmin = 255.0
        self.vmax = 0.0
        self._recalc()
        self.warmup = warmup   # cantidad de símbolos a descartar
        self.count = 0

    def _ema(self, old, new): 
        return (1.0 - self.alpha)*old + self.alpha*new

    def _recalc(self):
        span = max(1.0, self.vmax - self.vmin)
        step = span / 4.0
        self.t1 = self.vmin + step
        self.t2 = self.vmin + 2*step
        self.t3 = self.vmin + 3*step

    def level(self, s):
        x = float(s)
        if x < self.vmin: 
            self.vmin = self._ema(self.vmin, x)
        if x > self.vmax: 
            self.vmax = self._ema(self.vmax, x)
        self._recalc()

        # Durante warmup, solo calibramos
        if self.count < self.warmup:
            self.count += 1
            return None  

        # Clasificación normal
        if x < self.t1: return 0
        if x < self.t2: return 1
        if x < self.t3: return 2
        return 3

    def bits_from_sample(self, s):
        lvl = self.level(s)
        if lvl is None:
            return None  # todavía en warmup
        return LEVEL_TO_BITS_PAM4[lvl]

# ----- Utilidades -----
def pack_bits_to_bytes(bits):
    out, buf, n = bytearray(), 0, 0
    for bit in bits:
        buf = (buf << 1) | (bit & 1)
        n += 1
        if n == 8:
            out.append(buf & 0xFF)
            buf, n = 0, 0
    if n: out.append((buf << (8-n)) & 0xFF)
    return out

def ascii_preview(b, maxlen=80):
    try:
        s = b.decode("utf-8", "ignore")
        s = "".join(ch if 32 <= ord(ch) <= 126 else "." for ch in s)
        return s[:maxlen]
    except:
        return ""

# ----- Cliente al VISUALIZADOR -----
class ViewerSink:
    def __init__(self, host, port):
        self.host, self.port = host, port
        self.sock = None
    def _connect(self):
        while True:
            try:
                s = socket.socket()
                s.connect((self.host, self.port))
                self.sock = s
                print("[VIEWER] conectado →", (self.host, self.port))
                return
            except Exception as e:
                print("[VIEWER] reconectando:", e)
                time.sleep(1.0)
    def send(self, data):
        if not data: return
        if self.sock is None: self._connect()
        try: self.sock.send(data)
        except:
            try: self.sock.close()
            except: pass
            self.sock = None
            self._connect()
            self.sock.send(data)

# ----- Servidor en PC -----
def main():
    viewer = ViewerSink(VIEW_HOST, VIEW_PORT)
    dem = PAM4Demod(alpha=0.02, warmup=50)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((LISTEN_IP, LISTEN_PORT))
    srv.listen(5)
    print(f"[PC] Escuchando en {LISTEN_IP}:{LISTEN_PORT}")

    while True:
        conn, addr = srv.accept()
        print("[PC] Conexión desde", addr)
        try:
            while True:
                chunk = conn.recv(RECV_CHUNK)
                if not chunk:
                    break

                # Mostrar crudo en tiempo real
                print(f"[PC][CRUDO] {len(chunk)} bytes")
                print(" hex:", chunk.hex(" ")[:120])
                ap = ascii_preview(chunk)
                if ap: print(" asc:", ap)

                # Demodular en tiempo real
                out_bits = []
                for s in chunk:
                    bits = dem.bits_from_sample(s)
                    if bits is None:
                        continue  # todavía en warmup
                    b0, b1 = bits
                    out_bits += [b0, b1]

                if out_bits:
                    out = pack_bits_to_bytes(out_bits)
                    print(f"[PC][DEMOD] {len(out)} bytes")
                    print(" hex:", out.hex(" ")[:120])
                    ap2 = ascii_preview(out)
                    if ap2: print(" asc:", ap2)

                    # Reenviar al visualizador
                    viewer.send(out)

        except Exception as e:
            print("[PC] Error:", e)
        finally:
            try: conn.close()
            except: pass

if __name__ == "__main__":
    main()