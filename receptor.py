import socket

# 🔄 Decodificación PAM4 a texto
def pam4_to_text(pam4_data):
    binary = ''.join(format(val, '02b') for val in pam4_data if val in [0, 1, 2, 3])
    chars = [chr(int(binary[i:i+8], 2)) for i in range(0, len(binary), 8) if len(binary[i:i+8]) == 8]
    return ''.join(chars)

# 🚀 Envío directo del mensaje decodificado al visualizador
def enviar_a_visualizador(mensaje, ip_destino='10.0.2.61', puerto_destino=9100):
    print(f"📤 Enviando al visualizador: '{mensaje}'")  # Solo imprime lo que se manda
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((ip_destino, puerto_destino))
            s.sendall(mensaje.encode('utf-8'))
            print(f"✅ Mensaje reenviado a {ip_destino}:{puerto_destino}")
        except Exception as e:
            print(f"❌ Error al enviar al visualizador: {e}")

# 🧲 Receptor en bucle
def main():
    ip_rx = '0.0.0.0'
    port = 5000

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((ip_rx, port))
        s.listen()
        print(f"📡 Receptor activo en el puerto {port}. Esperando conexiones...")

        while True:
            conn, addr = s.accept()
            with conn:
                print(f"\n🔗 Conectado desde {addr}")
                data = conn.recv(4096)
                if not data:
                    print("⚠️ Conexión vacía o cerrada.")
                    continue

                pam4_data = list(data)
                print("📊 Datos PAM4 recibidos:", pam4_data)

                # Decodificar mensaje
                message = pam4_to_text(pam4_data)
                print("📨 Mensaje decodificado:", message)

                # Reenviar sin modificar
                enviar_a_visualizador(message)

if __name__ == "__main__":
    main()