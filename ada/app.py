from flask import Flask
from .util.conf import config
from flask_uwsgi_websocket import GeventWebSocket

app = Flask(__name__)
websocket = GeventWebSocket(app)

import ada.ui
