import os
from app.actors import bp
from flask import send_file, jsonify, render_template, request, abort

def getActorDir(a: str) -> str:
    return os.path.join('actors/', a)

@bp.route('/')
def index():
    return render_template(f'{request.url_rule.rule}/index.html')

@bp.route('/list')
def actorList():
    retVal = []
    dir = 'actors'
    for a in os.listdir(dir):
        if a == '__pycache__':
            continue
        if os.path.isdir(os.path.join(dir, a)):
            retVal.append(
                {
                    'id': a,
                    'name': a,
                    'hasAbort': os.path.exists(os.path.join(dir, a, 'abort.txt')),
                    'hasTarget': os.path.exists(os.path.join(dir, a, 'target.png')),
                    'portrait_url': f'{a}/portrait',
                }
            )
    return jsonify(retVal)

@bp.route('/<actor>/portrait')
def actorPortrait(actor):
    dir = getActorDir(actor)
    for k in ['folder.png', 'actor.png']:
        fname = os.path.join(dir, k)
        if os.path.exists(fname):
            return send_file(fname, mimetype='image/png')
    return 'Not found', 404

def actorFileOp(actor_name, fname):
    if actor_name is None:
        abort(400)

    enable = request.values.get('enable', type=int)
    full_fname = os.path.join(getActorDir(actor_name), fname)
    if enable is None:
        return '1' if os.path.exists(full_fname) else '0', 200

    if enable == 1:
        with (open(full_fname, 'w')) as f:
            action = request.values.get('action', type=str)
            if action is not None:
                f.write(action)
    else:
        os.remove(full_fname)

    return 'OK', 200

@bp.route('/<actor>/skip')
def actorSkip(actor):
    return actorFileOp(actor, 'skip.txt')

@bp.route('/<actor>/abort')
def actorAbort(actor):
    return actorFileOp(actor, 'abort.txt')

@bp.route('/<actor>/wish')
def actorWish(actor):
    return actorFileOp(actor, 'wish.txt')