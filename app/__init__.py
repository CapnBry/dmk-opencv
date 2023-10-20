from flask import Flask
import mimetypes

app = Flask('dmk')

from app.main import bp as bp_main
app.register_blueprint(bp_main)

from app.actors import bp as bp_actors
app.register_blueprint(bp_actors, url_prefix='/actors')

mimetypes.add_type('text/javascript', '.js')
mimetypes.add_type('text/css', '.css')
