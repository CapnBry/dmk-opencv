import os
import json
import re
import shutil
import app.main.main as main
from app.actors import bp
from flask import send_file, jsonify, render_template, request, abort, redirect, url_for

def getActorDir(actor_id: str) -> str:
    return os.path.join('actors/', actor_id)

def getTargetCacheKey(base_fname, full_fname) -> str:
    # use mtime to differentiate updated target files with the same nane
    mtime = int(os.path.getmtime(full_fname))
    return base_fname + '.' + str(mtime)

def fillActorClass(actor_id):
    dir = getActorDir(actor_id)
    target_fullfname = os.path.join(dir, 'target.png')
    actor =  {
            'id': actor_id,
            'name': actor_id,
            'hasTarget': os.path.exists(target_fullfname),
            'hasAbort': os.path.exists(os.path.join(dir, 'abort.txt')),
            'hasClip': os.path.exists(os.path.join(dir, 'clip.txt')),
            'hasEq': os.path.exists(os.path.join(dir, 'eq.txt')),
            'hasForce': os.path.exists(os.path.join(dir, 'force.txt')),
            'hasKq': os.path.exists(os.path.join(dir, 'kq.txt')),
            'hasSkip': os.path.exists(os.path.join(dir, 'skip.txt')),
            'hasWish': os.path.exists(os.path.join(dir, 'wish.txt')),
        }
    if actor['hasTarget']:
        actor['target'] = getTargetCacheKey('target.png', target_fullfname)

    return actor

@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        return actorHandleTasksPost(request.values.get('actor', type=str))

    actors = []
    counts = {}
    dir = 'actors'
    for a in os.listdir(dir):
        if a == '__pycache__':
            continue
        if os.path.isdir(os.path.join(dir, a)):
            actor = fillActorClass(a)

            # Running total for summary
            for item in ['Target', 'Abort', 'Clip', 'Eq', 'Force', 'Kq', 'Skip', 'Wish']:
                item_full = f'has{item}'
                counts[item] = counts.get(item, 0) + (1 if actor[item_full] else 0)

            actors.append(actor)

    actors.sort(key=lambda a: a['name'].lower())
    return render_template(f'{request.blueprint}/index.html',
        actors=actors, counts=counts, paused=main.pauseMainThread.paused)

@bp.route('/<actor_id>/portrait')
def actorPortrait(actor_id):
    dir = getActorDir(actor_id)
    for k in ['folder.png', 'actor.png']:
        fname = os.path.join(dir, k)
        if os.path.exists(fname):
            resp = send_file(fname, mimetype='image/png')
            resp.cache_control.no_cache = None
            resp.cache_control.public = True
            resp.cache_control.max_age = (60 * 60 * 24 * 7)
            return resp

    return redirect(url_for('static', filename='actor_unknown.png'))

@bp.route('/<actor_id>/taskimg/<fname>')
def actorTaskImg(actor_id, fname):
    dir = getActorDir(actor_id)

    # Filenames may have a numeric suffix to allow caching (target.png.1698842042)
    fname = fname[:fname.find('.png')+4]

    full_fname = os.path.join(dir, fname)
    if os.path.exists(full_fname):
        resp = send_file(full_fname, mimetype='image/png')
        resp.cache_control.no_cache = None
        resp.cache_control.public = True
        resp.cache_control.max_age = (60 * 60 * 24 * 7)
        return resp

    return 'Not found', 404

def actorHandleTasksPost(actor_id):
    dir = getActorDir(actor_id)
    # Look for action file create/delete
    for item in ['abort', 'clip', 'eq', 'force', 'kq', 'skip', 'wish']:
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
    if settask:
        settask = settask[:settask.find('.png')+4]
        if settask != 'target.png':
            target = os.path.join(dir, 'target.png')
            try:
                os.remove(target)
            except FileNotFoundError:
                pass
            shutil.copy2(os.path.join(dir, settask), target)

    return redirect(request.url)

@bp.route('/<actor_id>/tasks', methods=['GET', 'POST'])
def actorTasks(actor_id):
    if request.method == 'POST':
        return actorHandleTasksPost(actor_id)

    dir = getActorDir(actor_id)
    if not os.path.exists(dir):
        return 'Not found', 404

    tasks = []
    notes = None
    srch = re.compile('^target[a-z0-9\-]*.png$')
    actor = fillActorClass(actor_id)
    for entry in os.listdir(dir):
        entryfull = os.path.join(dir, entry)
        if not os.path.isfile(entryfull):
            continue
        if entry == 'notes.txt':
            with open(entryfull, 'r') as f:
                notes = f.read().splitlines()
            continue
        if not srch.match(entry):
            continue
        entry = getTargetCacheKey(entry, entryfull)
        tasks.append(entry)

    # Scraped from wiki
    json_fname = os.path.join(dir, 'actor.json')
    if os.path.exists(json_fname):
        with open(json_fname, 'r') as f:
            scraped = json.load(f)
            actor['name'] = scraped['name']
    else:
        scraped = None

    # Put the active one up top
    tasks.sort(key=lambda a: '' if a.startswith('target.png') else a.lower())
    return render_template(f'{request.blueprint}/tasks.html',
        a=actor, tasks=tasks, notes=notes, scraped=scraped)

@bp.route('/<actor_id>/rescrape', methods=['POST'])
def actorReScrape(actor_id):
    from scraper import scrapeActor
    scrapeActor(actor_id, request.values.get('remote_id', type=str, default=None),
        request.values.get('force', type=bool, default=False))

    return redirect(url_for('actors.actorTasks', actor_id=actor_id))

def actorFileOp(actor_id, fname):
    if actor_id is None:
        abort(400)

    enable = request.values.get('enable', type=int)
    full_fname = os.path.join(getActorDir(actor_id), fname)
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

@bp.route('/<actor_id>/skip')
def actorSkip(actor_id):
    return actorFileOp(actor_id, 'skip.txt')

@bp.route('/<actor_id>/abort')
def actorAbort(actor_id):
    return actorFileOp(actor_id, 'abort.txt')

@bp.route('/<actor_id>/wish')
def actorWish(actor_id):
    return actorFileOp(actor_id, 'wish.txt')
