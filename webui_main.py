from flask import Flask, render_template
from dmkgrabber import DmkGrabber

app = Flask(__name__, template_folder='html')

@app.route('/')
def index():
    return render_template('index.html')