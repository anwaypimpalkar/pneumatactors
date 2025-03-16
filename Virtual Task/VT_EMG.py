import os
# Set QUARC DLL Path before importing Quanser modules
quarc_dll_path = r"C:\Program Files\Quanser\QUARC"
os.add_dll_directory(quarc_dll_path)

import time
import numpy as np
import matplotlib.pyplot as plt
import threading
from scipy.signal import iirfilter, lfilter
from quanser.hardware import HIL

# ---------------------------
# Optimized EMG Processing Functions
# ---------------------------
def butter_lowpass_iir(cutoff=5, fs=1000, order=4):
    """Creates a real-time IIR low-pass filter (for speed)."""
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = iirfilter(order, normal_cutoff, btype='low', ftype='butter')
    return b, a

# Get filter coefficients
b, a = butter_lowpass_iir()

def process_emg(emg_signal, z=None):
    """Rectifies and filters EMG in real time using an IIR filter."""
    rectified = np.abs(np.atleast_1d(emg_signal))
    if z is None:
        filtered, z = lfilter(b, a, rectified, zi=np.zeros(max(len(a), len(b)) - 1))
    else:
        filtered, z = lfilter(b, a, rectified, zi=z)
    return filtered, z  # Return processed EMG and filter state

# ---------------------------
# Setup DAQ Board & Buffers
# ---------------------------
BOARD_TYPE = "qpid_e"
BOARD_IDENTIFIER = "0"
frequency = 1000  # Hz
window_size = 500  # Store last 500 samples (~0.5 sec)

# Analog Input Channels
input_channels = np.array([1, 2], dtype=np.uint32)  # FLEXION_EMG (Ch 1), EXTENSION_EMG (Ch 2)
num_input_channels = len(input_channels)

# Buffers (Shared Memory for Multithreading)
shared_emg_data = np.zeros((num_input_channels, window_size))  # Circular buffer
shared_index = 0  # Current index in the buffer
emg_flexion_z, emg_extension_z = None, None  # Filter states
lock = threading.Lock()  # Thread synchronization lock

# Initialize HIL board
card = HIL()
card.open(BOARD_TYPE, BOARD_IDENTIFIER)

# ---------------------------
# Data Collection Thread (Thread-1)
# ---------------------------
def collect_emg():
    """Continuously reads EMG data and stores it in the shared buffer."""
    global shared_emg_data, shared_index, emg_flexion_z, emg_extension_z

    input_buffer = np.zeros(num_input_channels, dtype=np.float64)  # Raw EMG readings
    while True:
        # Read EMG signals
        card.read_analog(input_channels, num_input_channels, input_buffer)

        # Process EMG in real time using IIR filter
        processed_flexion, emg_flexion_z = process_emg(input_buffer[0], emg_flexion_z)
        processed_extension, emg_extension_z = process_emg(input_buffer[1], emg_extension_z)

        # Store data in shared buffer
        with lock:  # Lock to avoid race conditions
            shared_emg_data[:, shared_index] = [processed_flexion, processed_extension]
            shared_index = (shared_index + 1) % window_size  # Circular buffer index

        # Print debug info
        print(f"Raw: {input_buffer}, Processed: [{processed_flexion}, {processed_extension}]")

        time.sleep(1.0 / frequency)  # Non-blocking sleep to match sampling rate

# ---------------------------
# Plotting Thread (Thread-2)
# ---------------------------
def plot_emg():
    """Continuously plots EMG data from the shared buffer."""
    fig, ax = plt.subplots()
    ax.set_ylim(0, 5)  # Adjust based on expected EMG range
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Voltage (V)")
    ax.set_title("Processed EMG (Envelope)")
    line_flexion, = ax.plot(np.zeros(window_size), label="FLEXION_EMG (Filtered)", color="blue")
    line_extension, = ax.plot(np.zeros(window_size), label="EXTENSION_EMG (Filtered)", color="red")
    ax.legend()

    while True:
        with lock:
            flexion_values = np.roll(shared_emg_data[0, :], -shared_index)
            extension_values = np.roll(shared_emg_data[1, :], -shared_index)

        # Fast update using `set_ydata()`
        line_flexion.set_ydata(flexion_values)
        line_extension.set_ydata(extension_values)
        ax.set_xlim(0, window_size)

        plt.draw()
        plt.pause(0.001)  # Allow updates without blocking

# ---------------------------
# Start Both Threads
# ---------------------------
if __name__ == "__main__":
    # Start data collection thread
    thread_collect = threading.Thread(target=collect_emg, daemon=True)
    thread_collect.start()

    # Start plotting in the main thread
    plot_emg()  # Blocking call (runs until the user closes the plot)
