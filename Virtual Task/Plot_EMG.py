import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pandas as pd
import time

CSV_FILENAME = "emg_data.csv"
PLOT_WINDOW = 5  # Number of seconds to display

# Initialize plot
fig, ax = plt.subplots()
ax.set_xlabel("Time (s)")
ax.set_ylabel("Voltage (V)")
ax.set_title("Real-Time EMG Signal")
line_flexion, = ax.plot([], [], label="FLEXION_EMG (Ch 1)", color="blue")
line_extension, = ax.plot([], [], label="EXTENSION_EMG (Ch 2)", color="red")
ax.legend()
ax.grid()

# Function to read CSV and update plot
def update_plot(frame):
    try:
        df = pd.read_csv(CSV_FILENAME)
        if df.empty:
            return
        
        # Get last PLOT_WINDOW seconds of data
        current_time = time.time()
        df = df[df["Timestamp"] > (current_time - PLOT_WINDOW)]
        
        # Update plot data
        line_flexion.set_data(df["Timestamp"], df["FLEXION_EMG"])
        line_extension.set_data(df["Timestamp"], df["EXTENSION_EMG"])
        
        ax.set_xlim(df["Timestamp"].min(), df["Timestamp"].max())
        ax.set_ylim(df[["FLEXION_EMG", "EXTENSION_EMG"]].min().min() - 0.5, 
                    df[["FLEXION_EMG", "EXTENSION_EMG"]].max().max() + 0.5)

    except Exception as e:
        print(f"Error reading file: {e}")

# Use Matplotlib animation for real-time updates
ani = animation.FuncAnimation(fig, update_plot, interval=50)
plt.show()
