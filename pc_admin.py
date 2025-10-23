import socket
import threading

HOST = '0.0.0.0'
CONTROL_PORT = 5050

esp_conn = None
esp_addr = None
esp_lock = threading.Lock()

modo_error = False  # Nuevo: estado de error en memoria

def esp_acceptor():
    global esp_conn, esp_addr
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, CONTROL_PORT))
    server.listen(1)
    print(f"[ADMIN] Esperando conexión de la ESP en {HOST}:{CONTROL_PORT} ...")

    while True:
        conn, addr = server.accept()
        with esp_lock:
            if esp_conn:
                try:
                    esp_conn.close()
                except:
                    pass
            esp_conn = conn
            esp_addr = addr
        print(f"[ADMIN] ESP conectada desde {addr[0]}:{addr[1]}")
        threading.Thread(target=esp_receiver, args=(conn, addr), daemon=True).start()

def esp_receiver(conn, addr):
    global modo_error
    try:
        while True:
            data = conn.recv(2048)
            if not data:
                break

            lines = data.split(b'\n')
            for line in lines:
                if not line:
                    continue

                if line.startswith(b'CANAL (crudo):'):
                    payload = line[len(b'CANAL (crudo):'):].strip()
                    hex_str = ' '.join(f'{b:02X}' for b in payload)
                    print("\n🛰️ --- MENSAJE DEL CANAL (CRUDO) ---")
                    print(hex_str)
                    continue

                if line.startswith(b'CANAL (modulado):'):
                    payload = line[len(b'CANAL (modulado):'):].strip()
                    hex_str = ' '.join(f'{b:02X}' for b in payload)
                    print("\n♻️ --- MENSAJE DEL CANAL (MODULADO) ---")
                    print(hex_str)
                    continue

                if b'[OK]' in line:
                    print("\n[INFO] Reenvío: ✅ Correcto")
                elif b'[ERROR]' in line:
                    print(f"\n[INFO] Reenvío: ❌ {line.decode(errors='ignore')}")
                elif b'MODO_ERROR_ON' in line:
                    modo_error = True
                    print("[ADMIN] ⚠️ Modo error ACTIVADO")
                elif b'MODO_ERROR_OFF' in line:
                    modo_error = False
                    print("[ADMIN] ✅ Modo error DESACTIVADO")
                else:
                    print(f"\n[INFO] {line.decode(errors='ignore')}")

    except Exception as e:
        print(f"[ERROR] Receiver: {e}")
    finally:
        with esp_lock:
            if esp_conn == conn:
                esp_conn = None
                esp_addr = None
        print(f"[ADMIN] Conexión cerrada desde {addr[0]}")

def enviar_a_esp(msg):
    with esp_lock:
        if not esp_conn:
            print("No hay ESP conectada.")
            return False
        try:
            esp_conn.sendall((msg + "\n").encode())
            return True
        except Exception as e:
            print("Error enviando a ESP:", e)
            return False

def main_menu():
    global modo_error
    while True:
        print("\n--- ADMINISTRADOR ---")
        with esp_lock:
            ip = esp_addr[0] if esp_addr else "NINGUNA"
        print("IP ESP:", ip)
        print("Modo error actual:", "ACTIVADO ✅" if modo_error else "DESACTIVADO ❌")
        print("1) Solicitar INFO de la ESP")
        print("2) Activar MODO ERROR (modificación PAM4)")
        print("3) Desactivar MODO ERROR")
        print("4) Salir")

        op = input("Opción: ").strip()
        if op == "1":
            enviar_a_esp("info")
        elif op == "2":
            modo_error = True
            enviar_a_esp("MODO_ERROR_ON")
            print("[ADMIN] ✅ Modo error ACTIVADO.")
        elif op == "3":
            modo_error = False
            enviar_a_esp("MODO_ERROR_OFF")
            print("[ADMIN] ❌ Modo error DESACTIVADO.")
        elif op == "4":
            break
        else:
            print("Opción inválida.")

if __name__ == "__main__":
    threading.Thread(target=esp_acceptor, daemon=True).start()
    main_menu()
