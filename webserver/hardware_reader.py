# hardware_reader.py
import time
import serial
import numpy as np
import serial.tools.list_ports

from CTC100 import CTC100Device
from lakeshore224device import LakeShore224Device
from lakeshore372device import LakeShore372Device

class HardwareTemperatureReader:
    """
    Headless (no GUI) replacement for your TemperaturePlotter.
    Only reads temperatures and returns a unified reading dict.
    """

    def __init__(self, devices):
        self.devices = devices

    def connect_devices(self):
        ports = serial.tools.list_ports.comports()
        ctc100A = None
        ctc100B = None
        ls224 = None
        ls372 = None

        for p in ports:
            if 'FT230X' in p.description:
                if 'DK0CDLQP' in p.serial_number:
                    ctc100B = CTC100Device(address=p.device, name='CTC100B')
                elif 'DK0CDKFB' in p.serial_number:
                    ctc100A = CTC100Device(address=p.device, name='CTC100A')

            elif '224' in p.description:
                ls224 = LakeShore224Device(port=p.device, name='Lakeshore224')

            elif '372' in p.description:
                ls372 = LakeShore372Device(port=p.device, name='Lakeshore372')

        connected = {
            "CTC100A": ctc100A,
            "CTC100B": ctc100B,
            "Lakeshore224": ls224,
            "Lakeshore372": ls372,
        }
        return {k: v for k, v in connected.items() if v is not None}

    def read_temperatures(self):
        d = self.devices
        readings = {}

        # -------------------- CTC100A --------------------
        if "CTC100A" in d:
            dev = d["CTC100A"]
            readings["CTC100A"] = {
                "4switchA": dev.get_temperature("4switch"),
                "4pumpA":   dev.get_temperature("4pump"),
                "3switchA": dev.get_temperature("3switch"),
                "3pumpA":   dev.get_temperature("3pump"),
            }

        # -------------------- CTC100B --------------------
        if "CTC100B" in d:
            dev = d["CTC100B"]
            readings["CTC100B"] = {
                "4switchB": dev.get_temperature("4switch"),
                "4pumpB":   dev.get_temperature("4pump"),
                "3switchB": dev.get_temperature("3switch"),
                "3pumpB":   dev.get_temperature("3pump"),
            }

        # -------------------- LakeShore 224 --------------------
        if "Lakeshore224" in d:
            dev = d["Lakeshore224"]
            readings["Lakeshore224"] = {
                "4HePotA": dev.get_temperature("C1"),
                "3HePotA": dev.get_temperature("B"),
                "4HePotB": dev.get_temperature("C2"),
                "3HePotB": dev.get_temperature("D1"),
                "Condenser": dev.get_temperature("A"),
                "50K Plate": dev.get_temperature("D2"),
                "4K Plate": dev.get_temperature("D3"),
            }

        # -------------------- LakeShore 372 --------------------
        if "Lakeshore372" in d:
            dev = d["Lakeshore372"]
            readings["Lakeshore372"] = {
                "MC":    dev.get_temperature("1"),
                "Still": dev.get_temperature("A"),
            }

        return readings

