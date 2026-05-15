import time
import queue
from threading import Thread, Event
from dataclasses import dataclass, field
from typing import Optional


# Side config 
@dataclass
class SideConfig:
    t_switches_off: int = 600
    t_heaters_on: int = 1200
    t_switch_on: int = 900
    t_between_sides: int = 2700

    heater_3puheat: float = 50.0
    heater_4puheat: float = 50.0

    switch_3swheat: float = 7.0
    switch_4swheat: float = 7.0


# Pre-cooling config
@dataclass
class PreCoolingConfig:
    enabled: bool = False
    value: float = 0.0


# Algorithm config 
@dataclass
class AlgorithmConfig:
    A: SideConfig = field(default_factory=SideConfig)
    B: SideConfig = field(default_factory=SideConfig)

    initial_precool: PreCoolingConfig = field(
        default_factory=lambda: PreCoolingConfig(
            enabled=False,
            value=50.0
        )
    )

    pre_cycle_cool: PreCoolingConfig = field(
        default_factory=lambda: PreCoolingConfig(
            enabled=False,
            value=7.0
        )
    )


# Cycle thread 
class Cycle(Thread):

    def __init__(
        self,
        controller,
        config: AlgorithmConfig,
        last_values: dict,
        last_states: dict
    ):
        super().__init__(daemon=True)

        self.controller = controller
        self.config = config
        self.last_values = last_values
        self.last_states = last_states

        self.stop_event = Event()
        self._cmd_queue = queue.Queue()
        self._running = Event()

        self.state = "Idle"
        self.step_start: Optional[float] = None
        self.step_total: int = 1
        self.current_side: Optional[str] = None


    def cmd_start(self):
        self._cmd_queue.put(("start", None))

    def cmd_stop(self):
        self._cmd_queue.put(("stop", None))

    def cmd_initial_precool(self, temp):
        self._cmd_queue.put(("initial_precool", temp))

    def cmd_pre_cycle_cool(self, voltage):
        self._cmd_queue.put(("pre_cycle_cool", voltage))

    def stop(self):
        self.stop_event.set()

    def _handle_commands(self):
        while not self._cmd_queue.empty():
            cmd, value = self._cmd_queue.get()

            if cmd == "start":
                self._running.set()

            elif cmd == "stop":
                self._running.clear()
                self.set_step("Idle", 0)
                self.current_side = None

            elif cmd == "initial_precool":
                self._running.clear()
                self.initial_precool(value)

            elif cmd == "pre_cycle_cool":
                self._running.clear()
                self.pre_cycle_cool(value)

    # Interruptible sleep 
    def sleep(self, seconds: int) -> bool:

        end = time.time() + seconds

        while time.time() < end:
            if self.stop_event.is_set():
                return False

            self._handle_commands()

            if not self._running.is_set():
                return False

            time.sleep(0.5)

        return True


    # Step handling 
    def set_step(self, state: str, duration: Optional[int]):
        self.state = state
        self.step_start = time.time()
        self.step_total = duration if duration is not None else 1


    # Send command with retries 
    def send_and_update(self, channel, cmd_func, value=None, retries=3):

        for attempt in range(1, retries + 1):
            try:
                if value is not None:
                    cmd_func(channel, value)

                    self.last_values[channel] = value
                    self.last_states[channel] = "on"

                else:
                    cmd_func(channel)

                    self.last_values[channel] = None
                    self.last_states[channel] = "off"

                return True

            except Exception as e:

                print(
                    f"[Cycle] Attempt {attempt} failed "
                    f"for {channel} -> {e}"
                )

                time.sleep(0.2)

        return False


    # Run one side 
    def run_side(self, side_name: str, c: SideConfig) -> bool:

        self.current_side = side_name

        # Switches off 
        self.set_step(f"{side_name}: switches off", c.t_switches_off)

        if not self.send_and_update(
            f"4switch{side_name} [K]",
            self.controller.off
        ):
            return False

        if not self.send_and_update(
            f"3switch{side_name} [K]",
            self.controller.off
        ):
            return False

        if not self.sleep(c.t_switches_off):
            return False


        # Heaters on 
        self.set_step(f"{side_name}: heaters on", c.t_heaters_on)

        if not self.send_and_update(
            f"4pump{side_name} [K]",
            self.controller.set_setpoint,
            c.heater_4puheat
        ):
            return False

        if not self.send_and_update(
            f"3pump{side_name} [K]",
            self.controller.set_setpoint,
            c.heater_3puheat
        ):
            return False

        if not self.sleep(c.t_heaters_on):
            return False


        # 4puheat off, 4swheat on 
        self.set_step(
            f"{side_name}: 4puheat off, 4swheat on",
            c.t_switch_on
        )

        if not self.send_and_update(
            f"4pump{side_name} [K]",
            self.controller.off
        ):
            return False

        if not self.send_and_update(
            f"4switch{side_name} [K]",
            self.controller.set_manual,
            c.switch_4swheat
        ):
            return False

        if not self.sleep(c.t_switch_on):
            return False


        # 3puheat off, 3swheat on 
        self.set_step(
            f"{side_name}: 3puheat off, 3swheat on",
            None
        )

        if not self.send_and_update(
            f"3pump{side_name} [K]",
            self.controller.off
        ):
            return False

        if not self.send_and_update(
            f"3switch{side_name} [K]",
            self.controller.set_manual,
            c.switch_3swheat
        ):
            return False

        return True


    # Main loop 
    def run(self):
        print("[Cycle] Algorithm thread started")

        while not self.stop_event.is_set():

            self._handle_commands()

            if not self._running.is_set():
                self._handle_commands()
                time.sleep(0.1)
                continue

            try:
                if not self.run_side("A", self.config.A):
                    self._running.clear()
                    continue

                self.set_step("Sleeping between sides", self.config.A.t_between_sides)
                if not self.sleep(self.config.A.t_between_sides):
                    self._running.clear()
                    continue

                if not self.run_side("B", self.config.B):
                    self._running.clear()
                    continue

                self.set_step("Sleeping between sides", self.config.B.t_between_sides)
                if not self.sleep(self.config.B.t_between_sides):
                    self._running.clear()
                    continue

            except Exception as e:
                print(f"[Cycle] Error: {e}")
                self._running.clear()

        print("[Cycle] Thread exiting")


    def initial_precool(self, temp):
        self.config.initial_precool.enabled = True
        self.config.initial_precool.value = temp

        # Switches off 
        if not self.send_and_update(
            f"4switchA [K]",
            self.controller.off
        ):
            return False

        if not self.send_and_update(
            f"3switchA [K]",
            self.controller.off
        ):
            return False

        if not self.send_and_update(
            f"4switchB [K]",
            self.controller.off
        ):
            return False

        if not self.send_and_update(
            f"3switchB [K]",
            self.controller.off
        ):
            return False

        # Heaters on
        if not self.send_and_update(
            f"4pumpA [K]",
            self.controller.set_setpoint,
            temp
        ):
            return False

        if not self.send_and_update(
            f"3pumpA [K]",
            self.controller.set_setpoint,
            temp
        ):
            return False

        if not self.send_and_update(
            f"4pumpB [K]",
            self.controller.set_setpoint,
            temp
        ):
            return False

        if not self.send_and_update(
            f"3pumpB [K]",
            self.controller.set_setpoint,
            temp
        ):
            return False

        return True

    def pre_cycle_cool(self, voltage):
        self.config.pre_cycle_cool.enabled = True
        self.config.pre_cycle_cool.value = voltage

        # Heaters off 
        if not self.send_and_update(
            f"4pumpA [K]",
            self.controller.off
        ):
            return False

        if not self.send_and_update(
            f"3pumpA [K]",
            self.controller.off
        ):
            return False

        if not self.send_and_update(
            f"4pumpB [K]",
            self.controller.off
        ):
            return False

        if not self.send_and_update(
            f"3pumpB [K]",
            self.controller.off
        ):
            return False

        # Switches on
        if not self.send_and_update(
            f"4switchA [K]",
            self.controller.set_manual,
            voltage
        ):
            return False

        if not self.send_and_update(
            f"3switchA [K]",
            self.controller.set_manual,
            voltage
        ):
            return False

        if not self.send_and_update(
            f"4switchB [K]",
            self.controller.set_manual,
            voltage
        ):
            return False

        if not self.send_and_update(
            f"3switchB [K]",
            self.controller.set_manual,
            voltage
        ):
            return False
        
        return True


    # Status API 
    def get_status(self):

        elapsed = 0.0

        if self.step_start is not None:
            elapsed = time.time() - self.step_start

        return {
            "running": self._running.is_set(),
            "state": self.state,
            "side": self.current_side,
            "elapsed": elapsed,
            "total": self.step_total
        }
