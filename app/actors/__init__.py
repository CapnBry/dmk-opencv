from flask import Blueprint

bp = Blueprint('actors', __name__)

from app.actors import routes