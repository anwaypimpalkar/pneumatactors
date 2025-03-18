import os
# Set QUARC DLL Path before importing Quanser modules
quarc_dll_path = r"C:\Program Files\Quanser\QUARC"
os.add_dll_directory(quarc_dll_path)

import time
import threading
import numpy as np
import pandas as pd
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
from collections import deque
from scipy.signal import butter, filtfilt
from quanser.hardware import HIL

# Constants
BOARD_TYPE = "qpid_e"
BOARD_IDENTIFIER = "0"
FREQUENCY = 1000  # Hz
INPUT_CHANNELS = np.array([1, 2], dtype=np.uint32)  # FLEXION_EMG (Ch 1), EXTENSION_EMG (Ch 2)
WINDOW_SIZE = 20  # Number of samples for filtering
DURATION = 10  # Duration in seconds

# Shared Data
latest_emg = np.zeros(len(INPUT_CHANNELS))  # Raw EMG
processed_emg = np.zeros(len(INPUT_CHANNELS))  # Filtered EMG
time_stamps = deque()  # Store timestamps dynamically
lock_emg = threading.Lock()
lock_processed = threading.Lock()
emg_window_buffer = {ch: deque(maxlen=WINDOW_SIZE) for ch in range(len(INPUT_CHANNELS))}
raw_data = deque()
filtered_data = deque()
stop_threads = False  # Flag to stop threads cleanly

def collect_emg_data():
    """Thread function to continuously collect EMG data."""
    global latest_emg, stop_threads
    period = 1.0 / FREQUENCY

    card = HIL()
    card.open(BOARD_TYPE, BOARD_IDENTIFIER)
    input_buffer = np.zeros(len(INPUT_CHANNELS), dtype=np.float64)

    try:
        start_time = time.time()
        while time.time() - start_time < DURATION:
            if stop_threads:
                break
            card.read_analog(INPUT_CHANNELS, len(INPUT_CHANNELS), input_buffer)
            with lock_emg:
                latest_emg[:] = input_buffer  # Update shared EMG array
            # time.sleep(period)
    except KeyboardInterrupt:
        print("EMG data collection stopped.")
    finally:
        if card.is_valid():
            card.close()
        print("DAQ device closed.")

def butter_lowpass_filter(data, cutoff=10, fs=1000, order=4):
    if len(data) < (order * 3):
        return np.mean(data) if len(data) > 0 else 0
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)

def emg_processing_thread():
    global processed_emg, stop_threads
    start_time = time.time()
    
    while time.time() - start_time < DURATION:
        if stop_threads:
            break
        with lock_emg:
            latest_read_emg = np.copy(latest_emg)

        for i, val in enumerate(latest_read_emg):
            emg_window_buffer[i].append(np.abs(val))

        if all(len(emg_window_buffer[i]) >= max(WINDOW_SIZE, 3 * 4) for i in range(len(INPUT_CHANNELS))):
            filtered_values = np.array([
                butter_lowpass_filter(list(emg_window_buffer[i]))[-1]
                for i in range(len(INPUT_CHANNELS))
            ])
            with lock_processed:
                processed_emg[:] = filtered_values
            
            # Store timestamp
            current_time = time.time() - start_time
            time_stamps.append(current_time)
            raw_data.append(np.mean(latest_emg))
            filtered_data.append(np.mean(processed_emg))
            
            # Ensure the time window remains within the last 10 seconds
            while time_stamps and time_stamps[0] < (current_time - DURATION):
                time_stamps.popleft()
                raw_data.popleft()
                filtered_data.popleft()
        else:
            with lock_processed:
                processed_emg[:] = np.zeros(len(INPUT_CHANNELS))
        # time.sleep(0.001)

class RealTimeEMGPlot(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time EMG Signal")
        self.setGeometry(100, 100, 800, 500)

        self.graph_widget = pg.PlotWidget()
        self.setCentralWidget(self.graph_widget)
        self.graph_widget.setLabel('left', 'EMG Amplitude')
        self.graph_widget.setLabel('bottom', 'Time (s)')
        self.graph_widget.addLegend()
        self.graph_widget.setXRange(0, DURATION)  # Fix x-axis range

        # self.raw_curve = self.graph_widget.plot(pen='r', name="Raw EMG")
        self.filtered_curve = self.graph_widget.plot(pen='y', name="Filtered EMG")

        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(10)

        # Close application after DURATION seconds
        QtCore.QTimer.singleShot(DURATION * 1000, self.close_application)

    def update_plot(self):
        if time_stamps:
            self.graph_widget.setXRange(0, DURATION)  # Ensure x-axis stays fixed
            # self.raw_curve.setData(list(time_stamps), list(raw_data))
            self.filtered_curve.setData(list(time_stamps), list(filtered_data))

    def close_application(self):
        global stop_threads
        print("Stopping application after 10 seconds.")
        stop_threads = True  # Stop the threads

        # Save data to CSV
        data_dict = {
            "Time (s)": list(time_stamps),
            "Raw EMG": list(raw_data),
            "Filtered EMG": list(filtered_data),
        }
        df = pd.DataFrame(data_dict)
        df.to_csv("emg_data.csv", index=False)  # Save to CSV file

        print("Data saved to emg_data.csv")
        QtWidgets.QApplication.instance().quit()

if __name__ == "__main__":
    emg_thread = threading.Thread(target=collect_emg_data, daemon=True)
    process_thread = threading.Thread(target=emg_processing_thread, daemon=True)
    emg_thread.start()
    process_thread.start()

    app = QtWidgets.QApplication([])
    main_window = RealTimeEMGPlot()
    main_window.show()
    app.exec()

    stop_threads = True
    emg_thread.join()
    process_thread.join()