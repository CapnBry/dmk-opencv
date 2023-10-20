import os
import re
import shutil
from app.actors import bp
from flask import send_file, jsonify, render_template, request, abort

def getActorDir(a: str) -> str:
    return os.path.join('actors/', a)

@bp.route('/')
def index():
    actors = []
    counts = {}
    dir = 'actors'
    for a in os.listdir(dir):
        if a == '__pycache__':
            continue
        if os.path.isdir(os.path.join(dir, a)):
            actor =  {
                    'id': a,
                    'name': a,
                    'hasTarget': os.path.exists(os.path.join(dir, a, 'target.png')),
                    'hasAbort': os.path.exists(os.path.join(dir, a, 'abort.txt')),
                    'hasForce': os.path.exists(os.path.join(dir, a, 'force.txt')),
                    'hasSkip': os.path.exists(os.path.join(dir, a, 'skip.txt')),
                    'hasWish': os.path.exists(os.path.join(dir, a, 'wish.txt')),
                }
            # Running total for summary
            for item in ['Target', 'Abort', 'Force', 'Skip', 'Wish']:
                item_full = f'has{item}'
                counts[item] = counts.get(item, 0) + (1 if actor[item_full] else 0)

            actors.append(actor)

    actors.sort(key=lambda a: a['name'])
    return render_template(f'{request.blueprint}/index.html',
        actors=actors, counts=counts)

# @bp.route('/list')
# def actorList():
#     retVal = []
#     dir = 'actors'
#     for a in os.listdir(dir):
#         if a == '__pycache__':
#             continue
#         if os.path.isdir(os.path.join(dir, a)):
#             retVal.append(
#                 {
#                     'id': a,
#                     'name': a,
#                     'hasAbort': os.path.exists(os.path.join(dir, a, 'abort.txt')),
#                     'hasTarget': os.path.exists(os.path.join(dir, a, 'target.png')),
#                     'portrait_url': f'{a}/portrait',
#                 }
#             )
#     return jsonify(retVal)

@bp.route('/<actor>/portrait')
def actorPortrait(actor):
    dir = getActorDir(actor)
    for k in ['folder.png', 'actor.png']:
        fname = os.path.join(dir, k)
        if os.path.exists(fname):
            resp = send_file(fname, mimetype='image/png')
            resp.cache_control.no_cache = None
            resp.cache_control.public = True
            resp.cache_control.max_age = (60 * 60 * 24 * 7)
            return resp

    return 'Not found', 404

@bp.route('/<actor>/taskimg/<fname>')
def actorTaskImg(actor, fname):
    dir = getActorDir(actor)
    full_fname = os.path.join(dir, (fname or '###'))
    if os.path.exists(full_fname):
        resp = send_file(full_fname, mimetype='image/png')
        # The active item can chage so do not cache it
        resp.cache_control.public = True
        if fname != 'target.png':
            resp.cache_control.no_cache = None
            resp.cache_control.max_age = 3600
        else:
            resp.cache_control.no_cache = None
            resp.cache_control.max_age = 30
        return resp

    return 'Not found', 404

def actorHandleTasksPost(actor):
    dir = getActorDir(actor)
    # Look for action file create/delete
    for item in ['wish', 'abort', 'force']:
        ival = request.values.get(item)
        if not ival:
            continue
        fname = os.path.join(dir, f'{item}.txt')
        if ival == "1":
            with open(fname, 'w') as f:
                f.write(repr(request))
                pass
        elif ival == "0":
            os.remove(fname)

    # Change task target
    settask = request.values.get('settask')
    if settask and settask != 'target.png':
        target = os.path.join(dir, 'target.png')
        os.remove(target)
        shutil.copy2(os.path.join(dir, settask), target)

@bp.route('/<actor>/tasks', methods=['GET', 'POST'])
def actorTasks(actor):
    if request.method == 'POST':
        actorHandleTasksPost(actor)

    dir = getActorDir(actor)
    tasks = []
    hasWish = False
    hasAbort = False
    hasForce = False
    notes = None
    srch = re.compile('^target[a-z\-]*.png$')
    for entry in os.listdir(dir):
        entryfull = os.path.join(dir, entry)
        if not os.path.isfile(entryfull):
            continue
        if entry == 'wish.txt':
            hasWish = True
            continue
        if entry == 'abort.txt':
            hasAbort = True
            continue
        if entry == 'force.txt':
            hasForce = True
            continue
        if entry == 'notes.txt':
            with open(entryfull, 'r') as f:
                notes = f.read().splitlines()
            continue
        if not srch.match(entry):
            continue
        tasks.append(entry)
    tasks.sort(reverse=True)
    return render_template(f'{request.blueprint}/tasks.html',
        actor=actor, tasks=tasks,
        hasWish=hasWish, hasAbort=hasAbort, hasForce=hasForce, notes=notes)

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
