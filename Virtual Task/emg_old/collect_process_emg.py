import os

# Set QUARC DLL Path before importing Quanser modules
quarc_dll_path = r"C:\Program Files\Quanser\QUARC"
os.add_dll_directory(quarc_dll_path)

import time
import numpy as np
import threading
from quanser.hardware import HIL, HILError
from collections import deque
from scipy.signal import butter, filtfilt


# Constants
BOARD_TYPE = "qpid_e"
BOARD_IDENTIFIER = "0"
FREQUENCY = 1e5  # Hz
INPUT_CHANNELS = np.array([1, 2], dtype=np.uint32)  # FLEXION_EMG (Ch 1), EXTENSION_EMG (Ch 2)

# Shared Data
latest_emg = np.zeros(len(INPUT_CHANNELS))  # Latest EMG values (Flexion, Extension)
lock = threading.Lock()

def collect_emg_data():
    """Thread function to continuously collect EMG data."""
    global latest_emg
    period = 1.0 / FREQUENCY

    card = HIL()
    card.open(BOARD_TYPE, BOARD_IDENTIFIER)

    input_buffer = np.zeros(len(INPUT_CHANNELS), dtype=np.float64)

    try:
        while True:
            card.read_analog(INPUT_CHANNELS, len(INPUT_CHANNELS), input_buffer)
            with lock:
                latest_emg[:] = input_buffer  # Update shared EMG array
            time.sleep(period)  # Maintain sampling rate
    except KeyboardInterrupt:
        print("EMG data collection stopped.")
    finally:
        if card.is_valid():
            card.close()
        print("DAQ device closed.")

def read_latest_emg():
    """Function to safely read the latest EMG data."""
    with lock:
        return np.copy(latest_emg)  # Return a copy to prevent modification during read

WINDOW_SIZE = 20  # Number of samples needed before filtering
emg_window_buffer = {ch: deque(maxlen=WINDOW_SIZE) for ch in range(len(INPUT_CHANNELS))}

def butter_lowpass_filter(data, cutoff=10, fs=1000, order=4):
    """Applies a low-pass Butterworth filter, ensuring sufficient input length."""
    if len(data) < (order * 3):  # filtfilt requires at least `3 * order` samples
        return np.mean(data) if len(data) > 0 else 0  # Return average if data exists, else 0
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)

def process_emg():
    """Safely reads, rectifies, and filters EMG data in real-time."""
    with lock:
        latest_read_emg = np.copy(latest_emg)  # Read safely from shared EMG data
    
    # Update rolling buffer with new EMG values
    for i, val in enumerate(latest_read_emg):
        emg_window_buffer[i].append(np.abs(val))  # Rectify and store

    # Ensure enough data in buffer before filtering
    if all(len(emg_window_buffer[i]) >= WINDOW_SIZE for i in range(len(INPUT_CHANNELS))):
        filtered_values = np.array([
            butter_lowpass_filter(list(emg_window_buffer[i])) for i in range(len(INPUT_CHANNELS))
        ])
        return np.mean(filtered_values, axis=1)  # Return the average processed value
    
    return np.zeros(len(INPUT_CHANNELS))  # Return zeroes until enough data is collected

# Start EMG data collection in a separate thread
data_thread = threading.Thread(target=collect_emg_data, daemon=True)
data_thread.start()

# Example of reading EMG data without interfering with collection
while True:
    emg_values = process_emg()
    print(f"Latest EMG: Flexion: {emg_values[0]:.4f}, Extension: {emg_values[1]:.4f}")
