import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt

def butter_lowpass_filter(data, cutoff=5, fs=1000, order=4):
    """
    Applies a low-pass Butterworth filter to the input data.

    Parameters:
    - data (np.ndarray): Input signal.
    - cutoff (float): Cutoff frequency in Hz.
    - fs (int): Sampling frequency in Hz.
    - order (int): Filter order.

    Returns:
    - np.ndarray: Filtered signal.
    """
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data, axis=1)

def process_emg(raw_emg, frequency=1000, plot=True):
    """
    Processes raw EMG signals by rectification and low-pass filtering.

    Parameters:
    - raw_emg (np.ndarray): Raw EMG data array (2 x N samples).
    - frequency (int): Sampling frequency in Hz.
    - plot (bool): If True, plots the filtered EMG signals.

    Returns:
    - np.ndarray: Processed EMG signals (envelope).
    """
    
    # Step 1: Rectify the signal (absolute value)
    rectified_emg = np.abs(raw_emg)

    # Step 2: Apply low-pass filtering to extract the envelope
    filtered_emg = butter_lowpass_filter(rectified_emg, cutoff=5, fs=frequency)

    if plot:
        # Setup Matplotlib figure
        duration = filtered_emg.shape[1] / frequency
        time_values = np.linspace(-duration, 0, filtered_emg.shape[1])

        fig, ax = plt.subplots()
        ax.set_xlim(-duration, 0)
        ax.set_ylim(0, np.max(filtered_emg) * 1.2)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Voltage (V)")
        ax.set_title("Processed EMG (Envelope)")
        ax.plot(time_values, filtered_emg[0], label="FLEXION_EMG (Filtered)", color="blue")
        ax.plot(time_values, filtered_emg[1], label="EXTENSION_EMG (Filtered)", color="red")
        ax.legend()
        
        # **Ensure the plot window opens**
        plt.draw()
        plt.pause(0.1)
        print("Displaying Processed EMG Plot...")
        plt.show(block=True)  # **Force plot window to stay open**

    return filtered_emg
