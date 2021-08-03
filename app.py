from flask import Flask
from datetime import datetime
import re
from debugger import initialize_flask_server_debugger_if_needed

initialize_flask_server_debugger_if_needed()

app = Flask(__name__)

async def start():
    return "Hello!"

@app.route("/")
async def home():
    return await start()