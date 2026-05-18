import sys
import os

from database_functions import read_config_file
from webserver.sql import SQL

import datetime
import matplotlib
matplotlib.use("TkAgg")  # ensures the plot opens in a separate window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def read_db(config_file : str):

    # Add the project root to sys.path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    conf_args = read_config_file(config_file)

    options    = conf_args["options"]
    START_TIME = conf_args["start_time"]
    END_TIME   = conf_args["end_time"]
    channels   = conf_args["channels"]
    log_plot   = conf_args["log_plot"]

    sql = SQL(debug=False, options=options)

    # Get the values from db
    data = sql.getSCValuesBetween(
        names=channels,
        start_time=datetime.datetime.fromisoformat(START_TIME),
        end_time=datetime.datetime.fromisoformat(END_TIME)
    )

    # Print the number of data points fetched for each channel
    for ch in channels:
        print(ch, "Times fetched:", len(data[ch]["time"]))

    # Plot the data
    plt.figure(figsize = (14,6))
    for channel in channels:
        plt.plot(data[channel]["time"], data[channel]["value"], label = channel)

    if log_plot:
        plt.yscale("log")

    plt.grid()
    plt.xlabel("Time")
    plt.ylabel("Temperature (K)")
    plt.legend(loc = "upper center", bbox_to_anchor=(1, 1))
    plt.show()

    # Save the data to a CSV file
    dfs = []
    for channel in channels:
        df_ch = pd.DataFrame({
            "time": data[channel]["time"],
            channel: data[channel]["value"]
        })
        dfs.append(df_ch)

    df = dfs[0]
    for df_ch in dfs[1:]:
        df = pd.merge(df, df_ch, on="time", how="outer")

    df = df.sort_values("time")

    df.to_csv(f"{START_TIME}_cooldown.csv", index=False)

    return

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage:")
        print("python database_reader.py <config_file>")
        sys.exit(1)

    config_file = sys.argv[1]

    read_db(config_file)
