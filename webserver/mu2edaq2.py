from remote_controller import RemoteController
from remote_readout import DBReader
from flask import Flask, render_template, request, jsonify
from sql import SQL

import queue
from algorithm import Cycle, AlgorithmConfig

HOST = "0.0.0.0"
PORT = 8084

LAST_VALUES = {}
LAST_STATES = {}

app = Flask(__name__, template_folder="templates")

controller = RemoteController(HOST, PORT)
channel_info = controller.get_channels()
channels = channel_info.keys()

algorithm_config = AlgorithmConfig()
cycle_thread = Cycle(controller, algorithm_config, LAST_VALUES, LAST_STATES)
cycle_thread.start()

for ch in channels:
    LAST_VALUES[ch] = None
    LAST_STATES[ch] = "off"

@app.route("/")
def root():
    return """
    <h2>ARCTIC FOX interface</h2>
    <p><a href="/interactive">Display (interactive plot)</a></p>
    <p><a href="/controller">Controller (control panel)</a></p>
    <p><a href="/algorithm">Algorithm (config panel)</a></p>
    """

# Algorithm
@app.route("/algorithm")
def algorithm_page():
    return render_template("algorithm.html", defaults=algorithm_config)

@app.route("/api/algorithm/config", methods=["POST"])
def set_algorithm_config():

    data = request.json
    side = data["side"]
    key = data["key"]
    value = data["value"]

    side_cfg = getattr(algorithm_config, side)
    setattr(side_cfg, key, value)

    return jsonify({"status": "ok"})

@app.route("/api/algorithm/status")
def algorithm_status():
    return jsonify(cycle_thread.get_status())

@app.route("/api/algorithm/start", methods=["POST"])
def start_algorithm():
    cycle_thread.cmd_start()
    return jsonify({"status": "started"})

@app.route("/api/algorithm/stop", methods=["POST"])
def stop_algorithm():
    cycle_thread.cmd_stop()
    return jsonify({"status": "stopped"})

@app.route("/api/algorithm/initial_precool", methods=["POST"])
def algorithm_initial_precool():
    data = request.json
    value = float(data["value"])
    cycle_thread.cmd_initial_precool(value)
    return jsonify({"status": "ok"})

@app.route("/api/algorithm/pre_cycle_cool", methods=["POST"])
def algorithm_pre_cool_cycle():
    data = request.json
    value = float(data["value"])
    cycle_thread.cmd_pre_cycle_cool(value)
    return jsonify({"status": "ok"})


# Controller UI
# filter only channels that should appear in controller
controller_channels = [ch for ch,info in channel_info.items() if info[1]]

@app.route("/controller")
def controller_page():

    return render_template(
        "controller.html",
        channels=controller_channels,
        channel_info=channel_info,
        last_values=LAST_VALUES,
        last_states=LAST_STATES
    )

@app.route("/api/controller_state")
def api_controller_state():

    return jsonify({
        "values": LAST_VALUES,
        "states": LAST_STATES
    })

@app.route("/api/set_value", methods=["POST"])
def api_set_value():

    data = request.json
    ch = data["channel"]
    value = float(data["value"])

    backend_type = channel_info[ch][0]

    if backend_type == "software_pid":
        controller.set_setpoint(ch, value)

    elif backend_type == "manual":
        controller.set_manual(ch, value)

    else:
        return jsonify({"status":"error","msg":"unsupported backend"}),400

    LAST_VALUES[ch] = value
    LAST_STATES[ch] = "on"

    return jsonify({"status":"ok"})

@app.route("/api/turn_off", methods=["POST"])
def api_turn_off():

    data = request.json
    ch = data["channel"]

    controller.off(ch)

    LAST_VALUES[ch] = None
    LAST_STATES[ch] = "off"

    return jsonify({"status":"ok"})


# Plotting
sql = SQL(debug=False, options=["localhost", "axion_writer", 8082, "axion_db"])

plot_queue = queue.Queue(maxsize=5)

# filter only channels that should be displayed
display_channels = [ch for ch,info in channel_info.items() if info[3]]

db_reader = DBReader(sql, plot_queue, display_channels)
db_reader.start()

latest_plot_snapshot = {}


def update_latest_plot_data():

    global latest_plot_snapshot

    try:
        while True:
            snapshot = plot_queue.get_nowait()
            latest_plot_snapshot = snapshot
    except queue.Empty:
        pass


@app.route("/api/plotly_data")
def api_plotly_data():

    update_latest_plot_data()
    return jsonify(latest_plot_snapshot)


@app.route("/interactive")
def interactive():
    return render_template("interactive.html")


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8083)
