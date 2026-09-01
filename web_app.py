from flask import Flask, jsonify, render_template

from database import get_sizes, init_database


app = Flask(__name__)


@app.route("/")
def index():
    return render_template("sizes.html")


@app.route("/api/sizes")
def api_sizes():
    return jsonify(get_sizes())


if __name__ == "__main__":
    init_database()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )