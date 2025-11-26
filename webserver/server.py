"""
server.py

Flask app that:
 - auto-discovers devices via connect_devices()
 - serves /controller (dynamic control panel)
 - serves /display (live plot)
 - exposes AJAX endpoints for all controls that map to your existing functions
    (switch_on, switch_off, heater_on, heater_off, device.write_setpoint, device.set_still_voltage)
 - has safe mocks if hardware libs are not available so you can run/test without devices
"""

from flask import Flask, render_template, request, jsonify, Response
import threading, time, io
import random
import sys

from cooldown_loop_dilution_v2 import switch_on, switch_off, heater_on, heater_off
from CTC100 import CTC100Device
from lakeshore224device import LakeShore224Device
from lakeshore372device import LakeShore372Device
import serial

from hardware_reader import HardwareTemperatureReader
from controller import hardware_lock
from controller import DeviceController
from device import connect_devices

# load devices and create controller
devices = connect_devices()
print("Detected devices:", list(devices.keys()))
controller = DeviceController(devices)

# create the reader
temp_reader = HardwareTemperatureReader(devices)

# temp hardware lock

app = Flask(__name__, template_folder="templates")

# ---------------------------------------------------------------------
# Channel mapping function (same mapping you used in PyQt)
# ---------------------------------------------------------------------
def get_channels_for_device(dev_name):
    if dev_name in ("CTC100A", "CTC100B"):
        return {
            "4puheat": "heater",
            "3puheat": "heater",
            "4swheat": "switch",
            "3swheat": "switch",
            "AIO3": "switch",
            "AIO4": "switch",
        }
    elif dev_name in ("LakeshoreModel372", "Lakeshore372"):
        return {"still": "still_heater"}
    # If you later add Lakeshore224 mapping, add here
    return {}

# ---------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------
@app.route("/")
def root():
    # simple redirect to /display (optional) or present links
    return """
    <h2>ARCTIC FOX interface</h2>
    <p><a href="/display">Display (live plot)</a></p>
    <p><a href="/controller">Controller (control panel)</a></p>
    """

@app.route("/display")
def display():
    return render_template("display.html")

@app.route("/controller")
def controller_page():
    # Pass the devices and channel mappings to Jinja template
    # For each device we pass device.name and channels
    devices_context = {}
    for dev_name, dev in devices.items():
        channels = get_channels_for_device(dev_name)
        devices_context[dev_name] = {
            "channels": channels
        }
    return render_template("controller.html", devices=devices_context)


# ---------------------------------------------------------------------
# CONTROL AJAX endpoints - accept JSON POSTs
# ---------------------------------------------------------------------

# -----------------------------
# SWITCH CONTROL
# -----------------------------
@app.route("/api/set_switch_voltage", methods=["POST"])
def api_set_switch():
    data = request.json
    controller.set_switch_voltage(
        data["device"], data["channel"], float(data["value"])
    )
    return jsonify(status="ok")

@app.route("/api/turn_off_switch", methods=["POST"])
def api_switch_off():
    data = request.json
    controller.turn_off_switch(
        data["device"], data["channel"]
    )
    return jsonify(status="ok")


# -----------------------------
# HEATER CONTROL
# -----------------------------
@app.route("/api/set_heater_temp", methods=["POST"])
def api_set_heater_temp():
    data = request.json
    controller.set_heater_temperature(
        data["device"], data["channel"], float(data["value"])
    )
    return jsonify(status="ok")

@app.route("/api/turn_off_heater", methods=["POST"])
def api_heater_off():
    data = request.json
    controller.turn_off_heater(
        data["device"], data["channel"]
    )
    return jsonify(status="ok")

@app.route("/api/toggle_heater", methods=["POST"])
def api_toggle_heater():
    data = request.json
    controller.toggle_heater(
        data["device"], data["channel"], bool(data["state"])
    )
    return jsonify(status="ok")


# -----------------------------
# STILL HEATER CONTROL
# -----------------------------
@app.route("/api/set_still_percentage", methods=["POST"])
def api_set_still():
    data = request.json
    controller.set_still_percentage(
        data["device"], data["channel"], float(data["value"])
    )
    return jsonify(status="ok")

@app.route("/api/turn_off_still", methods=["POST"])
def api_still_off():
    data = request.json
    controller.turn_off_still(
        data["device"], data["channel"]
    )
    return jsonify(status="ok")

# ---------------------------------------------------------------------
# Live plot backend — FOUR independent data streams
# ---------------------------------------------------------------------

# new structure:
# plot_data[device][channel] = list of values
# plot_data[device]["times"] = list of timestamps

plot_data = {
    "CTC100A": {"times": [], "4switchA": [], "4pumpA": [], "3switchA": [], "3pumpA": []},
    "CTC100B": {"times": [], "4switchB": [], "4pumpB": [], "3switchB": [], "3pumpB": []},
    "Lakeshore372": {"times": [], "MC": [], "Still": []},
    "Lakeshore224": {"times": [], "4HePotA": [], "3HePotA": [], "4HePotB": [], "3HePotB": [], "Condenser": [], "50K": [], "4K": []}
}

plot_lock = threading.Lock()

def background_update_thread():
    start_time = time.time()

    while True:
        with hardware_lock:
            temps = temp_reader.read_temperatures()

        t = time.time() - start_time

        with plot_lock:
            for dev_name, sensors in temps.items():

                # Ensure structure exists
                if dev_name not in plot_data:
                    plot_data[dev_name] = {"times": []}
                if "times" not in plot_data[dev_name]:
                    plot_data[dev_name]["times"] = []

                plot_data[dev_name]["times"].append(t)

                for ch, value in sensors.items():
                    if ch not in plot_data[dev_name]:
                        plot_data[dev_name][ch] = []
                    plot_data[dev_name][ch].append(value)

                # window = 300 seconds
                window = 300
                times = plot_data[dev_name]["times"]
                start = next((i for i,x in enumerate(times) if x >= t - window), 0)

                # trim to last 300 seconds
                for ch in plot_data[dev_name]:
                    plot_data[dev_name][ch] = plot_data[dev_name][ch][start:]

        time.sleep(2)

threading.Thread(target=background_update_thread, daemon=True).start()

@app.route("/plot/<int:plot_id>.png")
def plot_png(plot_id):
    import matplotlib.pyplot as plt

    if plot_id not in plot_data:
        return "Invalid plot ID", 404

    with plot_lock:
        ys = plot_data[plot_id][:]
    xs = list(range(len(ys)))

    buf = io.BytesIO()

    fig, ax = plt.subplots(figsize=(6, 3))   # a bit larger

    if xs and ys:
        ax.plot(xs, ys)
        ax.set_xlabel("sample #")

    ax.set_title(f"Plot {plot_id}")
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)

    buf.seek(0)
    return Response(buf.getvalue(), mimetype="image/png")

# Backwards-compatible small endpoint returning the 4 numeric single traces (if you still want them)
@app.route("/api/plotdata")
def api_plotdata():
    # Build up to 4 summary traces (CTC100A, CTC100B, Lakeshore372, Lakeshore224)
    with plot_lock:
        def last_channel_avg(dev, chname):
            devd = plot_data.get(dev, {})
            vals = devd.get(chname, [])
            return list(vals)
        return jsonify({
            "1": last_channel_avg("CTC100A", "4switchA"),
            "2": last_channel_avg("CTC100B", "4switchB"),
            "3": last_channel_avg("Lakeshore372", "MC"),
            "4": last_channel_avg("Lakeshore224", "4K Plate"),
        })

@app.route("/display/CTC100A")
def display_ctc100a():
    return render_template("display_single.html", title="CTC100A", plots=[1])

@app.route("/display/CTC100B")
def display_ctc100b():
    return render_template("display_single.html", title="CTC100B", plots=[2])

@app.route("/display/Lakeshore372")
def display_ls372():
    return render_template("display_single.html", title="Lakeshore 372", plots=[3])

@app.route("/display/Lakeshore224")
def display_ls224():
    return render_template("display_single.html", title="Lakeshore 224", plots=[4])


# ---------------------------------------------------------------------
# Run server
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # 0. Optionally re-scan devices each time you start; devices already scanned at import
    print("Starting Flask server. Devices:", list(devices.keys()))
    app.run(debug=True, host="0.0.0.0", port=5000)

