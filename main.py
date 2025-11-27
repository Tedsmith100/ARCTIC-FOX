import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from devices.device import connect_devices
from ui.elements import ControlPanel
from core.controller import DeviceController
from core.plotter import TemperaturePlotter


def main():
    # -------------------------------
    # Qt must always run in main thread
    # -------------------------------
    app = QApplication(sys.argv)

    # -------------------------------
    # Connect serial devices
    # -------------------------------
    devices = connect_devices()
    if not devices:
        print("No devices found. UI will still open, but controls will do nothing.")
    else:
        print("Connected devices:", list(devices.keys()))

    # -------------------------------
    # Create controller
    # -------------------------------
    controller = DeviceController(devices)

    # -------------------------------
    # Start plotter thread
    # -------------------------------
    plotter = TemperaturePlotter(window_seconds=300, interval=2000)
    plotter.start()

    # -------------------------------
    # Create control panel UI
    # -------------------------------
    panel = ControlPanel(controller)
    panel.show()

    # -------------------------------
    # Ensure plotter stops when Qt closes
    # -------------------------------
    def on_exit():
        print("Stopping plotter thread...")
        plotter.stop()

    app.aboutToQuit.connect(on_exit)

    # -------------------------------
    # Run event loop
    # -------------------------------
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
