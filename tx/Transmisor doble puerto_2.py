import socket

def text_to_pam4(message):
    binary = ''.join(format(ord(c), '08b') for c in message)
    pam4 = []
    for i in range(0, len(binary), 2):
        bits = binary[i:i+2].ljust(2, '0')
        pam4.append(int(bits, 2))
    return pam4

def send_pam4_to_destinations(pam4_data, destinos):
    for ip, port in destinos:
        send_pam4(ip, port, pam4_data)

def send_pam4(ip, port, pam4_data):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(bytes(pam4_data))
            print(f"Mensaje enviado a {ip}:{port} → {pam4_data}")
    except Exception as e:
        print(f"Error al enviar a {ip}:{port} → {e}")

def main():
    # Destinos
    destinos = [
        ("10.0.0.48", 5051),
        ("10.0.1.255", 8100)
    ]

    while True:
        line = input("Ingrese el mensaje a enviar (escriba 'quit' para terminar): ")
        if line.lower() == 'quit':
            break

        pam4_data = text_to_pam4(line) # Convert and send each line
        send_pam4_to_destinations(pam4_data, destinos) # Send to destinations


if __name__ == "__main__":
    main()