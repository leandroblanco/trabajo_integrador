import socket #Un socket es como un enchufe de red (una conexión virtual)
#que permite que dos dispositivos se comuniquen entre sí en una red (por WiFi o Ethernet).
import threading

# --- Configuración del servidor administrador ---
HOST = '0.0.0.0'        # Escucha en todas las interfaces de red disponibles
CONTROL_PORT = 5050     # Puerto donde espera conexión desde la ESP32

# --- Variables globales para conexión con la ESP ---
esp_conn = None          # Objeto socket de la ESP conectada
esp_addr = None          # Dirección IP/puerto de la ESP
esp_lock = threading.Lock()  # Lock para evitar conflictos entre hilos

modo_error = False       # Bandera local para saber si el modo error está activado

# --- Hilo que acepta conexiones entrantes desde la ESP32 ---
def esp_acceptor():
    global esp_conn, esp_addr

    # Crear socket TCP del servidor
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Permite reusar el puerto
    server.bind((HOST, CONTROL_PORT))  # Asociar IP/puerto
    server.listen(1)  # Aceptar una conexión a la vez
    print(f"[ADMIN] Esperando conexión de la ESP en {HOST}:{CONTROL_PORT} ...")

    # Bucle infinito para aceptar conexiones
    while True:
        conn, addr = server.accept()  # Espera a que la ESP se conecte
        with esp_lock:
            # Si ya hay una ESP conectada, cerrar la conexión anterior
            if esp_conn:
                try:
                    esp_conn.close()
                except:
                    pass
            esp_conn = conn  # Guardar el nuevo socket
            esp_addr = addr  # Guardar la dirección IP de la ESP
        print(f"[ADMIN] ESP conectada desde {addr[0]}:{addr[1]}")
        # Crear hilo receptor para manejar los mensajes entrantes
        threading.Thread(target=esp_receiver, args=(conn, addr), daemon=True).start()

# --- Hilo que recibe mensajes desde la ESP ---
def esp_receiver(conn, addr):
    global modo_error
    try:
        while True:
            data = conn.recv(2048)  # Espera datos de la ESP
            if not data:
                break  # Si la conexión se cerró, salir

            # Los datos pueden venir en varias líneas, separadas por "\n"
            lines = data.split(b'\n')
            for line in lines:
                if not line:
                    continue  # Ignora líneas vacías

                # --- Caso 1: mensaje crudo recibido del canal ---
                if line.startswith(b'CANAL (crudo):'):
                    payload = line[len(b'CANAL (crudo):'):].strip()
                    # Mostrar en formato hexadecimal para ver los bytes
                    hex_str = ' '.join(f'{b:02X}' for b in payload)
                    print("\n🛰️ --- MENSAJE DEL CANAL (CRUDO) ---")
                    print(hex_str)
                    continue

                # --- Caso 2: mensaje modulado (con error) ---
                if line.startswith(b'CANAL (modulado):'):
                    payload = line[len(b'CANAL (modulado):'):].strip()
                    hex_str = ' '.join(f'{b:02X}' for b in payload)
                    print("\n♻️ --- MENSAJE DEL CANAL (MODULADO) ---")
                    print(hex_str)
                    continue

                # --- Caso 3: respuestas del ESP sobre reenvíos ---
                if b'[OK]' in line:
                    print("\n[INFO] Reenvío: ✅ Correcto")
                elif b'[ERROR]' in line:
                    print(f"\n[INFO] Reenvío: ❌ {line.decode(errors='ignore')}")
                # --- Caso 4: mensajes de control del modo error ---
                elif b'MODO_ERROR_ON' in line:
                    modo_error = True
                    print("[ADMIN] ⚠️ Modo error ACTIVADO")
                elif b'MODO_ERROR_OFF' in line:
                    modo_error = False
                    print("[ADMIN] ✅ Modo error DESACTIVADO")
                # --- Caso 5: otros mensajes informativos ---
                else:
                    print(f"\n[INFO] {line.decode(errors='ignore')}")

    except Exception as e:
        print(f"[ERROR] Receiver: {e}")
    finally:
        # Si la ESP se desconecta, limpiar variables globales
        with esp_lock:
            if esp_conn == conn:
                esp_conn = None
                esp_addr = None
        print(f"[ADMIN] Conexión cerrada desde {addr[0]}")

# --- Función para enviar comandos o mensajes a la ESP ---
def enviar_a_esp(msg):
    with esp_lock:
        if not esp_conn:
            print("No hay ESP conectada.")
            return False
        try:
            esp_conn.sendall((msg + "\n").encode())  # Envía el comando al ESP
            return True
        except Exception as e:
            print("Error enviando a ESP:", e)
            return False

# --- Menú principal interactivo en consola ---
def main_menu():
    global modo_error
    while True:
        print("\n--- ADMINISTRADOR ---")
        with esp_lock:
            ip = esp_addr[0] if esp_addr else "NINGUNA"  # Muestra IP si hay conexión
        print("IP ESP:", ip)
        print("Modo error actual:", "ACTIVADO ✅" if modo_error else "DESACTIVADO ❌")
        print("1) Solicitar INFO de la ESP")
        print("2) Activar MODO ERROR (modificación PAM4)")
        print("3) Desactivar MODO ERROR")
        print("4) Salir")

        # Esperar comando del usuario
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
            break  # Sale del programa
        else:
            print("Opción inválida.")

# --- Programa principal ---
if __name__ == "__main__":
    # Inicia el hilo que espera conexión desde la ESP
    threading.Thread(target=esp_acceptor, daemon=True).start()
    # Ejecuta el menú de control interactivo
    main_menu()
