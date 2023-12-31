import sys
import os
import time
import glob
import re
import numpy as np
import cv2 as cv
import app.main.main as main
from colorama import Fore, Back, Style

def clickGo(grabber, bounds, loc):
    target = cv.imread('images/go.png', cv.IMREAD_GRAYSCALE)
    for tries in range(4):
        grabber.click(loc[0], loc[1], interval=0.067)

        # make sure the GO went away
        tasks = grabber.grab(bounds=bounds)
        _, maxval, maxloc = grabber.search(tasks, target, cv.TM_CCOEFF_NORMED)
        if maxval < 0.90:
            return
        grabber.log('ACT', f'{Fore.YELLOW}Click did not register{Fore.WHITE}. Found {maxloc}={maxval:0.3f}')

def pauseSpam(grabber, fname):
    # Get any reason from the file
    with open(fname, 'r') as f:
        reason = f.read()
    # Make sure this doesn't fire again
    os.remove(fname)
    # Spam
    grabber.log('ACT', Fore.YELLOW +
        '\n***********************************************************\n' +
        '*                                                         *\n' +
        f'* PAUSE: {reason:<49}*\n' +
        '*                                                         *\n' +
        '***********************************************************\n' +
        Fore.WHITE)

    main.pauseMainThread.paused = True

img_wish = None
def clipOneTask(grabber, bounds):
    item = grabber.grab(bounds=bounds, color=True)
    # cv.imshow('Result', item)
    # cv.waitKey(2000)
    item_gray = cv.cvtColor(item, cv.COLOR_BGR2GRAY)

    # If there is a wish icon, shift the clipped item over to remove it
    global img_wish
    _, maxval, _ = grabber.search(item_gray, img_wish)
    if maxval > 0.85:
        item = item[:, 43:]
        item_gray = item_gray[:, 43:]

    #_, item_gray = cv.threshold(item_gray, 127, 255, cv.THRESH_BINARY)
    # cv.imshow('Result', item_gray)
    # cv.waitKey(3000)
    item_text = grabber.imgToStr(item_gray).lower()
    # sanitize
    item_text = re.sub('[^a-z ]', '', item_text).strip()

    # clip off the end of the search image
    item = item[:, 0:250]
    # clip off the start of the gray image so it won't have any actor icon
    item_gray = item_gray[:, 44:]
    # cv.imshow('Result', item_gray)
    # cv.waitKey(2000)

    return item, item_gray, item_text

def clipOneTaskInit():
    global img_wish
    if img_wish is None:
        img_wish = cv.imread('images/clip-wish.png', cv.IMREAD_GRAYSCALE)

def deleteFilesGlob(pattern):
    for f in glob.glob(pattern):
        os.remove(f)

def clipAllTasks(grabber, dest_path):
    deleteFilesGlob(os.path.join(dest_path, 'target-auto-??.png'))
    clipOneTaskInit()

    bounds_first = (896, 186, 896+405, 186+29)
    bounds_second = (bounds_first[0], bounds_first[1]+172, bounds_first[2], bounds_first[3]+172)

    lastGrab = None
    lastGrabTime = 0
    exitAfterThis = False
    taskIdx = 0
    while taskIdx < 30:
        item, item_gray, item_text = clipOneTask(grabber, bounds_first)
        if not lastGrab is None:
            _, maxval, _ = grabber.search(lastGrab, item_gray)
            # If the first item didn't change, grab the second and we're done
            if maxval > 0.98:
                grabber.log('CAT', f'Top did not change {maxval:0.3f}')
                exitAfterThis = True
                item, item_gray, item_text = clipOneTask(grabber, bounds_second)

        # Detect item being all white / grayed out
        _, item_bw = cv.threshold(item_gray, 127, 255, cv.THRESH_BINARY)
        avg = np.average(np.average(item_bw, axis=0), axis=0)
        if avg > 254.0:
            grabber.log('CAT', f'Item became desaturated {avg}')
            break

        nameguess = ''
        for word in item_text.split(' '):
            if len(word) > 0:
                nameguess += word[0]

        # wait at least 1 second to get a different mtime on the file
        now = time.monotonic()
        remain = 1.0 - (now - lastGrabTime)
        if remain > 0.0:
            time.sleep(remain)

        grabber.log('CAT', f'Clipped task [{item_text}]={nameguess}')
        cv.imwrite(os.path.join(dest_path, f'target-auto-{taskIdx:02d}.png'), item)
        lastGrabTime = time.monotonic()
        if exitAfterThis:
            break

        grabber.scroll(-423, bounds_first[0]-50, bounds_first[1])
        time.sleep(0.200) # need plenty of time between imwrites so be generous here
        taskIdx += 1
        lastGrab = item_gray

def assignTask(actor, grabber, forceTask=None) -> bool:
    path_base = os.path.join(os.path.dirname(__file__), actor)

    # ClipAll
    if os.path.exists(os.path.join(path_base, 'clip.txt')):
        os.remove(os.path.join(path_base, 'clip.txt'))
        clipAllTasks(grabber, path_base)
        # Close the tasks window
        grabber.click(1390, 102, interval=0.5)
        return False

    if os.path.exists(os.path.join(path_base, 'skip.txt')):
        # Close the task dialog
        grabber.click(1390, 102, interval=0.5)
        return True

    # Pause
    if os.path.exists(os.path.join(path_base, 'pause.txt')):
        pauseSpam(grabber, os.path.join(path_base, 'pause.txt'))
        return False

    # Bounds of the task area, first 2 items only
    bounds = (864, 166, 1396, 492)

    override = next(
        (o for o in [ 'wish', 'kq', 'eq' ] if os.path.exists(os.path.join(path_base, f'{o}.txt')))
        , None)

    if override:
        target_png = os.path.join(os.path.dirname(__file__), f'{override}.png')
        target_desc = override
    else:
        targetfname = (forceTask if forceTask else 'target') + '.png'
        target_png = os.path.join(path_base, targetfname)
        target_desc = None # filled in later
    if not os.path.exists(target_png):
        # No target, just click GO on the first item
        clickGo(grabber, bounds, (int(grabber.width*0.92), int(grabber.height*0.41)))
        return False

    target = cv.imread(target_png, cv.IMREAD_GRAYSCALE)

    search_history = []
    found = False
    for x in range(25):
        tasks = grabber.grab(bounds=bounds)
        match, maxval, maxloc = grabber.search(tasks, target, cv.TM_CCOEFF_NORMED)
        search_history.append(maxval)

        #grabber.log('ACT', f'Scroll={x} {maxval:0.3f}={maxloc}')
        #cv.imshow('Task List', tasks)
        #cv.waitKey(15000)
        #cv.imwrite('match.png', match)
        #cv.imwrite('tasks.png', tasks)
        #cv.imwrite('target.png', target)

        if maxval > 0.88:
            found = True
            maxloc = (int(grabber.width*0.92), bounds[1] + maxloc[1] + int(grabber.height*0.137))
            if not target_desc:
                target_desc = re.sub('[^a-z ]', '', grabber.imgToStr(target).lower()).strip()
            grabber.log('ACT', f'Clicking {maxloc}={maxval:0.3f} after {x} scrolls ({target_desc})')

            clickGo(grabber, bounds, maxloc)
            break

        grabber.scroll(-423, bounds[0], bounds[1])
        time.sleep(0.100)

    # Delete even if not found, must be stale
    if override:
        os.remove(os.path.join(path_base, f'{override}.txt'))
    if forceTask:
        os.remove(os.path.join(path_base, 'force.txt'))

    if not found:
        #grabber.log('ERR', f'Max={max(search_history):0.3f} {["%0.3f" % y for y in search_history]})
        grabber.log('ERR', ["%0.3f" % y for y in search_history])
        cv.imwrite('tasks.png', tasks)
        cv.imwrite('target.png', target)

    return False