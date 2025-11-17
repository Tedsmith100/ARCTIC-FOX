import time
import serial
import h5py
import numpy as np
import serial.tools.list_ports
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from CTC100 import CTC100Device
from lakeshore224device import LakeShore224Device
from lakeshore372device import LakeShore372Device


def connect_devices():
    devices = serial.tools.list_ports.comports()

    ctc100A = None
    ctc100B = None
    model224 = None
    model372 = None

    for device in devices:
        if 'FT230X' in device.description:
            if 'DK0CDLQP' in device.serial_number:
                ctc100B = CTC100Device(address=device.device, name='CTC100B')
            elif 'DK0CDKFB' in device.serial_number:
                ctc100A = CTC100Device(address=device.device, name='CTC100A')
        elif '224' in device.description:
            model224 = LakeShore224Device(port=device.device, name='LakeshoreModel224')
        elif '372' in device.description:
            model372 = LakeShore372Device(port=device.device, name='LakeshoreModel372')

    connected = {
        "CTC100A": ctc100A,
        "CTC100B": ctc100B,
        "LakeshoreModel224": model224,
        "LakeshoreModel372": model372,
    }

    return {k: v for k, v in connected.items() if v is not None}


def read_temperatures(devices): # Channels currently hardcoded, sorry, could change names here also, see fridge diagram for labels
    readings = {}

    if "CTC100A" in devices:
        dev = devices["CTC100A"]
        readings["CTC100A"] = {
            "4switch": dev.get_temperature("4switch"),
            "4pump": dev.get_temperature("4pump"),
            "3switch": dev.get_temperature("3switch"),
            "3pump": dev.get_temperature("3pump"),
        }

    if "CTC100B" in devices:
        dev = devices["CTC100B"]
        readings["CTC100B"] = {
            "4switch": dev.get_temperature("4switch"),
            "4pump": dev.get_temperature("4pump"),
            "3switch": dev.get_temperature("3switch"),
            "3pump": dev.get_temperature("3pump"),
        }

    if "LakeshoreModel224" in devices:
        dev = devices["LakeshoreModel224"]
        readings["LakeshoreModel224"] = {
            "C1": dev.get_temperature("C1"),
            "B": dev.get_temperature("B"),
            "C2": dev.get_temperature("C2"),
            "D1": dev.get_temperature("D1"),
            "A": dev.get_temperature("A"),
            "D2": dev.get_temperature("D2"),
            "D3": dev.get_temperature("D3"),
        }

    if "LakeshoreModel372" in devices:
        dev = devices["LakeshoreModel372"]
        readings["LakeshoreModel372"] = {
            "1": dev.get_temperature("1"),
            "A": dev.get_temperature("A"),
        }

    return readings


def setup_plots(device_data):
    num_devices = len(device_data)
    nrows = (num_devices + 1) // 2
    ncols = 2 if num_devices > 1 else 1
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, nrows * 3))

    if num_devices == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    lines = {}
    data = {}

    for ax, (dev_name, sensors) in zip(axes, device_data.items()):
        ax.set_title(dev_name)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Temperature (K)")
        ax.grid(True)

        lines[dev_name] = []
        data[dev_name] = {ch: [] for ch in sensors.keys()}
        data[dev_name]['times'] = []

        for ch in sensors.keys():
            (line,) = ax.plot([], [], lw=2, label=ch)
            lines[dev_name].append(line)

        ax.legend()

    plt.tight_layout()
    return fig, axes, lines, data


def main():
    devices = connect_devices()
    if not devices:
        print("No devices found. Exiting.")
        return

    # Initial temperature read
    initial_data = read_temperatures(devices)
    fig, axes, lines, data = setup_plots(initial_data)

    # ---- HDF5 SETUP ----
    # Record real time data to h5
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"temperature_log_{timestamp}.h5"
    h5file = h5py.File(filename, "w")

    h5_groups = {}
    for dev_name, sensors in initial_data.items():
        grp = h5file.create_group(dev_name)
        h5_groups[dev_name] = grp

        # Create datasets we can add to
        grp.create_dataset("time", shape=(0,), maxshape=(None,), dtype=float)

        for ch in sensors.keys():
            grp.create_dataset(ch, shape=(0,), maxshape=(None,), dtype=float)

    print(f"Logging to: {filename}")

    window_seconds = 1200 # How wide do you want the plotting window (s)? None = full history
    start_time = time.time()

    def append_to_dataset(ds, value):
        ds.resize((ds.shape[0] + 1,))
        ds[-1] = value

    def update(frame):
        current_time = time.time() - start_time # records time since start
        readings = read_temperatures(devices)

        for dev_name, sensors in readings.items():
            grp = h5_groups[dev_name]

            # Append time
            append_to_dataset(grp["time"], current_time)
            data[dev_name]["times"].append(current_time)

            # Append each channel
            for i, (ch, temp) in enumerate(sensors.items()):
                append_to_dataset(grp[ch], temp)
                data[dev_name][ch].append(temp)

                # Sliding window for plotting
                times = data[dev_name]["times"]
                if window_seconds:
                    start_idx = next((j for j, t in enumerate(times)
                                      if t >= current_time - window_seconds), 0)
                    xdata = times[start_idx:]
                    ydata = data[dev_name][ch][start_idx:]
                else:
                    xdata = times
                    ydata = data[dev_name][ch]

                lines[dev_name][i].set_data(xdata, ydata)

            # Updates axes
            ax = axes[list(devices.keys()).index(dev_name)]
            if window_seconds:
                ax.set_xlim(max(0, current_time - window_seconds), current_time)
            else:
                ax.set_xlim(0, current_time)
            ax.relim()
            ax.autoscale_view(scalex=False, scaley=True)

        # Ensure data is written to disk
        h5file.flush()

        return [l for sub in lines.values() for l in sub]

    # Live plots
    ani = animation.FuncAnimation(
        fig, update, interval=2000, blit=False, cache_frame_data=False)  # CHANGE INTERVAL TO CHANGE SAMPLE RATE
    
    try:
        plt.show()
    finally:
        print("Closing HDF5 file...")
        h5file.close()
        print("Closed.")

if __name__ == "__main__":
    main()
