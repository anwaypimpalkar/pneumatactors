import os

# Set QUARC DLL Path before importing Quanser modules
quarc_dll_path = r"C:\Program Files\Quanser\QUARC"
os.add_dll_directory(quarc_dll_path)

import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from array import array
from quanser.hardware import HIL, HILError


def collect_raw_emg(duration=2, frequency=1000, plot=True):
    """
    Collects raw EMG data from QPIDe analog input channels 1 and 2.

    Parameters:
    - duration (float): Duration of the rolling window in seconds.
    - frequency (int): Sampling frequency in Hz.
    - plot (bool): If True, plots the data in real-time.

    Returns:
    - np.ndarray: Raw EMG data (2 x N samples).
    """
    
    # Board Constants
    BOARD_TYPE = "qpid_e"
    BOARD_IDENTIFIER = "0"
    
    # Sampling & Storage
    samples = int(frequency * duration)
    period = 1.0 / frequency

    # Analog Input Channels
    input_channels = np.array([1, 2], dtype=np.uint32)  # FLEXION_EMG (Ch 1), EXTENSION_EMG (Ch 2)
    num_input_channels = len(input_channels)
    
    # Buffers
    input_buffer = np.zeros(num_input_channels, dtype=np.float64)  # Buffer for reading
    emg_data = np.zeros((num_input_channels, samples))  # Data storage
    time_values = np.linspace(-duration, 0, samples)  # Time axis

    # Initialize HIL board
    card = HIL()
    card.open(BOARD_TYPE, BOARD_IDENTIFIER)

    if plot:
        # Setup Matplotlib figure
        fig, ax = plt.subplots()
        ax.set_xlim(-duration, 0)
        ax.set_ylim(-5, 5)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Voltage (V)")
        ax.set_title("Real-Time EMG Signals")
        line_flexion, = ax.plot([], [], label="FLEXION_EMG (Ch 1)", color="blue")
        line_extension, = ax.plot([], [], label="EXTENSION_EMG (Ch 2)", color="red")
        ax.legend()

    start_time = time.time()
    for i in range(samples):
        t = time.time() - start_time

        # Read EMG signals
        card.read_analog(input_channels, num_input_channels, input_buffer)

        # Store data
        emg_data[:, i] = input_buffer

        # Update plot if enabled
        if plot:
            line_flexion.set_data(time_values[:i+1], emg_data[0, :i+1])
            line_extension.set_data(time_values[:i+1], emg_data[1, :i+1])
            plt.pause(0.001)  # Allow the plot to update

        time.sleep(period)

    if plot:
        plt.show()

    # Close DAQ device
    if card.is_valid():
        card.close()
    print("DAQ device closed successfully.")

    return emg_data
