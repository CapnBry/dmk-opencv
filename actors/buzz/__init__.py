import sys
import os
import cv2 as cv
import numpy as np
import importlib

def moveToTab(grabber, target: str):
    tab = ''
    # max = 0
    # haystack = grabber.grab(bounds=(590, 20, 960, 65)) #sizedep
    # for k in ['druun', 'cursedcrabs', 'forestfiends']:
    #     needle = cv.imread(f'events/{k}.png', cv.IMREAD_GRAYSCALE)
    #     _, maxval, _ = grabber.search(haystack, needle)
    #     grabber.log('WFE', f'{k}={maxval:0.3f}')

    #     if maxval > max:
    #         max = maxval
    #         tab = k
    # if max < 0.9:
    #     grabber.log('WFE', 'No tab match found')
    #     sys.exit(0)
    # grabber.log('WFE', f'On tab {tab}={max:0.3f} target {target}')

    if target != tab:
        if target == 'forestfiends':
            grabber.click(256, 628, interval=0.5) #sizedep
        elif target == 'cursedcrabs':
            grabber.click(252, 359, interval=0.5) #sizedep

def assignIdleTask(actor, grabber) -> bool:
    if actor == 'buzz':
        task = 'target-so'
    elif actor == 'mickey':
        task = 'target-rpc'
    elif actor == 'goofy':
        task = 'target-ctf'
    elif actor == 'cinderella':
        task = 'target-sftg'

    func = importlib.import_module('actors.default')
    return func.assignTask(actor, grabber, forceTask=task)

def assignTask(actor, grabber) -> bool:
    # Check if the idle.txt was created by the last call
    path_base = os.path.dirname(__file__)
    idle_fname = os.path.join(path_base, 'force.txt')
    do_idle = os.path.exists(idle_fname)
    if do_idle:
        return assignIdleTask(actor, grabber)

    # Close the tasks window
    grabber.click(1390, 102, interval=0.5) #sizedep
    # Open the events window
    grabber.click(768, 585, interval=0.5) #sizedep

    # Figure out if we're on the right screen: druun, cursedcrabs, forestfiends
    if actor in ['buzz', 'mickey']:
        targettab = 'forestfiends'
    else:
        targettab = 'cursedcrabs'
    moveToTab(grabber, targettab)

    # Drag left to right to see the available characters
    grabber.windowDrag((1174, 323), (-20, 0), 30) #sizedep

    # Check the two items to make sure there are enough
    if actor in ['mickey', 'goofy']:
        targetx = 463
    else:
        targetx = 830

    haystack_check = grabber.grab(bounds=(targetx+44, 278, targetx+44+138, 304))
    needle_check = cv.imread(f'events/hascheck.png', cv.IMREAD_GRAYSCALE)
    found = grabber.searchAll(haystack_check, needle_check, 0.9)
    if len(found) == 2:
        grabber.log('WFE', f'Ready item count=2, clicking x={targetx}')
        grabber.click(targetx+171, 430, interval=0.100)
    else:
        # Close the event window
        grabber.click(1381, 44, interval=0.100)
        # When the event window is closed, the actor has advanced so save
        # the idlefile to indicate next time that idle task should be assigned
        grabber.log('WFE', f'Ready item count={len(found)}, IDLE TASK')
        with open(idle_fname, "w"):
            pass
    return False
