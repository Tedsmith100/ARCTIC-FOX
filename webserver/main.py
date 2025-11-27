from flask import Flask, Response, render_template_string
import matplotlib.pyplot as plt
import io
import random
import time

app = Flask(__name__)

@app.route("/")
def index():
    return render_template_string("""
    <html>
      <head>
        <meta http-equiv="refresh" content="1"> <!-- auto refresh every 1 sec -->
      </head>
      <body>
        <h1>Live Hardware Plot (Python only)</h1>
        <img src="/plot.png" />
      </body>
    </html>
    """)

@app.route("/plot.png")
def plot_png():
    fig, ax = plt.subplots()

    # Replace with your real hardware read:
    data = [random.random() for _ in range(100)]

    ax.plot(data)
    ax.set_title("Hardware Data")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    return Response(buf.getvalue(), mimetype="image/png")

if __name__ == "__main__":
    app.run(debug=True)

