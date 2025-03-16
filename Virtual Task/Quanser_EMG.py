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

# Constants
BOARD_TYPE = "qpid_e"
BOARD_IDENTIFIER = "0"
FREQUENCY = 1000  # Hz (Sampling frequency)
DURATION = 2  # Rolling window duration (seconds)
SAMPLES = int(FREQUENCY * DURATION)  # Number of samples in rolling window
PERIOD = 1.0 / FREQUENCY

# Analog Input Channels
input_channels = np.array([1, 2], dtype=np.uint32)  # FLEXION_EMG (Ch 1), EXTENSION_EMG (Ch 2)
num_input_channels = len(input_channels)

# Buffers
input_buffer = np.zeros(num_input_channels, dtype=np.float64)  # Buffer for reading

# Data storage for rolling window
time_values = np.linspace(-DURATION, 0, SAMPLES)  # Time axis (rolling window)
emg_data = np.zeros((num_input_channels, SAMPLES))  # FLEXION_EMG and EXTENSION_EMG

# Initialize HIL board
card = HIL()
card.open(BOARD_TYPE, BOARD_IDENTIFIER)

# Setup Matplotlib figure
fig, ax = plt.subplots()
ax.set_xlim(-DURATION, 0)  # Rolling window of 2 seconds
ax.set_ylim(-5, 5)  # Adjust based on expected EMG signal range
ax.set_xlabel("Time (s)")
ax.set_ylabel("Voltage (V)")
ax.set_title("Real-Time EMG Signals")
line_flexion, = ax.plot([], [], label="FLEXION_EMG (Ch 1)", color="blue")
line_extension, = ax.plot([], [], label="EXTENSION_EMG (Ch 2)", color="red")
ax.legend()

# Real-time update function for animation
start_time = time.time()

def update(frame):
    global start_time, emg_data

    t = time.time() - start_time

    # Read EMG signals
    card.read_analog(input_channels, num_input_channels, input_buffer)

    # Shift data left and insert new values
    emg_data[:, :-1] = emg_data[:, 1:]  # Shift left
    emg_data[:, -1] = input_buffer  # Insert new reading

    # Update plot data
    line_flexion.set_data(time_values, emg_data[0])
    line_extension.set_data(time_values, emg_data[1])

    return line_flexion, line_extension

# Start animation
ani = animation.FuncAnimation(fig, update, interval=PERIOD * 1000, blit=False)

try:
    print("Running real-time EMG visualization. Press Ctrl+C to stop.")
    plt.show()
except KeyboardInterrupt:
    print("\nProcess stopped by user.")
finally:
    if card.is_valid():
        card.close()
    print("DAQ device closed successfully.")
