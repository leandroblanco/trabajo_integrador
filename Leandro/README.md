# Análisis del Código: Transmisor doble puerto_2.py

Este script implementa un transmisor de datos que convierte texto en una señal PAM4 y la envía a dos destinos IP mediante sockets TCP.

## Explicación línea por línea

- `import socket`
  - Importa la biblioteca `socket` para comunicación en red.
- `def text_to_pam4(message):`
  - Define una función que convierte texto en una señal PAM4.
- `    binary = ''.join(format(ord(c), '08b') for c in message)`
  - Convierte cada carácter del mensaje en su representación binaria de 8 bits.
- `    pam4 = []`
  - Inicializa una lista para almacenar los símbolos PAM4.
- `    for i in range(0, len(binary), 2):`
  - Itera sobre los bits binarios de dos en dos para formar símbolos PAM4.
- `        bits = binary[i:i+2].ljust(2, '0')`
- `        pam4.append(int(bits, 2))`
  - Convierte cada par de bits en un entero (0 a 3) y lo agrega a la lista PAM4.
- `    return pam4`
- `def send_pam4_to_destinations(pam4_data, destinos):`
  - Define una función para enviar los datos PAM4 a múltiples destinos.
- `    for ip, port in destinos:`
- `        send_pam4(ip, port, pam4_data)`
  - Llama a la función que envía los datos a un destino específico.
- `def send_pam4(ip, port, pam4_data):`
  - Llama a la función que envía los datos a un destino específico.
- `    try:`
- `        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:`
  - Crea un socket TCP/IP.
- `            s.connect((ip, port))`
  - Establece conexión con el destino especificado.
- `            s.sendall(bytes(pam4_data))`
  - Envía todos los datos PAM4 como bytes.
- `            print(f"Mensaje enviado a {ip}:{port} → {pam4_data}")`
  - Muestra en consola el mensaje enviado y el destino.
- `    except Exception as e:`
  - Captura errores en el envío y los muestra.
- `        print(f"Error al enviar a {ip}:{port} → {e}")`
- `def main():`
  - Función principal que gestiona la entrada del usuario y el envío.
- `    # Destinos`
- `    destinos = [`
  - Lista de direcciones IP y puertos a los que se enviará el mensaje.
- `        ("10.0.2.189", 5000),`
- `        ("10.0.2.61", 9100)`
- `    ]`
- `    while True:`
  - Bucle infinito para recibir mensajes del usuario.
- `        line = input("Ingrese el mensaje a enviar (escriba 'quit' para terminar): ")`
  - Solicita al usuario que ingrese un mensaje.
- `        if line.lower() == 'quit':`
  - Permite salir del programa escribiendo 'quit'.
- `            break`
- `        pam4_data = text_to_pam4(line) # Convert and send each line`
- `        send_pam4_to_destinations(pam4_data, destinos) # Send to destinations`
- `if __name__ == "__main__":`
  - Ejecuta la función principal si el script se corre directamente.
- `    main()`

## Teoría sobre su función
Este script simula un transmisor digital que convierte texto en una señal PAM4 (modulación por amplitud de pulsos con 4 niveles), ideal para sistemas de comunicación. Luego, transmite esta señal a dos dispositivos o servidores definidos por IP y puerto. Puede utilizarse en simulaciones de redes, pruebas de transmisión o sistemas embebidos.
