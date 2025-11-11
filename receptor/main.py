# main.py -- ESP32 Receptor
# Recibe bytes desde el CANAL y reenvía frames de 68 bytes a la PC en streaming.
#
# Formato de cada frame:
#   0..3  -> 'h','o','l','a'   (cabecera)
#   4..67 -> 64 amplitudes 0..255

import network
import usocket as socket
import time

# ========= CONFIG WiFi =========
SSID = "UBP"
PASS = "pascal25"

# ESP32 <-- CANAL (servidor)
IP_RX   = "0.0.0.0"
PORT_RX = 5052           # puerto donde escucha al canal (coincide con RECEIVER_PORT)

# ESP32 --> PC RECEPTORA (cliente persistente)
PC_IP      = "10.0.0.131"   # IPv4 de tu PC receptora
PC_PORT_TX = 9100           # puerto donde escucha tu script de PC

FRAME_BYTES = 68            # "hola" (4) + 64 amplitudes

pc_sock = None  # socket persistente hacia la PC


def wifi_connect():
    sta = network.WLAN(network.STA_IF)
    if not sta.active():
        sta.active(True)
    print("Conectando a WiFi...")
    if not sta.isconnected():
        sta.connect(SSID, PASS)
        t0 = time.ticks_ms()
        while not sta.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > 20000:
                raise RuntimeError("Timeout WiFi (revisá SSID/clave)")
            time.sleep_ms(200)
    print("OK WiFi:", sta.ifconfig())


def conectar_pc():
    """Conexión PERSISTENTE ESP32 -> PC. Reintenta hasta lograrlo."""
    global pc_sock
    if pc_sock:
        try:
            pc_sock.close()
        except:
            pass
        pc_sock = None

    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((PC_IP, PC_PORT_TX))
            s.settimeout(None)
            pc_sock = s
            print("✅ Conectado en forma persistente a PC {}:{}".format(PC_IP, PC_PORT_TX))
            return
        except Exception as e:
            print("⚠️ No puedo conectar a PC {}:{} -> {} (reintento en 2s)".format(
                PC_IP, PC_PORT_TX, e
            ))
            try:
                s.close()
            except:
                pass
            time.sleep(2)


def enviar_frame_a_pc_stream(frame_bytes):
    """
    Envía un frame de 68 bytes a la PC usando la conexión persistente.
    Si se rompe la conexión, reconecta y reintenta una vez.
    """
    global pc_sock

    if not pc_sock:
        conectar_pc()

    for intento in range(2):
        try:
            pc_sock.sendall(frame_bytes)
            print("▶ frame (68 bytes) enviado a PC")
            return
        except Exception as e:
            print("⚠️ error enviando a PC:", e)
            try:
                pc_sock.close()
            except:
                pass
            pc_sock = None
            if intento == 0:
                print("🔄 Reintentando conexión con la PC...")
                conectar_pc()
            else:
                print("⛔ No se pudo reenviar el frame a la PC")
                return


def main():
    wifi_connect()
    conectar_pc()  # conexión persistente con la PC

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((IP_RX, PORT_RX))
        srv.listen(1)
        print("📡 ESP32 escuchando al CANAL en {}:{}".format(IP_RX, PORT_RX))
        print("↩️  Reenviará frames de 68 bytes a {}:{} (conexión persistente)".format(
            PC_IP, PC_PORT_TX
        ))

        while True:
            print("⏳ Esperando conexión del CANAL...")
            conn, addr = srv.accept()
            print("🔗 Conexión desde {}".format(addr))

            buf = bytearray()

            try:
                # SIN timeout: la conexión con el canal se mantiene
                while True:
                    chunk = conn.recv(1024)
                    if not chunk:
                        print("⚠️ Conexión del canal cerrada por el otro lado")
                        break

                    # acumular bytes crudos del canal
                    buf.extend(chunk)

                    # mientras haya al menos 68 bytes, armar frames completos
                    while len(buf) >= FRAME_BYTES:
                        frame = bytes(buf[:FRAME_BYTES])
                        buf = buf[FRAME_BYTES:]   # mover ventana en el buffer

                        print("🧱 frame crudo(68B):", list(frame))
                        enviar_frame_a_pc_stream(frame)

            except Exception as e:
                print("⚠️ error RX desde el canal:", e)
            finally:
                try:
                    conn.close()
                except:
                    pass
                print("⏹ Conexión con el canal cerrada, esperando otra…")

    finally:
        try:
            srv.close()
        except:
            pass
        if pc_sock:
            try:
                pc_sock.close()
            except:
                pass


if __name__ == "__main__":
    main()
