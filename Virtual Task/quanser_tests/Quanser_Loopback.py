import os
import time
import math
import numpy as np
import matplotlib.pyplot as plt
from array import array

# Set QUARC DLL Path
quarc_dll_path = r"C:\Program Files\Quanser\QUARC"

os.add_dll_directory(quarc_dll_path)

from quanser.hardware import HIL, HILError
# Constants
BOARD_TYPE = "qpid_e"
BOARD_IDENTIFIER = "0"
FREQUENCY = 1000  # Hz (Sampling frequency)
SINE_FREQUENCY = 10  # Hz (Sine wave frequency)
DURATION = 0.5  # seconds
SAMPLES = int(FREQUENCY * DURATION)  # Total number of samples
PERIOD = 1.0 / FREQUENCY

# Analog Channels
input_channels = np.array([1, 2], dtype=np.uint32)   # Analog Input Channels
output_channels = np.array([1, 2], dtype=np.uint32)  # Analog Output Channels
num_input_channels = len(input_channels)
num_output_channels = len(output_channels)

# Buffers
initial_voltages = np.full(num_output_channels, 5.0, dtype=np.float64)  # Initialize outputs to 5V
input_buffer = np.zeros(num_input_channels, dtype=np.float64)   # Buffer for reading
output_buffer = np.zeros(num_output_channels, dtype=np.float64)  # Buffer for writing

# Initialize HIL board
card = HIL()
try:
    card.open(BOARD_TYPE, BOARD_IDENTIFIER)

    # Write initial voltages (5V)
    card.write_analog(output_channels, num_output_channels, initial_voltages)

    # Data storage for plotting
    time_values = []
    ai_data = [[] for _ in range(num_input_channels)]
    ao_data = [[] for _ in range(num_output_channels)]

    print("Starting real-time loopback test...")
    start_time = time.time()

    for i in range(SAMPLES):
        t = time.time() - start_time

        # Generate sine wave values
        for ch in range(num_output_channels):
            output_buffer[ch] = (ch + 7) * math.sin(2 * math.pi * SINE_FREQUENCY * t)

        # Read & Write Analog I/O
        card.read_analog_write_analog(input_channels, num_input_channels,
                                      output_channels, num_output_channels,
                                      input_buffer, output_buffer)

        # Store values
        time_values.append(t)
        for ch in range(num_input_channels):
            ai_data[ch].append(input_buffer[ch])
        for ch in range(num_output_channels):
            ao_data[ch].append(output_buffer[ch])

        # Maintain real-time execution
        time.sleep(PERIOD)

    print("Test complete. Plotting results...")

    # Plot results
    plt.figure(figsize=(10, 6))
    for ch in range(num_output_channels):
        plt.plot(time_values, ao_data[ch], linestyle='--', label=f"AO {ch} (Generated)")
        plt.plot(time_values, ai_data[ch], label=f"AI {ch} (Measured)")

    plt.xlabel("Time (s)")
    plt.ylabel("Voltage (V)")
    plt.title("Analog Loopback Test: Output vs Input")
    plt.legend()
    plt.grid()
    plt.show()

except HILError as e:
    print(f"QUARC Error: {e.get_error_message()}")

finally:
    if card.is_valid():
        card.close()
    print("DAQ device closed successfully.")