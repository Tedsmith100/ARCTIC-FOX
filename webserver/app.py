from flask import Flask, Response, render_template
import matplotlib.pyplot as plt
import io
import random

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/plot.png")
def plot_png():
    # Generate some demo data — replace with your hardware
    data = [random.random() for _ in range(50)]

    fig, ax = plt.subplots()
    ax.plot(data)
    ax.set_title("Live Hardware Data")

    # Save plot to PNG in memory
    png_image = io.BytesIO()
    fig.savefig(png_image, format="png")
    plt.close(fig)
    png_image.seek(0)

    return Response(png_image.getvalue(), mimetype="image/png")

if __name__ == "__main__":
    app.run(debug=True)

