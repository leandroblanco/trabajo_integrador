import serial
import time
def main():
    puerto_serial = 'COM3'  # Cambia esto si usás Linux o Mac (ej: '/dev/ttyUSB0')
    baudrate = 9600

    try:
        ser = serial.Serial(puerto_serial, baudrate, timeout=1)
        print(f"🔌 Escuchando en {puerto_serial} a {baudrate} baudios...")
    except Exception as e:
        print(f"❌ No se pudo abrir el puerto serial: {e}")
        return

    try:
        while True:
            if ser.in_waiting:
                byte = ser.read(1)
                if byte:
                    valor = byte[0]
                    print(f"📥 Byte recibido: {valor}")
            time.sleep(0.1)  # Pequeña pausa para no saturar la consola
    except KeyboardInterrupt:
        print("🛑 Lectura interrumpida por el usuario.")
    finally:
        ser.close()

if __name__ == "__main__":
    main()