# analizador_triple_pam4_complete.py
import sys
import socket
import threading
from collections import deque
from datetime import datetime

import numpy as np
from PyQt6 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg

# -------------------------
# Utilities
# -------------------------
def symbols_to_bits(values, bits_per_symbol):
    fmt = '{:0' + str(bits_per_symbol) + 'b}'
    return ''.join(fmt.format(int(v) & ((1 << bits_per_symbol) - 1)) for v in values)

def bits_to_text(bitstr):
    chars = []
    for i in range(0, len(bitstr) - 7, 8):
        byte = bitstr[i:i+8]
        try:
            chars.append(chr(int(byte, 2)))
        except Exception:
            chars.append('?')
    return ''.join(chars)

def printable_score(s):
    if not s:
        return 0.0
    printable = sum(1 for ch in s if 32 <= ord(ch) < 127)
    return printable / max(1, len(s))

def try_decode_pam_text(values):
    if not values:
        return "", 2
    b2 = symbols_to_bits(values, 2)
    t2 = bits_to_text(b2); s2 = printable_score(t2)
    b3 = symbols_to_bits(values, 3)
    t3 = bits_to_text(b3); s3 = printable_score(t3)
    if s3 > s2:
        return t3, 3
    return t2, 2

def pam_symbols_to_voltage(vals):
    arr = np.array(vals, dtype=float)
    if arr.size == 0:
        return arr
    if np.nanmax(arr) <= 3:
        map4 = {0: -3.0, 1: -1.0, 2: 1.0, 3: 3.0}
        return np.array([map4.get(int(round(v)), 0.0) for v in arr], dtype=float)
    else:
        return ((arr / 7.0) * 6.0) - 3.0

def compute_fft(signal, fs=1.0):
    n = len(signal)
    if n == 0:
        return np.array([]), np.array([])
    x = signal * np.hanning(n)
    X = np.fft.rfft(x)
    mag = np.abs(X) / n
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    return freqs, mag

def compute_snr_db(sig_a, sig_b):
    a = np.array(sig_a, dtype=float)
    b = np.array(sig_b, dtype=float)
    if a.size == 0 or b.size == 0:
        return float('nan')
    noise = a - b
    p_signal = np.mean(a ** 2)
    p_noise = np.mean(noise ** 2)
    if p_noise <= 0:
        return float('inf')
    return 10.0 * np.log10(p_signal / p_noise)

# -------------------------
# Server Thread (QThread)
# -------------------------
class ServerThread(QtCore.QThread):
    status = QtCore.pyqtSignal(str)
    ip_assigned = QtCore.pyqtSignal(str, str)             # tx, ip
    message_text = QtCore.pyqtSignal(str, str, str)       # tx, ip, text
    message_raw = QtCore.pyqtSignal(str, str, list, int)  # tx, ip, preview, len
    buffer_update = QtCore.pyqtSignal(str, str, list)     # tx, ip, values

    def __init__(self, port=8100, parent=None):
        super().__init__(parent)
        self.port = int(port)
        self._stop_event = threading.Event()
        self.sock = None
        self.ip_to_tx = {}
        self.lock = threading.Lock()

    def stop(self):
        self._stop_event.set()
        try:
            if self.sock:
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                self.sock.close()
        except Exception:
            pass

    def assign_tx_for_ip(self, ip):
        with self.lock:
            if ip in self.ip_to_tx:
                return self.ip_to_tx[ip], False
            used = set(self.ip_to_tx.values())
            for tx in ("TX1", "TX2", "TX3"):
                if tx not in used:
                    self.ip_to_tx[ip] = tx
                    return tx, True
            self.ip_to_tx[ip] = "TX1"
            return "TX1", True

    def run(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", self.port))
            s.listen(8)
            s.settimeout(1.0)
            self.sock = s
        except Exception as e:
            self.status.emit(f"Error iniciando servidor: {e}")
            return

        self.status.emit(f"Servidor escuchando en 0.0.0.0:{self.port}")

        while not self._stop_event.is_set():
            try:
                conn, addr = s.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as e:
                self.status.emit(f"Accept error: {e}")
                break

            ip = addr[0]
            tx, newly = self.assign_tx_for_ip(ip)
            if newly:
                self.ip_assigned.emit(tx, ip)
                self.status.emit(f"{tx} asignado a {ip}")

            threading.Thread(target=self.client_handler, args=(conn, ip, tx), daemon=True).start()

        try:
            s.close()
        except:
            pass
        self.status.emit("Servidor detenido.")

    def client_handler(self, conn, ip, tx):
        self.status.emit(f"Handler iniciado para {ip} -> {tx}")
        try:
            while not self._stop_event.is_set():
                try:
                    data = conn.recv(65536)
                except Exception as e:
                    self.status.emit(f"Recv error {ip}: {e}")
                    break
                if not data:
                    break
                values = list(data)
                text, bits = try_decode_pam_text(values)
                if text and printable_score(text) > 0.6:
                    self.message_text.emit(tx, ip, text)
                else:
                    preview = values[:200] if len(values) > 200 else values
                    self.message_raw.emit(tx, ip, preview, len(values))
                self.buffer_update.emit(tx, ip, values)
        finally:
            try:
                conn.close()
            except:
                pass
            self.status.emit(f"Conexión cerrada {ip}")

# -------------------------
# Chat/Console floating window
# -------------------------
class ChatWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat / Consola")
        self.resize(520, 560)
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel("Chat recibido")
        label.setStyleSheet("font-weight:bold;")
        layout.addWidget(label)
        self.chat_view = QtWidgets.QTextEdit()
        self.chat_view.setReadOnly(True)
        layout.addWidget(self.chat_view, stretch=1)
        label2 = QtWidgets.QLabel("Eventos / Log")
        label2.setStyleSheet("font-weight:bold;")
        layout.addWidget(label2)
        self.console_view = QtWidgets.QTextEdit()
        self.console_view.setReadOnly(True)
        layout.addWidget(self.console_view, stretch=1)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def add_chat(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        self.chat_view.append(f"[{ts}] {text}")

    def add_console(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        self.console_view.append(f"[{ts}] {text}")

# -------------------------
# PAM4 Symbols Tab
# -------------------------
class PAM4SymbolsTab(QtWidgets.QWidget):
    def __init__(self, get_color_fn, is_visible_fn, get_name_fn):
        super().__init__()
        self.get_color = get_color_fn
        self.is_visible = is_visible_fn
        self.get_name = get_name_fn

        self.data = {"TX1": deque(maxlen=2000), "TX2": deque(maxlen=2000), "TX3": deque(maxlen=2000)}
        self.mode_box = QtWidgets.QComboBox()
        self.mode_box.addItems(["Secuencia", "Frecuencia"])
        self.reset_btn = QtWidgets.QPushButton("Resetear")

        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Modo:"))
        top.addWidget(self.mode_box)
        top.addStretch()
        top.addWidget(self.reset_btn)

        self.plot = pg.PlotWidget()
        self.plot.setBackground('k')
        self.plot.showGrid(x=True, y=True, alpha=0.3)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.plot, stretch=1)

        self.mode_box.currentTextChanged.connect(lambda _: self.update_plot())
        self.reset_btn.clicked.connect(self.reset)

    def reset(self):
        for k in self.data:
            self.data[k].clear()
        self.update_plot()

    def add_symbol(self, tx, v):
        vi = int(v) if v is not None else 0
        vi = max(0, min(7, vi))
        if vi > 3:
            vi = vi % 4
        self.data[tx].append(vi)
        self.update_plot()

    def update_plot(self):
        self.plot.clear()
        mode = self.mode_box.currentText()
        offsets_x = {"TX1": -0.18, "TX2": 0.0, "TX3": 0.18}
        for tx in ("TX1", "TX2", "TX3"):
            if not self.is_visible(tx):
                continue
            vals = list(self.data[tx])
            if not vals:
                continue
            color = self.get_color(tx)
            c = QtGui.QColor(color)
            qcolor = (c.red(), c.green(), c.blue())
            if mode == "Frecuencia":
                counts = [0, 0, 0, 0]
                for vv in vals:
                    counts[int(vv) % 4] += 1
                x = np.arange(4) + offsets_x[tx]
                bg = pg.BarGraphItem(x=x.tolist(), height=counts, width=0.15, brush=pg.mkBrush(qcolor + (180,)))
                self.plot.addItem(bg)
                # label per bar (name)
                for xi, yi in zip(x, counts):
                    text = pg.TextItem(self.get_name(tx), anchor=(0.5, -0.4), color=color)
                    text.setPos(xi, -0.2)
                    self.plot.addItem(text)
            else:
                N = len(vals)
                M = min(300, N)
                x = np.arange(N - M, N) + offsets_x[tx]
                y = np.array(vals[-M:], dtype=float)
                # build stem arrays with NaNs separator
                xx = np.empty(3 * M); yy = np.empty(3 * M)
                for i in range(M):
                    xx[3*i] = x[i]; xx[3*i+1] = x[i]; xx[3*i+2] = np.nan
                    yy[3*i] = 0.0; yy[3*i+1] = y[i]; yy[3*i+2] = np.nan
                pen = pg.mkPen(qcolor, width=1.2)
                self.plot.addItem(pg.PlotDataItem(xx, yy, pen=pen))
                self.plot.addItem(pg.ScatterPlotItem(x, y, size=6, brush=pg.mkBrush(qcolor)))
                # labels under groups: for last M points, show small labels every ~50
                name = self.get_name(tx)
                for idx in range(0, M, max(1, M//6)):
                    txpos = x[idx]
                    text = pg.TextItem(name, anchor=(0.5, 1.5), color=color)
                    text.setPos(txpos, -0.4)
                    self.plot.addItem(text)

# -------------------------
# PAM4 Values Tab (reconstructed 0..7) with offset + labels
# -------------------------
class PAM4ValuesTab(QtWidgets.QWidget):
    def __init__(self, get_color_fn, is_visible_fn, get_name_fn):
        super().__init__()
        self.get_color = get_color_fn
        self.is_visible = is_visible_fn
        self.get_name = get_name_fn

        self.values = {"TX1": deque(maxlen=2000), "TX2": deque(maxlen=2000), "TX3": deque(maxlen=2000)}
        self.counts = {"TX1": [0]*8, "TX2": [0]*8, "TX3": [0]*8}

        self.mode_box = QtWidgets.QComboBox()
        self.mode_box.addItems(["Secuencia", "Frecuencia"])
        self.reset_btn = QtWidgets.QPushButton("Resetear")

        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Modo:"))
        top.addWidget(self.mode_box)
        top.addStretch()
        top.addWidget(self.reset_btn)

        self.plot = pg.PlotWidget()
        self.plot.setBackground('k')
        self.plot.showGrid(x=True, y=True, alpha=0.3)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.plot, stretch=1)

        self.mode_box.currentTextChanged.connect(lambda _: self.update_plot())
        self.reset_btn.clicked.connect(self.reset)

    def reset(self):
        for k in self.values:
            self.values[k].clear()
            self.counts[k] = [0]*8
        self.update_plot()

    def add_reconstructed_value(self, tx, v):
        vi = int(v) if v is not None else 0
        vi = max(0, min(7, vi))
        self.values[tx].append(vi)
        self.counts[tx][vi] += 1
        self.update_plot()

    def update_plot(self):
        self.plot.clear()
        mode = self.mode_box.currentText()
        offsets_x = {"TX1": -0.18, "TX2": 0.0, "TX3": 0.18}
        for tx in ("TX1", "TX2", "TX3"):
            if not self.is_visible(tx):
                continue
            vals = list(self.values[tx])
            color = self.get_color(tx)
            c = QtGui.QColor(color); qcolor = (c.red(), c.green(), c.blue())
            if mode == "Frecuencia":
                x = np.arange(8) + offsets_x[tx]
                y = self.counts[tx]
                brush = pg.mkBrush(qcolor + (200,))
                bg = pg.BarGraphItem(x=x.tolist(), height=y, width=0.15, brush=brush)
                self.plot.addItem(bg)
                # label: name under group center
                text = pg.TextItem(self.get_name(tx), anchor=(0.5, 1.5), color=color)
                text.setPos(3.5 + offsets_x[tx], -0.6)
                self.plot.addItem(text)
            else:
                N = len(vals)
                if N == 0:
                    continue
                M = min(300, N)
                x = np.arange(N - M, N) + offsets_x[tx]
                y = np.array(vals[-M:], dtype=float)
                xx = np.empty(3 * M); yy = np.empty(3 * M)
                for i in range(M):
                    xx[3*i] = x[i]; xx[3*i+1] = x[i]; xx[3*i+2] = np.nan
                    yy[3*i] = 0.0; yy[3*i+1] = y[i]; yy[3*i+2] = np.nan
                pen = pg.mkPen(qcolor, width=1.2)
                self.plot.addItem(pg.PlotDataItem(xx, yy, pen=pen))
                self.plot.addItem(pg.ScatterPlotItem(x, y, size=7, brush=pg.mkBrush(qcolor)))
                # labels: show name every ~N/6 or fixed spacing
                name = self.get_name(tx)
                step = max(1, M//6)
                for idx in range(0, M, step):
                    posx = x[idx]
                    text = pg.TextItem(name, anchor=(0.5, 1.5), color=color)
                    text.setPos(posx, -0.6)
                    self.plot.addItem(text)

# -------------------------
# Main Window
# -------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analizador Triple — PAM4 (completo)")
        self.resize(1400, 920)

        # state
        self.tx_names = {"TX1": "TX1", "TX2": "TX2", "TX3": "TX3"}
        self.tx_ips = {"TX1": "-", "TX2": "-", "TX3": "-"}
        self.tx_colors = {"TX1": "#00ff00", "TX2": "#00ffff", "TX3": "#ff9900"}
        self.tx_visible = {"TX1": True, "TX2": True, "TX3": True}
        self.latest = {"TX1": np.array([]), "TX2": np.array([]), "TX3": np.array([])}

        # central widget
        w = QtWidgets.QWidget()
        self.setCentralWidget(w)
        v = QtWidgets.QVBoxLayout(w)

        # top controls
        top = QtWidgets.QHBoxLayout()
        v.addLayout(top)

        # TX columns
        for tx in ("TX1", "TX2", "TX3"):
            col = QtWidgets.QVBoxLayout()
            top.addLayout(col)
            lbl = QtWidgets.QLabel(tx)
            lbl.setStyleSheet("font-weight:bold;")
            col.addWidget(lbl)
            le = QtWidgets.QLineEdit(self.tx_names[tx])
            le.editingFinished.connect(lambda t=tx, e=le: self.set_tx_name(t, e.text()))
            col.addWidget(le)
            ip_lbl = QtWidgets.QLabel(f"IP: {self.tx_ips[tx]}")
            col.addWidget(ip_lbl)
            setattr(self, f"{tx}_ip_label", ip_lbl)
            hb = QtWidgets.QHBoxLayout()
            btn_color = QtWidgets.QPushButton("Color")
            btn_color.clicked.connect(lambda _, t=tx: self.choose_color(t))
            hb.addWidget(btn_color)
            chk = QtWidgets.QCheckBox("Mostrar")
            chk.setChecked(True)
            chk.stateChanged.connect(lambda s, t=tx: self.set_visible(t, s == QtCore.Qt.CheckState.Checked))
            hb.addWidget(chk)
            col.addLayout(hb)

        # demod checkbox + port
        self.demod_chk = QtWidgets.QCheckBox("Demodular TX1 (texto & voltaje)")
        self.demod_chk.setChecked(True)
        top.addWidget(self.demod_chk)
        top.addStretch()
        top.addWidget(QtWidgets.QLabel("Puerto:"))
        self.port_spin = QtWidgets.QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(8100)
        top.addWidget(self.port_spin)

        # start/stop/chat/layers
        self.btn_start = QtWidgets.QPushButton("▶ Iniciar servidor")
        self.btn_stop = QtWidgets.QPushButton("⏹ Detener servidor")
        self.btn_stop.setEnabled(False)
        top.addWidget(self.btn_start)
        top.addWidget(self.btn_stop)

        self.chat_btn = QtWidgets.QPushButton("💬 Chat")
        top.addWidget(self.chat_btn)

        self.layers_btn = QtWidgets.QPushButton("🗂 Capas")
        top.addWidget(self.layers_btn)

        # tabs
        self.tabs = QtWidgets.QTabWidget()
        v.addWidget(self.tabs, stretch=1)

        # Tiempo tab
        self.tab_time = QtWidgets.QWidget()
        self.tabs.addTab(self.tab_time, "Tiempo")
        tl = QtWidgets.QVBoxLayout(self.tab_time)
        self.plot_time = pg.PlotWidget()
        self.plot_time.showGrid(x=True, y=True, alpha=0.3)
        tl.addWidget(self.plot_time)
        self.curves = {
            "TX1": self.plot_time.plot(pen=pg.mkPen(self.tx_colors["TX1"], width=2), name="TX1"),
            "TX2": self.plot_time.plot(pen=pg.mkPen(self.tx_colors["TX2"], width=1.5), name="TX2"),
            "TX3": self.plot_time.plot(pen=pg.mkPen(self.tx_colors["TX3"], width=1.5), name="TX3"),
        }

        # FFT tab
        self.tab_fft = QtWidgets.QWidget()
        self.tabs.addTab(self.tab_fft, "FFT")
        fl = QtWidgets.QVBoxLayout(self.tab_fft)
        self.plot_fft = pg.PlotWidget()
        fl.addWidget(self.plot_fft)
        self.fft_curves = {
            "TX1": self.plot_fft.plot(pen=pg.mkPen(self.tx_colors["TX1"], width=2)),
            "TX2": self.plot_fft.plot(pen=pg.mkPen(self.tx_colors["TX2"], width=1.5)),
            "TX3": self.plot_fft.plot(pen=pg.mkPen(self.tx_colors["TX3"], width=1.5)),
        }

        # SNR tab
        self.tab_snr = QtWidgets.QWidget()
        self.tabs.addTab(self.tab_snr, "SNR")
        sl = QtWidgets.QVBoxLayout(self.tab_snr)
        self.snr_label = QtWidgets.QLabel("SNRs se mostrarán aquí")
        sl.addWidget(self.snr_label)

        # Diferencias
        self.tab_diff = QtWidgets.QWidget()
        self.tabs.addTab(self.tab_diff, "Diferencias")
        dl = QtWidgets.QVBoxLayout(self.tab_diff)
        self.plot_diff = pg.PlotWidget()
        dl.addWidget(self.plot_diff)
        self.diff12 = self.plot_diff.plot(pen=pg.mkPen(self.tx_colors["TX1"], width=1))
        self.diff13 = self.plot_diff.plot(pen=pg.mkPen(self.tx_colors["TX2"], width=1))
        self.diff23 = self.plot_diff.plot(pen=pg.mkPen(self.tx_colors["TX3"], width=1))

        # Eye
        self.tab_eye = QtWidgets.QWidget()
        self.tabs.addTab(self.tab_eye, "Ojo")
        el = QtWidgets.QVBoxLayout(self.tab_eye)
        self.plot_eye = pg.PlotWidget()
        el.addWidget(self.plot_eye)
        self.plot_eye.showGrid(x=True, y=True, alpha=0.3)

        # PAM4 Symbols and Values tabs
        self.pam4_symbols_tab = PAM4SymbolsTab(self.get_tx_color, self.get_tx_visible, self.get_tx_name)
        self.tabs.addTab(self.pam4_symbols_tab, "PAM4 Symbols")
        self.pam4_values_tab = PAM4ValuesTab(self.get_tx_color, self.get_tx_visible, self.get_tx_name)
        self.tabs.addTab(self.pam4_values_tab, "PAM4 Values")

        # chat/log
        self.chat_win = ChatWindow()

        # server thread
        self.server_thread = None

        # connections
        self.btn_start.clicked.connect(self.start_server)
        self.btn_stop.clicked.connect(self.stop_server)
        self.chat_btn.clicked.connect(self.chat_win.show)
        self.layers_btn.clicked.connect(self.toggle_layers_window)

        # layers window
        self.layers_win = None

        # timer (no-op) to keep UI responsive
        self.timer = QtCore.QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(lambda: None)
        self.timer.start()

    # Helpers
    def set_tx_name(self, tx, name):
        self.tx_names[tx] = name

    def get_tx_name(self, tx):
        return self.tx_names.get(tx, tx)

    def choose_color(self, tx):
        col = QtWidgets.QColorDialog.getColor()
        if not col.isValid():
            return
        hexc = col.name()
        self.tx_colors[tx] = hexc
        c = QtGui.QColor(hexc)
        pen = pg.mkPen((c.red(), c.green(), c.blue()), width=2 if tx=="TX1" else 1.5)
        self.curves[tx].setPen(pen)
        self.fft_curves[tx].setPen(pen)
        if tx == "TX1":
            self.diff12.setPen(pen)
        elif tx == "TX2":
            self.diff13.setPen(pen)
        else:
            self.diff23.setPen(pen)
        # force PAM4 tabs to update brushes and labels
        self.pam4_symbols_tab.update_plot()
        self.pam4_values_tab.update_plot()

    def get_tx_color(self, tx):
        return self.tx_colors.get(tx, "#ffffff")

    def set_visible(self, tx, visible):
        self.tx_visible[tx] = visible
        self.curves[tx].setVisible(visible)
        self.fft_curves[tx].setVisible(visible)
        # update other displays
        self.pam4_symbols_tab.update_plot()
        self.pam4_values_tab.update_plot()

    def get_tx_visible(self, tx):
        return self.tx_visible.get(tx, True)

    # Layers window
    def toggle_layers_window(self):
        if self.layers_win and self.layers_win.isVisible():
            self.layers_win.hide()
            return
        w = QtWidgets.QWidget()
        w.setWindowTitle("Capas (Mostrar/Ocultar TX)")
        w.setWindowFlags(w.windowFlags() | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        layout = QtWidgets.QVBoxLayout(w)
        for tx in ("TX1", "TX2", "TX3"):
            cb = QtWidgets.QCheckBox(tx)
            cb.setChecked(self.tx_visible[tx])
            cb.stateChanged.connect(lambda s, t=tx: self.set_visible(t, s == QtCore.Qt.CheckState.Checked))
            layout.addWidget(cb)
        w.show()
        self.layers_win = w

    # Server control
    def start_server(self):
        if self.server_thread and self.server_thread.isRunning():
            return
        port = int(self.port_spin.value())
        self.server_thread = ServerThread(port=port)
        self.server_thread.status.connect(self.on_status)
        self.server_thread.ip_assigned.connect(self.on_ip_assigned)
        self.server_thread.message_text.connect(self.on_message_text)
        self.server_thread.message_raw.connect(self.on_message_raw)
        self.server_thread.buffer_update.connect(self.on_buffer_update)
        self.server_thread.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.chat_win.add_console(f"Servidor iniciado en puerto {port}")

    def stop_server(self):
        if not self.server_thread:
            return
        self.server_thread.stop()
        self.server_thread.wait(timeout=3000)
        self.server_thread = None
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.chat_win.add_console("Servidor detenido (usuario)")

    # Server handlers
    @QtCore.pyqtSlot(str)
    def on_status(self, msg):
        self.chat_win.add_console(msg)

    @QtCore.pyqtSlot(str, str)
    def on_ip_assigned(self, tx, ip):
        self.tx_ips[tx] = ip
        lbl = getattr(self, f"{tx}_ip_label", None)
        if lbl:
            lbl.setText(f"IP: {ip}")
        self.chat_win.add_console(f"{tx} detectado: {ip}")

    @QtCore.pyqtSlot(str, str, str)
    def on_message_text(self, tx, ip, text):
        if tx == "TX1" and not self.demod_chk.isChecked():
            self.chat_win.add_console(f"{ip} (texto recibido pero demod disabled)")
            return
        name = self.tx_names.get(tx, tx)
        self.chat_win.add_chat(f"[{name} | {ip}] {text}")

    @QtCore.pyqtSlot(str, str, list, int)
    def on_message_raw(self, tx, ip, preview, total_len):
        name = self.tx_names.get(tx, tx)
        self.chat_win.add_chat(f"[{name} | {ip}] [RAW len={total_len}] {preview}")

    @QtCore.pyqtSlot(str, str, list)
    def on_buffer_update(self, tx, ip, values):
        arr = np.array(values, dtype=float)
        if arr.size > 20000:
            arr = arr[-20000:]
        self.latest[tx] = arr

        # time plot y
        if tx == "TX1" and self.demod_chk.isChecked():
            y = pam_symbols_to_voltage(arr)
        else:
            y = arr

        if self.tx_visible[tx]:
            self.curves[tx].setData(y)
        else:
            self.curves[tx].setData([])

        # FFT update
        if y.size > 1:
            f, m = compute_fft(y)
            self.fft_curves[tx].setData(f, m)

        # diffs
        a1 = pam_symbols_to_voltage(self.latest["TX1"]) if (self.demod_chk.isChecked() and self.latest["TX1"].size>0) else self.latest["TX1"]
        a2 = self.latest["TX2"]
        a3 = self.latest["TX3"]
        if a1.size and a2.size:
            L = min(a1.size, a2.size)
            self.diff12.setData(np.abs(a1[:L] - a2[:L]))
        if a1.size and a3.size:
            L = min(a1.size, a3.size)
            self.diff13.setData(np.abs(a1[:L] - a3[:L]))
        if a2.size and a3.size:
            L = min(a2.size, a3.size)
            self.diff23.setData(np.abs(a2[:L] - a3[:L]))

        # SNR
        try:
            snr12 = compute_snr_db(a1[:min(a1.size,a2.size)], a2[:min(a1.size,a2.size)]) if a1.size and a2.size else float('nan')
            snr13 = compute_snr_db(a1[:min(a1.size,a3.size)], a3[:min(a1.size,a3.size)]) if a1.size and a3.size else float('nan')
            snr23 = compute_snr_db(a2[:min(a2.size,a3.size)], a3[:min(a2.size,a3.size)]) if a2.size and a3.size else float('nan')
            txt = (f"SNR TX1 vs TX2: {'∞' if not np.isfinite(snr12) else f'{snr12:.2f} dB'}\n"
                   f"SNR TX1 vs TX3: {'∞' if not np.isfinite(snr13) else f'{snr13:.2f} dB'}\n"
                   f"SNR TX2 vs TX3: {'∞' if not np.isfinite(snr23) else f'{snr23:.2f} dB'}")
            self.snr_label.setText(txt)
        except Exception:
            pass

        # eye diagram (simple)
        if self.latest["TX1"].size > 4:
            self.plot_eye.clear()
            data_eye = pam_symbols_to_voltage(self.latest["TX1"]) if self.demod_chk.isChecked() else self.latest["TX1"]
            L = len(data_eye) - 1
            nshow = min(200, L)
            for i in range(L - nshow, L):
                self.plot_eye.plot([i, i+1], [data_eye[i], data_eye[i+1]], pen=pg.mkPen(self.tx_colors["TX1"], width=0.6, alpha=120))

        # reconstruct original 0..7 values from symbol stream (pairs)
        syms = list(values)
        reconstructed = []
        for i in range(0, len(syms)-1, 2):
            s1 = int(syms[i]) & 0x3
            s2 = int(syms[i+1]) & 0x3
            orig = (s1 << 2) | s2
            if orig > 7:
                orig = orig & 0x7
            reconstructed.append(orig)
        for val in reconstructed:
            self.pam4_values_tab.add_reconstructed_value(tx, val)
        for sym in syms:
            self.pam4_symbols_tab.add_symbol(tx, sym)

    def closeEvent(self, event):
        self.stop_server()
        event.accept()

# -------------------------
# Run
# -------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)
    pg.setConfigOption('background','k')
    pg.setConfigOption('foreground','w')
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
