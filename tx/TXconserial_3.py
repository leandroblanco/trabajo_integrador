import socket
import sys
import time

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
            return False

        def read(self, size=1):
            try:
                return sys.stdin.read(size).encode()
            except Exception:
                return b''

        def close(self):
            self._closed = True

    serial = type("serial_module", (), {"Serial": _FallbackSerial})
    print("Warning: pyserial not found; running with stdin fallback.")

def send_pam4_to_destinations(pam4_data, destinos):
    for ip, port in destinos:
        send_pam4(ip, port, pam4_data)

def send_pam4(ip, port, pam4_data):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(bytes(pam4_data))
            print(f"✅ Enviado a {ip}:{port} → {pam4_data}")
    except Exception as e:
        print(f"❌ Error al enviar a {ip}:{port} → {e}")

def main():
    puerto_serial = 'COM3'
    baudrate = 9600

    try:
        ser = serial.Serial(puerto_serial, baudrate, timeout=1)
        print(f"🔌 Conectado al puerto {puerto_serial} a {baudrate} baudios.")
    except Exception as e:
        print(f"❌ No se pudo abrir el puerto serial: {e}")
        return

    destinos = [
        ("10.0.0.48", 5051),  # Gonzalo
        # ("10.0.0.52", 5052),  # Candela
        ("10.0.1.255", 8100)  # Eric
    ]

    try:
        while True:
            byte = ser.read(1)  # Leer un byte
            if byte:
                value = byte[0]
                if 0 <= value <= 7:
                    print(f"📥 Valor recibido por serial: {value}")
                    send_pam4_to_destinations([value], destinos)
                else:
                    print(f"⚠️ Valor fuera de rango (0-7): {value}")
            else:
                print("⚠️ No se recibió ningún dato del puerto serial.")
            time.sleep(1)  # Esperar 100 ms antes de la próxima lectura
    except KeyboardInterrupt:
        print("🛑 Programa terminado por el usuario.")
    finally:
        ser.close()

if __name__ == "__main__":
    main()