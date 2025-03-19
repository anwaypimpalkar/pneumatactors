import os
# Set QUARC DLL Path before importing Quanser modules
quarc_dll_path = r"C:\Program Files\Quanser\QUARC"
os.add_dll_directory(quarc_dll_path)

import time
import csv
import threading
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
from collections import deque
from scipy.signal import butter, filtfilt
from quanser.hardware import HIL
from scipy.signal import hilbert, find_peaks
import pandas as pd
import plotly.express as px

# Constants
BOARD_TYPE = "qpid_e"
BOARD_IDENTIFIER = "0"
FREQUENCY = 1000  # Hz
INPUT_CHANNELS = np.array([1, 2], dtype=np.uint32)  # FLEXION_EMG (Ch 1), EXTENSION_EMG (Ch 2)
WINDOW_SIZE = 100  # Number of samples for filtering
DURATION = 10  # Duration in seconds
PARTICIPANT = "p02"

if not os.path.exists(f"{PARTICIPANT}"):
    os.makedirs(f"{PARTICIPANT}")
    print(f"Directory '{PARTICIPANT}' created.")
else:
    print(f"Directory '{PARTICIPANT}' already exists.")

# Shared Data
latest_emg = np.zeros(len(INPUT_CHANNELS))  # Raw EMG
processed_emg = np.zeros(len(INPUT_CHANNELS))  # Filtered EMG
time_stamps = deque()  # Store timestamps dynamically
lock_emg = threading.Lock()
lock_processed = threading.Lock()
emg_window_buffer = {ch: deque(maxlen=WINDOW_SIZE) for ch in range(len(INPUT_CHANNELS))}
start_event = threading.Event()

# Data storage for plotting
raw_data = deque()
filtered_data = deque()
start_time = None  # Track when the first EMG sample is read
true_start = 0
first_point = True

def collect_emg_data():
    """Thread function to initialize DAQ, discard zero EMG values, and start logging from first valid EMG."""
    global latest_emg, start_time
    period = 1.0 / FREQUENCY

    card = HIL()
    card.open(BOARD_TYPE, BOARD_IDENTIFIER)
    input_buffer = np.zeros(len(INPUT_CHANNELS), dtype=np.float64)


    while True:
        card.read_analog(INPUT_CHANNELS, len(INPUT_CHANNELS), input_buffer)

        # Check if any EMG channel is non-zero
        if np.any(input_buffer[0] != 0):
            start_time = time.time()  # Set first valid EMG timestamp as `t=0s`
            start_event.set()  # RELEASE the lock → Start GUI + logging
            break

        time.sleep(period)  # Continue discarding zero values

    try:
        while True:
            card.read_analog(INPUT_CHANNELS, len(INPUT_CHANNELS), input_buffer)

            with lock_emg:
                latest_emg[:] = input_buffer  # Now store actual data

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
    global processed_emg, first_point, true_start, start_time  # Use global start_time

    # Wait for first valid EMG before processing starts
    start_event.wait()

    while time.time() - start_time < DURATION:
        with lock_emg:
            latest_read_emg = np.copy(latest_emg)

        for i, val in enumerate(latest_read_emg):
            emg_window_buffer[i].append(np.abs(val))

        if all(len(emg_window_buffer[i]) >= max(WINDOW_SIZE, 3 * 4) for i in range(len(INPUT_CHANNELS))):
            filtered_values = np.array([
                rms_filter(list(emg_window_buffer[i]))
                for i in range(len(INPUT_CHANNELS))
            ])
            with lock_processed:
                processed_emg[:] = np.abs(filtered_values)

            # Store timestamp
            current_time = time.time() - start_time  
            if first_point:
                true_start = current_time  # Correctly track first point
                first_point = False
            current_time -= true_start  # Normalize timestamp

            time_stamps.append(current_time)
            raw_data.append(np.mean(latest_emg))
            filtered_data.append(np.mean(processed_emg))

            time.sleep(0.00001)

            # Ensure time window remains within the last `DURATION` seconds
            while time_stamps and time_stamps[0] < (current_time - DURATION):
                time_stamps.popleft()
                raw_data.popleft()
                filtered_data.popleft()
            
        else:
            with lock_processed:
                processed_emg[:] = np.zeros(len(INPUT_CHANNELS))
                
        
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
        self.graph_widget.setXRange(0, DURATION, padding=0)

        self.raw_curve = self.graph_widget.plot(pen='r', name="Raw EMG")
        self.filtered_curve = self.graph_widget.plot(pen='y', name="Filtered EMG")

        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(10)

    def update_plot(self):
        if time_stamps:
            self.graph_widget.setXRange(0, DURATION, padding=0)
            self.raw_curve.setData(list(time_stamps), list(raw_data))
            self.filtered_curve.setData(list(time_stamps), list(filtered_data))

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    main_window = RealTimeEMGPlot()
    main_window.show()

    time.sleep(2)

    emg_thread = threading.Thread(target=collect_emg_data, daemon=True)
    process_thread = threading.Thread(target=emg_processing_thread, daemon=True)
    emg_thread.start()
    process_thread.start()

    # Wait for data collection to officially start (after the 2s discard phase)
    print("Waiting to start..")
    start_event.wait()  # Blocks until `start_event.set()` is triggered

    # Start GUI shutdown timer AFTER official `t=0s` start
    QtCore.QTimer.singleShot(int((DURATION+true_start) * 1000), app.quit)

    app.exec()

    # Normalize timestamps so first value is 0
    normalized_time_stamps = [t for t in time_stamps]  # Already normalized in `emg_processing_thread()`

    raw_file = f"{PARTICIPANT}/{PARTICIPANT}_calibration_raw.csv"
    calibration_file = f"{PARTICIPANT}/{PARTICIPANT}_calibration.csv"

    # Save EMG data to CSV
    with open(raw_file, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp (s)", "Raw EMG", "Filtered EMG"])  # Header
        for t, raw, filt in zip(normalized_time_stamps, raw_data, filtered_data):
            writer.writerow([t, raw, filt])  # Now timestamps start at 0

    print("EMG data successfully saved to emg_data.csv")

    # Load the saved CSV file
    df = pd.read_csv(raw_file)

    # Extract the Filtered EMG data
    filtered_emg = df["Filtered EMG"].values
    timestamps = df["Timestamp (s)"].values

    # Find peaks in the filtered EMG signal
    peaks, _ = find_peaks(filtered_emg, height=np.mean(filtered_emg), distance=500)  # Adaptive threshold

    # Calculate mean of peak values
    peak_values = filtered_emg[peaks]
    mean_peak_value = np.mean(peak_values)

    # Estimate the baseline (average of lowest 10% values)
    sorted_emg = np.sort(filtered_emg)
    # Find first peak
    if len(peaks) > 0:
        first_peak_index = peaks[0]  # First detected peak index
    else:
        first_peak_index = 0  # Fallback if no peaks are found

    # Extract only values after the first peak
    emg_after_first_peak = filtered_emg[first_peak_index:]

    # Compute baseline from the lowest 10% values after first peak
    sorted_emg_after_peak = np.sort(emg_after_first_peak)
    baseline_values = sorted_emg_after_peak[:int(0.1 * len(sorted_emg_after_peak))]  # Lowest 10%
    average_baseline = np.mean(baseline_values)

    # Print results
    print(f"Mean of Peaks: {mean_peak_value:.4f}")
    print(f"Average Baseline: {average_baseline:.4f}")
    print(f"Number of Peaks Detected: {len(peaks)}")

    # Plot the data with peaks marked
    fig = px.line(df, x="Timestamp (s)", y="Filtered EMG", title=f"EMG Calibration Plot: {PARTICIPANT}")
    fig.add_scatter(x=timestamps[peaks], y=filtered_emg[peaks], mode="markers", name="Peaks", marker=dict(color='red', size=8))
    fig.update_layout(xaxis_title="Time (s)", yaxis_title="EMG Signal", template="plotly_dark")
    fig.add_hline(y=mean_peak_value, line_dash="dash", line_color="white", annotation_text=f"Mean Peak Height = {mean_peak_value:.4f}", annotation_position="top right")
    fig.add_hline(y=average_baseline, line_dash="dash", line_color="white", annotation_text=f"Mean Baseline = {average_baseline:.4f}", annotation_position="bottom right")

    # Show the plot
    fig.show()

    # Save EMG analysis results
    with open(calibration_file, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["mean_max", "mean_min", "num_peaks"])
        writer.writerow([mean_peak_value, average_baseline, len(peaks)])

    print(f"EMG calibration results saved to {calibration_file}")
