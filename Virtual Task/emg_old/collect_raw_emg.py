import os

# Set QUARC DLL Path before importing Quanser modules
quarc_dll_path = r"C:\Program Files\Quanser\QUARC"
os.add_dll_directory(quarc_dll_path)


import time
import numpy as np
import threading
from quanser.hardware import HIL, HILError


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

# Start EMG data collection in a separate thread
data_thread = threading.Thread(target=collect_emg_data, daemon=True)
data_thread.start()

# Example of reading EMG data without interfering with collection
while True:
    emg_values = read_latest_emg()
    print(f"Latest EMG: Flexion: {emg_values[0]:.4f}, Extension: {emg_values[1]:.4f}")
