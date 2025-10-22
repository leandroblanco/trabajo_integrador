import socket
import sys

# Try importing pyserial (serial); if unavailable provide a minimal fallback that reads from stdin
try:
    import serial
except Exception:
    class _FallbackSerial:
        def __init__(self, port, baudrate, timeout=1):
            self.port = port
            self.baudrate = baudrate
            self.timeout = timeout
            self._closed = False

        @property
        def in_waiting(self):
            # No automatic incoming data; user can type lines into stdin for testing
            return False

        def readline(self):
            # Read a line from stdin for testing (so program can run without pyserial)
            try:
                return sys.stdin.readline().encode()
            except Exception:
                return b''

        def close(self):
            self._closed = True

    # Create a serial-like module object with Serial class
    serial = type("serial_module", (), {"Serial": _FallbackSerial})
    print("Warning: pyserial not found; running with stdin fallback. Install pyserial with 'pip install pyserial' for real serial support.")

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
    # Configurar puerto serial (ajustar el nombre del puerto según tu sistema)
    puerto_serial = 'COM3'  # En Windows suele ser COMx, en Linux /dev/ttyUSBx
    baudrate = 9600

    try:
        ser = serial.Serial(puerto_serial, baudrate, timeout=1)
        print(f"Conectado al puerto {puerto_serial} a {baudrate} baudios.")
    except Exception as e:
        print(f"No se pudo abrir el puerto serial: {e}")
        return

    destinos = [
        ("10.0.2.215", 5051),
        ("10.0.2.208", 8100)
    ]

    try:
        while True:
            if ser.in_waiting:
                line = ser.readline().decode().strip()
                if line:
                    print(f"ADC recibido: {line}")
                    pam4_data = text_to_pam4(line)
                    send_pam4_to_destinations(pam4_data, destinos)
    except KeyboardInterrupt:
        print("Programa terminado por el usuario.")
    finally:
        ser.close()

if __name__ == "__main__":
    main()