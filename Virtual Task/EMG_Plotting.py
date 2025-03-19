import os
# Set QUARC DLL Path before importing Quanser modules
quarc_dll_path = r"C:\Program Files\Quanser\QUARC"
os.add_dll_directory(quarc_dll_path)

import time
import threading
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
from collections import deque
from scipy.signal import butter, filtfilt
from quanser.hardware import HIL
from scipy.signal import hilbert

# Constants
BOARD_TYPE = "qpid_e"
BOARD_IDENTIFIER = "0"
FREQUENCY = 1000  # Hz
INPUT_CHANNELS = np.array([1, 2], dtype=np.uint32)  # FLEXION_EMG (Ch 1), EXTENSION_EMG (Ch 2)
WINDOW_SIZE = 100  # Number of samples for filtering
DURATION = 5  # Duration in seconds

# Shared Data
latest_emg = np.zeros(len(INPUT_CHANNELS))  # Raw EMG
processed_emg = np.zeros(len(INPUT_CHANNELS))  # Filtered EMG
time_stamps = deque()  # Store timestamps dynamically
lock_emg = threading.Lock()
lock_processed = threading.Lock()
emg_window_buffer = {ch: deque(maxlen=WINDOW_SIZE) for ch in range(len(INPUT_CHANNELS))}

# Data storage for plotting
raw_data = deque()
filtered_data = deque()

def collect_emg_data():
    """Thread function to continuously collect EMG data."""
    global latest_emg
    period = 1.0 / FREQUENCY

    card = HIL()
    card.open(BOARD_TYPE, BOARD_IDENTIFIER)
    input_buffer = np.zeros(len(INPUT_CHANNELS), dtype=np.float64)

    try:
        start_time = time.time()
        while True:
            card.read_analog(INPUT_CHANNELS, len(INPUT_CHANNELS), input_buffer)
            with lock_emg:
                latest_emg[:] = input_buffer  # Update shared EMG array
            time.sleep(period)
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

def rms_filter(data):
    return np.sqrt(np.mean(np.square(data)))

def hilbert_envelope_filter(data, cutoff=10, fs=1000, order=4):
    """
    Applies Hilbert Transform to obtain the envelope and then 
    applies a Butterworth low-pass filter to smooth the envelope.
    
    Args:
        data (array): EMG signal
        cutoff (int): Low-pass filter cutoff frequency in Hz
        fs (int): Sampling frequency in Hz
        order (int): Order of the Butterworth filter
    
    Returns:
        float: Smoothed envelope value
    """
    if len(data) < (order * 3):
        return np.mean(data) if len(data) > 0 else 0

    # Compute the analytic signal using Hilbert Transform
    analytic_signal = hilbert(data)
    envelope = np.abs(analytic_signal)  # Envelope of the signal

    # Apply a low-pass filter to smooth the envelope
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    filtered_envelope = filtfilt(b, a, envelope)
    
    return filtered_envelope[-1]

def emg_processing_thread():
    global processed_emg
    start_time = time.time()
    
    while True:
        with lock_emg:
            latest_read_emg = np.copy(latest_emg)

        for i, val in enumerate(latest_read_emg):
            emg_window_buffer[i].append(np.abs(val))

        if all(len(emg_window_buffer[i]) >= max(WINDOW_SIZE, 3 * 4) for i in range(len(INPUT_CHANNELS))):
            filtered_values = np.array([
                # butter_lowpass_filter(list(emg_window_buffer[i]))[-1]
                rms_filter(list(emg_window_buffer[i]))
                # hilbert_envelope_filter(list(emg_window_buffer[i])) 
                for i in range(len(INPUT_CHANNELS))
            ])
            with lock_processed:
                # processed_emg[:] = filtered_values
                processed_emg[:] = np.abs(filtered_values)

            
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
            
            # print(f"Filtered EMG: {processed_emg}, Timestamp: {time_stamps[-1]}")
        else:
            with lock_processed:
                processed_emg[:] = np.zeros(len(INPUT_CHANNELS))
        time.sleep(0.001)

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
        self.graph_widget.setXRange(0, DURATION)

        self.raw_curve = self.graph_widget.plot(pen='r', name="Raw EMG")
        self.filtered_curve = self.graph_widget.plot(pen='y', name="Filtered EMG")

        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(10)

    def update_plot(self):
        if time_stamps:
            self.graph_widget.setXRange(time_stamps[0], time_stamps[-1])
            self.raw_curve.setData(list(time_stamps), list(raw_data))
            self.filtered_curve.setData(list(time_stamps), list(filtered_data))
            # print(f"Time Data (X-axis): {list(time_stamps)}")

if __name__ == "__main__":
    emg_thread = threading.Thread(target=collect_emg_data, daemon=True)
    process_thread = threading.Thread(target=emg_processing_thread, daemon=True)
    emg_thread.start()
    process_thread.start()

    app = QtWidgets.QApplication([])
    main_window = RealTimeEMGPlot()
    main_window.show()
    app.exec()
