import threading
import time
import copy

class DBReader(threading.Thread):

    def __init__(self, sql, plot_queue, channels, interval=2.0):
        super().__init__(daemon=True)

        self.sql = sql
        self.channels = channels          # exact DB names (with [K])
        self.plot_queue = plot_queue
        self.interval = interval

        # SCID lookup
        # Ensure channels is a list
        if isinstance(channels, str):
            channels = [channels]

        self.scids = {ch: sql.getSCID(ch) for ch in channels}

        # last timestamp
        last = sql.lastUpdate()
        self.last_timestamp = int(last.timestamp()) if last else 0

        # plotting state
        self.state = {
            "times": [],
            **{ch: [] for ch in channels}
        }

        # last values for forward fill
        self.last_values = {ch: None for ch in channels}

    def run(self):

        print("[DBReader] Starting DB poll thread.")

        while True:

            try:
                timestamps = self.sql.getSCTimes(self.last_timestamp)

                if not timestamps:
                    time.sleep(self.interval)
                    continue

                ts = max(timestamps)

                rows = self.sql.getSCValues(list(self.scids.values()), ts)

                if not rows:
                    time.sleep(self.interval)
                    continue

                record = rows[0]
                t = record["time"]

                # read DB values
                for i, ch in enumerate(self.channels):

                    raw = record.get(f"value-{i+1}")

                    try:
                        val = float(raw)
                    except:
                        continue

                    if val < -9:
                        continue

                    self.last_values[ch] = val

                # append aligned values
                self.state["times"].append(t)

                for ch in self.channels:

                    val = self.last_values[ch]

                    if val is not None:
                        self.state[ch].append(val)
                    else:
                        if self.state[ch]:
                            self.state[ch].append(self.state[ch][-1])

                # emit snapshot
                self.plot_queue.put(copy.deepcopy(self.state))

                self.last_timestamp = t

            except Exception as e:

                self.sql.db.rollback()
                print("[DBReader] ERROR:", e)

            time.sleep(self.interval)
