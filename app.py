from flask import Flask
from datetime import datetime
import re
from debugger import initialize_flask_server_debugger_if_needed

initialize_flask_server_debugger_if_needed()


import sys
sys.path.insert(1, '/app/ddd')

from ddd.data import Data
from ddd.phab import Conduit

from ddd.boardmetrics import ObjectMetrics
from ddd.data import PropertyMatcher



app = Flask(__name__)

async def start():
    return "Hello!"

@app.route("/")
async def home():
    return await start()