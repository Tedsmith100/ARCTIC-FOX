import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit
)
from PyQt5.QtCore import Qt
from cooldown_loop_dilution_v2 import switch_on, switch_off, heater_on, heater_off
from CTC100 import CTC100Device
from lakeshore224device import LakeShore224Device
from lakeshore372device import LakeShore372Device
import serial


def connect_devices():  # Connects to devices
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
        "LakeshoreModel372": model372
    } # Add extra devices here if the setup changes

    return {k: v for k, v in connected.items() if v is not None}


class SwitchControlWidget(QWidget):  # Creates inputs for heat switches - enter a voltage and confirm
    def __init__(self, device, channel):
        super().__init__()
        self.device = device
        self.channel = channel
        self.state = False  # OFF by default

        layout = QVBoxLayout()
        self.setLayout(layout)



        # Label for channel
        label = QLabel(f"{channel} SWITCH")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # Voltage input row
        row = QHBoxLayout()

        self.voltage_input = QLineEdit()
        self.voltage_input.setPlaceholderText("Voltage (V)")
        self.voltage_input.setFixedWidth(90)

        self.set_button = QPushButton("Set Voltage")
        self.set_button.clicked.connect(self.set_voltage)

        row.addWidget(self.voltage_input)
        row.addWidget(self.set_button)

        layout.addLayout(row)

        # Off button
        self.off_button = QPushButton("Turn Off")
        self.off_button.clicked.connect(self.turn_off)
        layout.addWidget(self.off_button)

        # Initialize button color
        self.update_off_button_color()

    def update_off_button_color(self):
        # Green if ON, red if OFF
        color = "lightgreen" if self.state else "lightcoral"
        self.off_button.setStyleSheet(f"background-color: {color};")

    def set_voltage(self):
        try:
            voltage = float(self.voltage_input.text())
            switch_on(self.device, self.channel, voltage)

            # Mark as ON after setting voltage
            self.state = True
            self.update_off_button_color()

            print(f"{self.device.name} {self.channel} updated to {voltage} V")

        except ValueError:
            print("Invalid voltage entered.")
        except Exception as e:
            print(f"Error setting voltage on {self.device.name} {self.channel}: {e}")

    def turn_off(self):
        try:
            switch_off(self.device, self.channel)
            self.state = False
            self.update_off_button_color()
            print(f"{self.device.name} {self.channel} switched OFF")
        except Exception as e:
            print(f"Error turning off {self.device.name} {self.channel}: {e}")



class HeaterButton(QPushButton):  # Buttons for heaters - these are PID controlled, currently function as on/off only
    def __init__(self, device, channel, initial_state=False):
        super().__init__()
        self.device = device
        self.channel = channel
        self.state = initial_state

        self.setCheckable(True)
        self.setChecked(initial_state)
        self.setText(f"{channel}\nHEATER")
        self.update_color()

        self.clicked.connect(self.toggle_heater)

    def update_color(self):
        self.setStyleSheet(
            "background-color: lightgreen;" if self.state else "background-color: lightcoral;"
        )

    def toggle_heater(self):
        try:
            if not self.state:
                heater_on(self.device, self.channel)
                self.state = True
            else:
                heater_off(self.device, self.channel)
                self.state = False
            self.update_color()

        except Exception as e:
            print(f"Error toggling heater {self.device.name} {self.channel}: {e}")


class ControlPanel(QWidget):  # Creates the surrounding control panel
    def __init__(self, devices):
        super().__init__()
        self.setWindowTitle("Heat Switch & Heater Control")
        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        for dev_name, dev in devices.items(): # Columns of devices, with controls of each channel under label

            device_layout = QVBoxLayout()
            label = QLabel(dev_name)
            label.setAlignment(Qt.AlignCenter)
            device_layout.addWidget(label)

            channel_map = self.get_channels_for_device(dev_name)

            for channel, ch_type in channel_map.items():
                row = QHBoxLayout()

                if ch_type == "switch":
                    row.addWidget(SwitchControlWidget(dev, channel))

                elif ch_type == "heater":
                    row.addWidget(HeaterButton(dev, channel))

                device_layout.addLayout(row)

            self.main_layout.addLayout(device_layout)

    @staticmethod
    def get_channels_for_device(dev_name):
        """
        Returns dict: {channel: "switch" | "heater"}
        """

        if dev_name in ("CTC100A", "CTC100B"):
            return {
                "4puheat": "heater",
                "3puheat": "heater",
                "4swheat": "switch",
                "3swheat": "switch",
                "AIO3": "switch",
                "AIO4": "switch",
            }

        return {}


if __name__ == "__main__":
    devices = connect_devices()
    app = QApplication(sys.argv)
    panel = ControlPanel(devices)
    panel.show()
    sys.exit(app.exec_())
