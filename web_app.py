import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR + '/envs/', "params.env"))
load_dotenv(os.path.join(BASE_DIR + '/envs/', "keys.env"))

from flask import Flask, jsonify, render_template
from database import get_sizes, init_database


app = Flask(__name__)

REPEAT_COUNTER = int(os.getenv("REPEAT_COUNTER", 4))

@app.route("/")
def index():
    return render_template(
        "sizes.html",
        repeat_counter=REPEAT_COUNTER
    )



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