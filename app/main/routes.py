import sys
import app.main.main as main
import json
import cv2 as cv
from app.main import bp
from flask import request, make_response, render_template, abort, jsonify

def handleIndexPost():
    pause = request.values.get('pause')
    if not pause:
        return
    if pause == '0':
        main.pauseMainThread.paused = False
    elif pause == '1':
        main.pauseMainThread.paused = True

@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        handleIndexPost()

    return render_template('index.html', paused=main.pauseMainThread.paused)

@bp.route('/showlog')
def showlog():
    log_as_list = main.grabber.getLog(request.args.get('cnt', type=int))
    return render_template('showlog.html', log=log_as_list)

@bp.route('/ss')
def getScreenshot():
    img = main.grabber.grab(color=True)
    _, img = cv.imencode('.webp', img, [int(cv.IMWRITE_WEBP_QUALITY), 10])

    response = make_response(img.tobytes())
    response.content_type = 'image/webp'
    response.cache_control.no_cache = True

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

@bp.route('/scroll', methods=['POST'])
def scroll():
    amt = request.values.get('amt', type=int)

    if amt is None:
        abort(400)

    main.pauseMainThread(True)
    main.grabber.moveTo(main.grabber.width // 2, main.grabber.height // 2)
    main.grabber.scroll(amt)
    main.pauseMainThread(False)

    return 'OK', 200

@bp.route('/log')
def getLogJson():
    resp = jsonify(main.grabber.getLog(request.values.get('cnt', type=int)))
    resp.cache_control.no_cache = None
    resp.cache_control.public = True
    resp.cache_control.max_age = 3
    return resp

@bp.route('/shutdown')
def shutdown():
    main.shutdown()
    sys.exit(0)
    return 'OK', 200
