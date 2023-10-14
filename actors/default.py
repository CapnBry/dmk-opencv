import sys
import os
import time
import cv2 as cv
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

def abortSpam(grabber, fname):
    with open(fname, 'r') as f:
        reason = f.read()
    grabber.log('ACT', Fore.YELLOW +
        '\n***********************************************************\n' +
        '*                                                         *\n' +
        f'* ABORT: {reason:<49}*\n' +
        '*                                                         *\n' +
        '***********************************************************\n' +
        Fore.WHITE);

    sys.exit(0)

def assignTask(actor, grabber, forceTask=None) -> bool:
    path_base = os.path.join(os.path.dirname(__file__), actor)
    do_skip = os.path.exists(os.path.join(path_base, 'skip.txt'))
    if do_skip:
        grabber.press('esc')
        time.sleep(0.500)
        return True

    do_abort = os.path.exists(os.path.join(path_base, 'abort.txt'))
    if do_abort:
        abortSpam(grabber, os.path.join(path_base, 'abort.txt'))

    # Bounds of the task area, first 2 items only
    bounds = (int(grabber.width*0.60), int(grabber.height*0.25), int(grabber.width*0.97), int(grabber.height*0.74))

    do_wish = os.path.exists(os.path.join(path_base, 'wish.txt'))
    if do_wish:
        target_png = os.path.join(os.path.dirname(__file__), 'wish.png')
    else:
        targetfname = (forceTask if forceTask else 'target') + '.png'
        target_png = os.path.join(path_base, targetfname)
    if not os.path.exists(target_png):
        # No target, just click GO on the first item
        clickGo(grabber, bounds, (int(grabber.width*0.92), int(grabber.height*0.41)))
        return False

    target = cv.imread(target_png, cv.IMREAD_GRAYSCALE)

    search_history = []
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
            maxloc = (int(grabber.width*0.92), bounds[1] + maxloc[1] + int(grabber.height*0.137))
            wish = 'wish' if do_wish else grabber.image_to_string(target).strip()
            grabber.log('ACT', f'Clicking {maxloc}={maxval:0.3f} after {x} scrolls ({wish})')

            clickGo(grabber, bounds, maxloc)

            if do_wish:
                os.remove(os.path.join(path_base, 'wish.txt'))
            if forceTask:
                os.remove(os.path.join(path_base, 'force.txt'))
            return False

        grabber.scroll(-423, bounds[0], bounds[1])
        time.sleep(0.100)

    grabber.log('ERR', ['%0.3f' % y for y in search_history])
    cv.imwrite('tasks.png', tasks)
    cv.imwrite('target.png', target)

    return False