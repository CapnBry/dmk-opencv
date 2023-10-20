import sys
import app.main.main as main
import json
import cv2 as cv
from app.main import bp
from flask import request, make_response, render_template, abort, jsonify
from flask_cachecontrol import dont_cache, cache_for

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/showlog')
def showlog():
    log_as_list = main.grabber.getLog(request.args.get('cnt', type=int))
    return render_template('showlog.html', log=log_as_list)

@bp.route('/ss')
@dont_cache()
def getScreenshot():
    img = main.grabber.grab(color=True)
    _, img = cv.imencode('.jpg', img, [int(cv.IMWRITE_JPEG_QUALITY), 80])

    response = make_response(img.tobytes())
    response.content_type = 'image/jpg'
    #response.cache_control.
    return response

@bp.route('/click', methods=['POST'])
def click():
    x = request.values.get('x', type=int)
    y = request.values.get('y', type=int)

    if x is None or y is None:
        abort(400)

    main.grabber.click(x, y)

    return 'OK', 200

@bp.route('/drag', methods=['POST'])
def drag():
    dir = request.values.get('dir', type=int)
    amt = request.values.get('amt', type=int, default=500)
    main.pauseMainThread(True)
    main.windowDrag(main.grabber, dir, amt)
    main.pauseMainThread(False)

    return 'OK', 200

@bp.route('/log')
@cache_for(seconds=3)
def getLogJson():
    return jsonify(main.grabber.getLog(request.values.get('cnt', type=int)))

@bp.route('/shutdown')
def shutdown():
    main.shutdown()
    sys.exit(0)
    return 'OK', 200
