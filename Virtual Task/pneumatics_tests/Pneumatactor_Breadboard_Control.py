import tkinter as tk
from tkinter import ttk
from aardvark_api.python.aardvark_py import *
from array import array

# Constants
I2C_BITRATE = 400  # I2C bitrate in kHz
VALVE_ADDRESSES = [0x40, 0x60, 0x55]  # Addresses of the three valves
PUMP_ADDRESS = 0x10  # Address of the pump


def send_number_to_address(address, number):
    """Send a number to a specific I2C address."""
    aardvark_handle = aa_open(0)
    if aardvark_handle <= 0:
        print(f"Unable to open Aardvark device. Error code: {aardvark_handle}")
        return

    aa_configure(aardvark_handle, AA_CONFIG_SPI_I2C)
    aa_i2c_bitrate(aardvark_handle, I2C_BITRATE)
    aa_i2c_pullup(aardvark_handle, AA_I2C_PULLUP_BOTH)

    data = array("B", [number])
    num_written = aa_i2c_write(aardvark_handle, address, AA_I2C_NO_FLAGS, data)

    if num_written < 0:
        print(f"Error writing to address {hex(address)}. Error code: {num_written}")
    elif num_written != len(data):
        print(
            f"Partial write to {hex(address)}. Expected {len(data)} bytes, wrote {num_written} bytes."
        )
    else:
        # print(f"Successfully sent {number} to address {hex(address)}")
        pass

    aa_close(aardvark_handle)


class ControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Valve and Pump Controller")

        self.valve_sliders = []
        self.valve_labels = []

        for i, addr in enumerate(VALVE_ADDRESSES):
            frame = ttk.Frame(root)
            frame.pack(pady=5)

            label = ttk.Label(frame, text=f"Valve {i+1} ({hex(addr)})")
            label.pack(side=tk.LEFT)

            slider = ttk.Scale(
                frame,
                from_=0,
                to=100,
                orient=tk.HORIZONTAL,
                command=lambda val, i=i, addr=addr: self.update_value(
                    i, addr, int(float(val))
                ),
            )
            slider.pack(side=tk.LEFT, padx=5)

            value_label = ttk.Label(frame, text="0")
            value_label.pack(side=tk.LEFT)

            self.valve_sliders.append(slider)
            self.valve_labels.append(value_label)

        frame = ttk.Frame(root)
        frame.pack(pady=5)

        pump_label = ttk.Label(frame, text=f"Pump ({hex(PUMP_ADDRESS)})")
        pump_label.pack(side=tk.LEFT)

        self.pump_slider = ttk.Scale(
            frame,
            from_=0,
            to=255,
            orient=tk.HORIZONTAL,
            command=lambda val: self.update_pump(int(float(val))),
        )
        self.pump_slider.pack(side=tk.LEFT, padx=5)

        self.pump_value_label = ttk.Label(frame, text="0")
        self.pump_value_label.pack(side=tk.LEFT)

        emergency_button = ttk.Button(
            root, text="Emergency Stop", command=self.emergency_stop
        )
        emergency_button.pack(pady=10)

    def update_value(self, index, address, value):
        """Update the displayed value and send it to the corresponding valve."""
        self.valve_labels[index].config(text=str(value))
        send_number_to_address(address, value)

    def update_pump(self, value):
        """Update the displayed value and send it to the pump."""
        self.pump_value_label.config(text=str(value))
        send_number_to_address(PUMP_ADDRESS, value)

    def emergency_stop(self):
        """Set all values to zero and send to all addresses."""
        for i, addr in enumerate(VALVE_ADDRESSES):
            self.valve_sliders[i].set(0)
            self.valve_labels[i].config(text="0")
            send_number_to_address(addr, 0)

        self.pump_slider.set(0)
        self.pump_value_label.config(text="0")
        send_number_to_address(PUMP_ADDRESS, 0)
        print("Emergency Stop Activated: All values set to 0")


if __name__ == "__main__":
    root = tk.Tk()
    app = ControlGUI(root)
    root.mainloop()