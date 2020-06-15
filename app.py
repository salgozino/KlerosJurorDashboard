import dash
from flask import Flask

server = Flask(__name__)
app = dash.Dash(__name__, 
                server=server,
                suppress_callback_exceptions=True)
app.title='Kleros Jurors Dashboard'
