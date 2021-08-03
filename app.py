from flask import Flask
from datetime import datetime
import re
from debugger import initialize_flask_server_debugger_if_needed

initialize_flask_server_debugger_if_needed()

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, Flask!"
