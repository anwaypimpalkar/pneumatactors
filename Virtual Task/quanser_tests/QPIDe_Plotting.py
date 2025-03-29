import os
# ---------------- CONFIGURATION ---------------- #
quarc_dll_path = r"C:\Program Files\Quanser\QUARC"
os.add_dll_directory(quarc_dll_path)

import time
import threading
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
from collections import deque
from quanser.hardware import HIL

BOARD_TYPE = "qpid_e"
BOARD_IDENTIFIER = "0"
FREQUENCY = 1000  # Hz
INPUT_CHANNELS = np.array([3, 4], dtype=np.uint32)  # Analog channels 1 and 2
DURATION = 5  # Plot window duration in seconds

# ---------------- SHARED BUFFERS ---------------- #
latest_values = np.zeros(len(INPUT_CHANNELS))  # Most recent analog values
lock = threading.Lock()
time_stamps = deque()
analog_data = {ch: deque() for ch in INPUT_CHANNELS}

# ---------------- DATA COLLECTION THREAD ---------------- #
def collect_analog_data():
    period = 1.0 / FREQUENCY
    card = HIL()
    card.open(BOARD_TYPE, BOARD_IDENTIFIER)
    input_buffer = np.zeros(len(INPUT_CHANNELS), dtype=np.float64)

    try:
        start_time = time.time()
        while True:
            card.read_analog(INPUT_CHANNELS, len(INPUT_CHANNELS), input_buffer)
            with lock:
                latest_values[:] = input_buffer
                current_time = time.time() - start_time
                time_stamps.append(current_time)
                for i, ch in enumerate(INPUT_CHANNELS):
                    analog_data[ch].append(input_buffer[i])
                # Maintain rolling window
                while time_stamps and time_stamps[0] < (current_time - DURATION):
                    time_stamps.popleft()
                    for ch in INPUT_CHANNELS:
                        analog_data[ch].popleft()
            time.sleep(period)
    except KeyboardInterrupt:
        print("Data collection stopped.")
    finally:
        if card.is_valid():
            card.close()
        print("DAQ device closed.")

# ---------------- GUI PLOTTING ---------------- #
class RealTimeAnalogPlot(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Analog Signals")
        self.setGeometry(100, 100, 800, 500)

        self.graph_widget = pg.PlotWidget()
        self.setCentralWidget(self.graph_widget)
        self.graph_widget.setLabel('left', 'Signal Amplitude')
        self.graph_widget.setLabel('bottom', 'Time (s)')
        self.graph_widget.addLegend()
        self.graph_widget.setXRange(0, DURATION)

        self.curves = {
            ch: self.graph_widget.plot(pen=pg.intColor(i), name=f"Channel {ch}")
            for i, ch in enumerate(INPUT_CHANNELS)
        }

        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(10)

    def update_plot(self):
        with lock:
            if time_stamps:
                self.graph_widget.setXRange(time_stamps[0], time_stamps[-1])
                for ch in INPUT_CHANNELS:
                    self.curves[ch].setData(list(time_stamps), list(analog_data[ch]))

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    data_thread = threading.Thread(target=collect_analog_data, daemon=True)
    data_thread.start()

    app = QtWidgets.QApplication([])
    main_window = RealTimeAnalogPlot()
    main_window.show()
    app.exec()
