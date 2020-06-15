import dash

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title='Kleros Jurors Dashboard'
server = app.server