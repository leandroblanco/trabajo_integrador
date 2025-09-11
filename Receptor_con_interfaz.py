import socket
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# 🔄 Decodificación PAM4 a texto
def pam4_to_text(pam4_data):
    binary = ''.join(format(val, '02b') for val in pam4_data if val in [0, 1, 2, 3])
    chars = [chr(int(binary[i:i+8], 2)) for i in range(0, len(binary), 8) if len(binary[i:i+8]) == 8]
    return ''.join(chars)

# 📨 Recibe mensaje desde TX
def recibir_desde_tx(conn):
    data = conn.recv(1024)
    if not data:
        return None
    pam4_data = list(data)
    return pam4_to_text(pam4_data)

# 📨 Recibe mensaje desde RX
def recibir_desde_rx(conn):
    data = conn.recv(1024)
    if not data:
        return None
    return data.decode('utf-8')

# 📊 Visualización embebida
def comparar_mensajes(m1, m2, frame):
    min_len = min(len(m1), len(m2))
    max_len = max(len(m1), len(m2))

    diferencias = []
    etiquetas = []
    for i in range(min_len):
        diferencias.append(m1[i] != m2[i])
        etiquetas.append(f"{m1[i]} | {m2[i]}")

    if len(m1) != len(m2):
        if len(m1) > len(m2):
            extra = [(True, f"{c} | -") for c in m1[min_len:]]
        else:
            extra = [(True, f"- | {c}") for c in m2[min_len:]]
        for err, lab in extra:
            diferencias.append(err)
            etiquetas.append(lab)

    errores = sum(diferencias)
    total = max_len
    error_pct = (errores / total) * 100 if total > 0 else 0

    posiciones = list(range(total))
    colores = ["#ff4d4d" if d else "#4CAF50" for d in diferencias]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(posiciones, [1]*total, color=colores)
    ax.set_yticks(posiciones)
    ax.set_yticklabels(etiquetas)
    ax.set_title(f"Errores: {errores}/{total} ({error_pct:.2f}%)")
    ax.set_xlabel("Coincidencia (verde=ok, rojo=error)")
    ax.set_ylabel("Posición")
    ax.invert_yaxis()
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack()

# 🧲 Servidor visualizador con GUI
def iniciar_servidor(num_msgs, frame):
    ip_rx = '0.0.0.0'
    port = 9100

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((ip_rx, port))
        s.listen(5)
        print(f"📡 Escuchando en {ip_rx}:{port}...")

        for i in range(num_msgs):
            mensajes = []

            conn_tx, _ = s.accept()
            with conn_tx:
                mensaje_tx = recibir_desde_tx(conn_tx)
                if mensaje_tx:
                    mensajes.append(mensaje_tx)

            conn_rx, _ = s.accept()
            with conn_rx:
                mensaje_rx = recibir_desde_rx(conn_rx)
                if mensaje_rx:
                    mensajes.append(mensaje_rx)

            if len(mensajes) == 2:
                comparar_mensajes(mensajes[0], mensajes[1], frame)

# 🖼️ Interfaz gráfica principal
def main_gui():
    root = tk.Tk()
    root.title("Visualizador PAM4 - Comparador de Mensajes")

    frm_top = ttk.Frame(root, padding=10)
    frm_top.pack()

    ttk.Label(frm_top, text="Cantidad de mensajes a comparar:").pack(side="left")
    num_entry = ttk.Entry(frm_top, width=5)
    num_entry.insert(0, "2")
    num_entry.pack(side="left")

    frm_canvas = ttk.Frame(root, padding=10)
    frm_canvas.pack(fill="both", expand=True)

    def iniciar():
        num_msgs = int(num_entry.get())
        iniciar_servidor(num_msgs, frm_canvas)

    ttk.Button(frm_top, text="Iniciar servidor", command=iniciar).pack(side="left")

    root.mainloop()

if __name__ == "__main__":
    main_gui()