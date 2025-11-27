from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit
)
from PyQt5.QtCore import Qt


class SwitchWidget(QWidget):
    def __init__(self, controller, device_name, channel):
        super().__init__()
        self.controller = controller
        self.device_name = device_name
        self.channel = channel
        self.state = False

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel(f"SWITCH ({channel})")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        row = QHBoxLayout()
        self.voltage_input = QLineEdit()
        self.voltage_input.setPlaceholderText("Voltage (V)")
        self.voltage_input.setFixedWidth(90)

        self.set_button = QPushButton("Set Voltage")
        self.set_button.clicked.connect(self.set_voltage)

        row.addWidget(self.voltage_input)
        row.addWidget(self.set_button)
        layout.addLayout(row)

        self.off_button = QPushButton("Turn Off")
        self.off_button.clicked.connect(self.turn_off)
        layout.addWidget(self.off_button)

        self.update_off_button_color()

    def update_off_button_color(self):
        color = "lightgreen" if self.state else "lightcoral"
        self.off_button.setStyleSheet(f"background-color: {color};")

    def set_voltage(self):
        try:
            voltage = float(self.voltage_input.text())
            self.controller.set_switch_voltage(self.device_name, self.channel, voltage)
            self.state = True
            self.update_off_button_color()
            print(f"{self.device_name} {self.channel} updated to {voltage} V")
        except Exception as e:
            print(f"Error setting voltage on {self.device_name} {self.channel}: {e}")

    def turn_off(self):
        try:
            self.controller.turn_off_switch(self.device_name, self.channel)
            self.state = False
            self.update_off_button_color()
            print(f"{self.device_name} {self.channel} switched OFF")
        except Exception as e:
            print(f"Error turning off {self.device_name} {self.channel}: {e}")


class HeaterSetWidget(QWidget):
    def __init__(self, controller, device_name, channel):
        super().__init__()
        self.controller = controller
        self.device_name = device_name
        self.channel = channel
        self.state = False

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel(f"HEATER ({channel})")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        row = QHBoxLayout()
        self.temperature_input = QLineEdit()
        self.temperature_input.setPlaceholderText("Temperature (K)")
        self.temperature_input.setFixedWidth(90)

        self.set_button = QPushButton("Set Temp PID")
        self.set_button.clicked.connect(self.set_temp)

        row.addWidget(self.temperature_input)
        row.addWidget(self.set_button)
        layout.addLayout(row)

        self.off_button = QPushButton("Turn Off")
        self.off_button.clicked.connect(self.turn_off)
        layout.addWidget(self.off_button)

        self.update_off_button_color()

    def update_off_button_color(self):
        color = "lightgreen" if self.state else "lightcoral"
        self.off_button.setStyleSheet(f"background-color: {color};")

    def set_temp(self):
        try:
            temperature = float(self.temperature_input.text())
            self.controller.set_heater_temperature(self.device_name, self.channel, temperature)
            self.state = True
            self.update_off_button_color()
            print(f"{self.device_name} {self.channel} updated to {temperature} K")
        except Exception as e:
            print(f"Error setting temperature on {self.device_name} {self.channel}: {e}")

    def turn_off(self):
        try:
            self.controller.turn_off_heater(self.device_name, self.channel)
            self.state = False
            self.update_off_button_color()
            print(f"{self.device_name} {self.channel} switched OFF")
        except Exception as e:
            print(f"Error turning off {self.device_name} {self.channel}: {e}")


class HeaterButton(QPushButton):
    def __init__(self, controller, device_name, channel, initial_state=False):
        super().__init__()
        self.controller = controller
        self.device_name = device_name
        self.channel = channel
        self.state = initial_state

        self.setCheckable(True)
        self.setChecked(initial_state)
        self.setText(f"HEATER \n ({channel})")
        self.update_color()
        self.clicked.connect(self.toggle_heater)

    def update_color(self):
        self.setStyleSheet(
            "background-color: lightgreen;" if self.state else "background-color: lightcoral;"
        )

    def toggle_heater(self):
        try:
            self.state = not self.state
            self.controller.toggle_heater(self.device_name, self.channel, self.state)
            self.update_color()
        except Exception as e:
            print(f"Error toggling heater {self.device_name} {self.channel}: {e}")


class StillHeater(QWidget):
    def __init__(self, controller, device_name, channel):
        super().__init__()
        self.controller = controller
        self.device_name = device_name
        self.channel = channel
        self.state = False

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel(f"STILL HEATER ({channel})")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        row = QHBoxLayout()
        self.percent_input = QLineEdit()
        self.percent_input.setPlaceholderText("Percentage of max voltage")
        self.percent_input.setFixedWidth(90)

        self.set_button = QPushButton("Set Value")
        self.set_button.clicked.connect(self.set_percentage)

        row.addWidget(self.percent_input)
        row.addWidget(self.set_button)
        layout.addLayout(row)

        self.off_button = QPushButton("Turn Off")
        self.off_button.clicked.connect(self.turn_off)
        layout.addWidget(self.off_button)

        self.update_off_button_color()

    def update_off_button_color(self):
        color = "lightgreen" if self.state else "lightcoral"
        self.off_button.setStyleSheet(f"background-color: {color};")

    def set_percentage(self):
        try:
            percentage = float(self.percent_input.text())
            self.controller.set_still_percentage(self.device_name, self.channel, percentage)
            self.state = True
            self.update_off_button_color()
            print(f"{self.device_name} {self.channel} updated to {percentage} %")
        except Exception as e:
            print(f"Error setting voltage on {self.device_name} {self.channel}: {e}")

    def turn_off(self):
        try:
            self.controller.turn_off_still(self.device_name, self.channel)
            self.state = False
            self.update_off_button_color()
            print(f"{self.device_name} {self.channel} switched OFF")
        except Exception as e:
            print(f"Error turning off {self.device_name} {self.channel}: {e}")


class ControlPanel(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Heat Switch & Heater Control")
        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        for dev_name in controller.devices:
            dev = controller.devices[dev_name]
            device_layout = QVBoxLayout()
            label = QLabel(dev_name)
            label.setAlignment(Qt.AlignCenter)
            device_layout.addWidget(label)

            channel_map = self.get_channels_for_device(dev_name)

            for channel, ch_type in channel_map.items():
                row = QHBoxLayout()
                if ch_type == "still_heater":
                    row.addWidget(StillHeater(controller, dev_name, channel))
                elif ch_type == "switch":
                    row.addWidget(SwitchWidget(controller, dev_name, channel))
                elif ch_type == "heater":
                    row.addWidget(HeaterSetWidget(controller, dev_name, channel))
                device_layout.addLayout(row)

            self.main_layout.addLayout(device_layout)

    @staticmethod
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
        return {}
