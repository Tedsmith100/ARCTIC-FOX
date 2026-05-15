import threading
import time
from simple_pid import PID

class PIDWorker(threading.Thread):
    def __init__(self, name, hwio, read_temp_fn, write_output_fn,
                 kp, ki, kd, min, max, sample_time=1.0):
        super().__init__(daemon=True)

        self.name = name
        self.hwio = hwio
        self.read_temp_fn = read_temp_fn
        self.write_output_fn = write_output_fn

        self.pid = PID(kp, ki, kd, output_limits=(min, max), proportional_on_measurement = True)
        self.max = max
        #self.pid.sample_time = sample_time

        self._enabled = threading.Event()
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def set_setpoint(self, sp):
        with self._lock:
            self.pid.setpoint = sp

    def enable(self):
        self._enabled.set()
        print(f"[PIDWorker:{self.name}] enable")

    def disable(self):
        self._enabled.clear()
        self.write_output_fn(0.0)
        print(f"[PIDWorker:{self.name}] disable")

    def run(self):
        while not self._stop_event.is_set():
            if self._enabled.is_set():
                try:
                    temp = self.read_temp_fn()
                    #print(f"[PIDWorker:{self.name}] Read: {temp}K")
                    if temp is not None:
                        with self._lock:
                            if self.pid.setpoint - temp < 0.01*self.pid.setpoint: 
                                #self.pid.reset()
                                out = self.pid(temp)

                            else:
                                out = self.max
                        #print(f"[PIDWorker:{self.name}] PID: {out}V")

                        self.write_output_fn(out)
                        #print("[PIDWorker:{self.name}] here")

                except Exception as e:
                    print(f"[PIDWorker:{self.name}] ERROR: {e}")

            time.sleep(3)

    def shutdown(self):
        self._stop_event.set()
        self.join()
        print(f"[PIDWorker:{self.name}] shutdown")
