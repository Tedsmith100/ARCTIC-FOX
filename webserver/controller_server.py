import socket
import time


class DeviceControllerServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    # ---------------- Switch Functions ----------------
    def set_switch_voltage(self, device_name, channel, voltage):
        cmd_str = f"set_switch_voltage {device_name} {channel} {voltage}"
        self.send_cmd(cmd_str)

    def turn_off_switch(self, device_name, channel):
        cmd_str = f"turn_off_switch {device_name} {channel}"
        self.send_cmd(cmd_str)

    # ---------------- Heater Functions ----------------
    def set_heater_temperature(self, device_name, channel, temperature):
        cmd_str = f"set_heater_temperature {device_name} {channel} {temperature}"
        self.send_cmd(cmd_str)

    def turn_off_heater(self, device_name, channel):
        cmd_str = f"turn_off_heater {device_name} {channel}"
        self.send_cmd(cmd_str)

    def toggle_heater(self, device_name, channel, state: bool):
        cmd_str = f"toggle_heater {device_name} {channel} {state}"
        self.send_cmd(cmd_str)

    # ---------------- Still Heater Functions ----------------
    def set_still_percentage(self, device_name, channel, percent):
        cmd_str = f"set_still_percentage {device_name} {channel} {percent}"
        self.send_cmd(cmd_str)

    def turn_off_still(self, device_name, channel):
        cmd_str = f"turn_off_still {device_name} {channel}"
        self.send_cmd(cmd_str)

    # --------------- Remote Functions -----------------
    def send_cmd(self, cmd: str):
        '''
        Send an ASCII command and wait for an ASCII response.
        Returns the response string.
        '''
        with socket.socket() as s:
            # connect socket
            s.connect((self.host, self.port))

            # Send command
            s.sendall((cmd + "\n").encode("ascii"))

            # Wait for response
            response = s.recv(1024).decode("ascii").strip()
            
            if response is not "0":
                raise ValueError(f"Command failed to send '{cmd}'")

        return response
