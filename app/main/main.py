import sys
import os
import threading
import time
import datetime
import re
import numpy as np
import cv2 as cv
import pyautogui
import random
import importlib
from dmkgrabber import DmkGrabber
from colorama import Fore, Back, Style
from dataclasses import dataclass

STANDALONE_CLICKS = [
    # latency sensitive items go first
    'complete-toon',
    'magic',
    'happy',
    'attract',
    'catbasket',
    'catmilk',
    # Static items
    'close-novideo',
    #'free',
    'swipe',
    'clear',
    'claim',
    'watchad-bonus',
    'watchad-mystery-parade',
    'watchad-sound',
    'watchad-thanks',
    'levelup',
    'collect-bronze-silver',
    'levelup-char',
]

PERIODIC_CLICKS = [
    'reward-streak',
    'enchant-complete',
    'collect-calendar',
    'claim-background',
    'levelup-char-tickle',
    'watchad-gem-tickle',
    'tasks-reward-tickle',
    'close-popupad',
    'close-popupad-01',
    'close-popupad-02',
    'close-popupad-03',
    'watchad-bronze',
    'watchad-magic',
    'quest-end-reward',
    'striking-gold', # popup when event starts
    'aristo-tickle',
    'close-missed-ad',
    'close-chestmenu', # chestmenu and charactermenu (should come last!)
]

@dataclass
class Actor:
    name: str
    last: float
    count: int
    needle: np.array
    handler: any

def clickParadeComplete(grabber, loc) -> bool:
    # To account for the top parade float going behind the EC, drag to the side or down
    # clicking the actor portrait takes a while to settle the further you are
    grabber.click(loc[0], loc[1], interval=3.0)
    rand = random.randrange(3)
    if rand == 0:
        # top->bottom, move the whole parade lower away from top of screen
        windowDrag(grabber, 1, 200)
    elif rand == 1:
        # right->left, move out from under the EC HUD
        windowDrag(grabber, 2, 200)
    else:
        # Just take what we got
        pass

    return True

def clickAdWait(grabber, loc) -> bool:
    # Click the sound off and then assume a 40s ad, and click close
    grabber.click(loc[0], loc[1], interval=0.020)
    time.sleep(40.0)
    grabber.click(1393, 48, interval=0.020)
    return True

def clickRewardStreak(grabber, loc) -> bool:
    img_calendar = grabber.grab(bounds=(0,0, 1050, 630))
    return lookAndClick(grabber, 'collect-calendar', img_calendar, periodicCheck.img_periodic['collect-calendar'], 0.80)

def clickCheckGreen(grabber, loc) -> bool:
    # actually checks that it is not gray
    #bounds = (loc[0] - 90, loc[1] - 25, loc[0] - 45, loc[1] + 25)
    #bounds = (loc[0] - 20, loc[1] - 30, loc[0] + 20, loc[1] - 10)
    bounds = (loc[0] - 60, loc[1] - 24, loc[0] + 60, loc[1] - 12)
    avg_color = grabber.grabColor(bounds)[0:3]
    how_colorful = np.std(avg_color)
    #print(f'Avg color: {avg_color} dev={how_colorful}')
    # colorful means the RGB values are not close, as a gray button will have all RGB the same value
    if how_colorful > 10:
        grabber.click(loc[0], loc[1])
        return True
    else:
        return False

def clickLevelupChar(grabber, loc) -> bool:
    if loc[0] < 700:
        grabber.click(1240, 340)
    else:
        grabber.click(250, 340)
    return True

def clickGemTickle(grabber, loc) -> bool:
    # click the tickle, the screen will scroll over so give it time
    grabber.click(loc[0], loc[1], interval=3.0)
    # click the theater, will open confirmation / not avail message
    grabber.click(715, 290)
    # rely on standalone to click the button
    return True

def clickQuestStartDialog(grabber, loc) -> bool:
    grabber.click(loc[0], loc[1])
    time.sleep(2)
    chatbubbleProcess(grabber)
    return True

def clickTasksReward(grabber, loc) -> bool:
    # open daily/weekly/event/season reward
    if loc:
        grabber.click(loc[0], loc[1], interval=1.0)

    # grab to top of where the collect button is (top right)
    # On the season pass page there's no button so it won't be very green
    # Collect:      46.74358974 229.38615385 129.34153846 255
    # green check: (mostly white)
    # season pass:  71.45538462 195.8174359  229.43538462 255 (gold border)
    # GO:          251.98461538 213.92512821  49.41692308 255 (blue)
    # Grey GO:     185.39128205 186.11897436 185.39128205 255 (gray)
    avg_color = grabber.grabColor((1055, 214, 1205, 227))
    iscollect =  avg_color[0] < 60 and avg_color[1] > 220 and (120 < avg_color[2] < 140)
    #print(f'{avg_color} = {iscollect}')
    #return True

    if iscollect:
        # not season pass, collect button is right on the top
        # "Collect" button on the top left
        grabber.click(1125, 240, interval=1.0)
        # Close dialog
        grabber.click(1385, 45, interval=0.033)
        # leave window open to get the reward
    else:
        # is season pass, click roughly the center of the free teir list (X=770 for next locked?)
        grabber.click(640, 445, interval=1.0)
        # Claim button on "Reward Claimed" popup
        grabber.click(725, 550, interval=0.033)

    return True

def clickAristoTickle(grabber, loc) -> bool:
    # open the event dialog
    grabber.click(loc[0], loc[1], interval=1.0)
    # Aristocats / Cauldron
    # # click aristo-gift-tickle (the box with the play button, no border)
    grabber.click(230, 340, interval=1.0)
    # # click watchad-mystery-radiant (should be green, why else would we be here)
    grabber.click(565, 475)
    return True

LOOKANDCLICK_CUSTOM = {
    'watchad-bonus': (870, 525),
    'claim-background': (714, 541),
    'enchant-complete': (720, 560),
    'watchad-thanks': (710, 530),
    'levelup': (710, 560),
    'striking-gold': (715, 462),
    'tasks-reward-tickle': clickTasksReward,
    'watchad-sound': clickAdWait,
    'reward-streak': clickRewardStreak,
    'collect-bronze-silver': clickCheckGreen,
    'watchad-bronze': clickCheckGreen,
    'watchad-magic': clickCheckGreen,
    'levelup-char': clickLevelupChar,
    'watchad-gem-tickle': clickGemTickle,
    'tickle-parade-complete': clickParadeComplete,
    'tickle-quest-avail': clickQuestStartDialog,
    'quest-end-reward': clickLevelupChar,
    'aristo-tickle': clickAristoTickle,
}

def clickAllCommon(grabber: DmkGrabber, src: str) -> None:
    grabber.log('LAC', Fore.RED+'** Nuclear clicking: {src} **'+Fore.WHITE)

    # Save a screenshot for later ss-yyyymmdd-hhnnss.png
    ss = grabber.grab(color=True)
    cv.imwrite(datetime.datetime.now().strftime('ss-%Y%m%d-%H%M%S.png'), ss)

def clickAllLAC(grabber):
    clickAllCommon(grabber, 'AllLAC')

    # Click all the items that have a defined place
    for v in LOOKANDCLICK_CUSTOM.values():
        if isinstance(v, tuple):
            grabber.click(v[0], v[1], interval=0.100)

def clickEverywhere(grabber):
    clickAllCommon(grabber, 'Everywhere')

    width = grabber.width
    height = grabber.height
    for y in range(0.05, 0.95, 0.06):
        for x in range(0.05, 0.95, 0.1):
            grabber.click(int(x * width), int(y * height), interval=0.100)

def lookAndClick(grabber, name, haystack, needle, threshold=0.97, extraWait=False):
    match, maxval, maxloc = grabber.search(haystack, needle, cv.TM_CCOEFF_NORMED, True)

    #print(f'Result {maxval} at {maxloc}')

    if maxval > threshold:
        if extraWait:
            # some sort of lockout on clicking things?
            time.sleep(1.0)
        clickpos = LOOKANDCLICK_CUSTOM.get(name) or maxloc
        retVal = True
        if type(clickpos) is tuple:
            grabber.click(clickpos[0], clickpos[1], interval=0.067)
        else:
            retVal = clickpos(grabber, maxloc)
            #clickpos = resultDesc or clickpos

        # Success
        if retVal:
            grabber.log('LAC', f'{name}={maxval:0.3f} at {clickpos}')
            if (lookAndClick.lastMatch == name):
                lookAndClick.lastMatchCnt = lookAndClick.lastMatchCnt + 1
                # If this is hitting over and over, delay the next loop
                # Or try some hella clicking
                if lookAndClick.lastMatchCnt == 30:
                    clickEverywhere(grabber)
                elif lookAndClick.lastMatchCnt == 20:
                    clickAllLAC(grabber)
                elif lookAndClick.lastMatchCnt == 15:
                    grabber.scroll(-2000, center=True)
                elif lookAndClick.lastMatchCnt > 10:
                    time.sleep(30.0)
            else:
                lookAndClick.lastMatch = name
                lookAndClick.lastMatchCnt = 1

        # cv.imshow('Result', needle)
        return retVal
    elif maxval > (threshold - 0.10):
        grabber.log('CLOSE', f'{name}={maxval:0.3f} at {maxloc}')
    # in progress attract sometimes 0.859-0.912
    # weekly/daily checks match complete-toon/2 0.946-0.956

    return False

def windowDrag(grabber, dir, amount):
    MOVE_PER_STEP = 20

    if dir == 0:
        # Left to Right
        startPos = (150, 320)
        moveParams = (MOVE_PER_STEP, 0)
    elif dir == 1:
        # Top to Bottom
        startPos = (573, 65)
        moveParams = (0, MOVE_PER_STEP)
    elif dir == 2:
        # Right to Left
        startPos = (1290, 301)
        moveParams = (-MOVE_PER_STEP, 0)
    else:
        # Bottom to Top (3)
        startPos = (573, 600)
        moveParams = (0, -MOVE_PER_STEP)
        # Bottom to top always requires more?
        amount = (amount * 1.1) + (2 * MOVE_PER_STEP)

    cnt = int(amount / MOVE_PER_STEP) + 1
    grabber.windowDrag(startPos, moveParams, cnt)

def moveRandom(grabber):
    grabber.activate()
    windowDrag(grabber, random.randrange(4), 500)

    # dir = random.randrange(16)

    # keys = []
    # keys.append('w' if (dir & 1) else 's')
    # keys.append('a' if (dir & 2) else 'd')
    # grabber.log('RND', f'moveRandom({keys}, {dir})')

    # pyautogui.keyDown(keys[0])
    # pyautogui.keyDown(keys[1])
    # time.sleep(0.5 + (dir*0.1))
    # pyautogui.keyUp(keys[1])
    # pyautogui.keyUp(keys[0])

def doRandom(grabber) -> bool:
    now = time.monotonic()
    if now - doRandom.lastRun < (60*10):
        return False
    doRandom.lastRun = now

    if not grabber.isForeground():
        return

    grabber.log('RND', Fore.BLUE+'~*~*~ Random Time ~*~*~'+Fore.WHITE)
    # action = random.randrange(10)
    # if action == 0:
        # grabber.log('RND', 'Checking for Chest Ads')
        # # open chest
        # grabber.press('v')
        # time.sleep(1)
        # periodicCheck.lastCheck = 0
    # elif action == 1:
        # grabber.log('RND', 'Checking for Magic Ads')
        # # Open Store -> Magic
        # grabber.press('z')
        # time.sleep(1)
        # grabber.press('a')
        # time.sleep(1)
        # periodicCheck.lastCheck = 0
    # else:
    moveRandom(grabber)

    return True

def ocrNextActivityTime(grabber):
    haystack = grabber.grab(bounds=(316, 183, 485, 215))
    #haystack = cv.equalizeHist(haystack)
    _, haystack = cv.threshold(haystack, 248, 255, cv.THRESH_BINARY)
    #haystack = cv.blur(haystack, (3,3))
    #_, haystack = cv.threshold(haystack, 128, 255, cv.THRESH_BINARY)
    timestr = grabber.imgToStr(haystack)
    if timestr == '':
        return
    cv.imshow('Result', haystack)
    # 3mini20s, 3min 04s, 3min 475, 345(34s), 12 min 46 $s, 12min12s, 1imin55s, li min 23s, Wmin its(11 min 12 s)
    # last character can be s, 5, 8, $
    if timestr[-1] in ['s', 'S', '5', '8', '$']:
        convert = timestr[:-1].strip() + 's'
    else:
        convert = timestr
    print(f'Raw=[{timestr}] convert={convert}')

def testSearch(grabber, needle, bounds=None):
    while True:
        #clickTasksReward(grabber, None)

        haystack = grabber.grab(bounds=bounds)
        #print(grabber.imgToStr(haystack))
        match, maxval, maxloc = grabber.search(haystack, needle, cv.TM_CCOEFF_NORMED, True)
        print(f'Result {maxval} at {maxloc} center')
        #clickCheckGreen(grabber, maxloc) # use watchad-bronze / watchad-mystery-radiant

        #cv.imshow('Result', match)
        #ocrNextActivityTime(grabber)

        if cv.waitKey(1000) == ord('q'):
            sys.exit(0)

def standaloneCheck(grabber) -> bool:
    ss_all = grabber.grab(UpdatePlace=True, bounds=(0,0,1440,485)) # bounds=(0,0,1266,715))
    if ss_all is None:
        return False

    retVal = False
    #cv.imshow('Whole', ss_all)
    #start = timer()
    for k in standaloneCheck.img_standalones:
        if lookAndClick(grabber, k, ss_all, standaloneCheck.img_standalones[k], extraWait=retVal):
            retVal = True
    #grabber.log('PROF', f'Dur {timer() - start:0.3f}')

    return retVal

def actorCheckNew(grabber):
    grabber.activate(interval=0.100)
    # Get the actor's photo before it changes when clicked
    img_portrait = grabber.grab(bounds=(21,24,95,62), color=True)
    #cv.imwrite('actortest.png', img_portrait)
    img_portrait_gray = cv.cvtColor(img_portrait, cv.COLOR_BGR2GRAY)

    # Click to open the tasks window hopefully
    grabber.click(52, 67, interval=0.700)
    # Try to get the name from the window title
    img_name = grabber.grab(bounds=(935,118,1375,157))
    #cv.imshow('Result', img_name)
    #cv.waitKey(3000)
    _, img_name = cv.threshold(img_name, 220, 255, cv.THRESH_BINARY)
    name = grabber.imgToStr(img_name)
    #cv.imshow('Result', img_name)
    #cv.waitKey(3000)

    bestMatch = { 'val': 0.0, 'name': '' }
    for a in actorsCheckAssign.actors:
        _, maxval, _ = grabber.search(img_portrait_gray, a.needle)
        if maxval > bestMatch['val']:
            bestMatch['val'] = maxval
            bestMatch['name'] = a.name

    # If no good match, create a new actor
    isNew = bestMatch['val'] < 0.9

    # sanitize the name to just upper/lower and replace internal space with underscore
    name = re.sub('[^a-zA-Z ]', '', name).strip()
    if name[-3:].lower() == 'lvl':
        name = name[:-3].strip()
    name = name.replace(' ', '_')

    grabber.log('ACT', f'New actor {name}: {isNew} (closest was {bestMatch["name"]}={bestMatch["val"]:0.3f})')

    if isNew:
        # New actor! Create a directory for them with their portrait
        newdir = os.path.join('actors', f'{name}_NEW')
        if not os.path.exists(newdir):
            os.mkdir(newdir)
            cv.imwrite(os.path.join(newdir, 'actor.png'), img_portrait)
            # Reload the list of actors
            actorsCheckAssign.actors = actorsLoad(grabber)

    # Click the close button on the actor's window
    grabber.click(1388, 100, interval=0.067)

    return isNew

def ticklerCheck(grabber) -> int:
    ### Tickler corner stuff
    ss_corner = grabber.grab(bounds=(10,10,125,140))
    cv.imshow('Corner', ss_corner)
    #print('ac')

    # check for any character portrait tickle active
    _, maxval, _ = grabber.search(ss_corner, ticklerCheck.img_tickactive)
    if maxval < 0.99:
        return 0

    # Complete Task
    foundAnything = False
    expediteNextActorCheck = False
    if lookAndClick(grabber, 'tickle-parade-complete', ss_corner, ticklerCheck.img_tickparadecomplete):
        # must return "no tickle" or will just come right back into this function and find the tickle-complete
        return 0
    if lookAndClick(grabber, 'tickle-complete', ss_corner, ticklerCheck.img_tickcomplete):
        foundAnything = True
    elif actorsCheckAssign(grabber, ss_corner):
        # Assign new task if the tickle is gone
        foundAnything = True
        expediteNextActorCheck = True
    elif lookAndClick(grabber, 'tickle-quest-avail', ss_corner, ticklerCheck.img_tickqavail):
        # must come after actor check because overlaps with chest/parade
        foundAnything = True

    # If the tickactive is present but no other template matches, it is possible
    # this is a new actor that needs to be added
    if foundAnything:
        ticklerCheck.failCnt = 0
    else:
        ticklerCheck.failCnt += 1
        if ticklerCheck.failCnt == 5:
            if actorCheckNew(grabber):
                ticklerCheck.failCnt = 0

    return 1 if expediteNextActorCheck else 2

def actorsLoad(grabber):
    retVal = []
    dir = 'actors'
    for a in os.listdir(dir):
        if a == '__pycache__':
            continue
        if os.path.isdir(os.path.join(dir, a)):
            profile_fname = os.path.join(dir, a, 'actor.png')
            if os.path.exists(profile_fname):
                retVal.append(
                    Actor(name=a, last=0.0, count=0,
                          needle=cv.imread(profile_fname, cv.IMREAD_GRAYSCALE), handler=None)
                )
            stale_force_fname = os.path.join(dir, a, 'force.txt')
            if os.path.exists(stale_force_fname):
                grabber.log('ACT', f'{Fore.YELLOW}Removing stale force.txt for {Fore.WHITE}{a}')
                os.remove(stale_force_fname)
            if os.path.exists(os.path.join(dir, a, 'abort.txt')):
                grabber.log('ACT', f'{Fore.YELLOW}WARNING:{Fore.WHITE} {a} has abort.txt')
    grabber.log('ACT', f'Loaded {len(retVal)} actors')
    return retVal

def actorsSort():
    # Actors that get used the most move to the front
    actorsCheckAssign.actors.sort(key=lambda a: a.count, reverse=True)

def actorsCheckAssign(grabber:DmkGrabber, ss):
    now = time.monotonic()
    if now - actorsCheckAssign.lastActorAssignCheck < (30 if actorsCheckAssign.lastWasSkip else 5):
        return False

    for a in actorsCheckAssign.actors:
        _, maxval, maxloc = grabber.search(ss, a.needle, returnCenter=True)
        #grabber.log('ACA', f'{a}={maxval:0.3f}')
        if maxval > 0.97:
            #after = time.monotonic()
            #print(f'Actor check took {after-now:0.3f}s')

            # before clicking, get a fresh portrait photo if needed
            portrait_fname = os.path.join('actors', a.name, 'folder.png')
            if not os.path.exists(portrait_fname):
                cv.imwrite(portrait_fname, grabber.grab(bounds=(22, 25, 96, 110), color=True))
            grabber.click(maxloc[0], maxloc[1], interval=0.5)

            closeness = (f'{Fore.RED}CLOSE{Fore.WHITE} ') if maxval < 0.991 else ''
            grabber.log('ACT', f'Assigning action for actor: {closeness}{maxval:0.3f} {a.name} x{a.count}')
            if a.handler is None:
                if os.path.exists(os.path.join('actors', a.name, '__init__.py')):
                    namespace = importlib.import_module('actors.' + a.name)
                else:
                    namespace = importlib.import_module('actors.default')
                a.handler = namespace.assignTask

            actorsCheckAssign.lastWasSkip = a.handler(a.name, grabber)
            actorsCheckAssign.lastActor = a.name

            if not actorsCheckAssign.lastWasSkip:
                a.last = now
                a.count += 1
                actorsSort()
                # Need to run again to refresh ss
                return True
        elif maxval > 0.90:
            grabber.log('CLOSE', f'Actor {a.name}={maxval}')

    # Stop checking once no actor was found
    actorsCheckAssign.lastActorAssignCheck = now
    return False

def actorsInit(grabber):
    actorsCheckAssign.lastActorAssignCheck = 0
    actorsCheckAssign.lastActor = ''
    actorsCheckAssign.lastWasSkip = False
    actorsCheckAssign.actors = actorsLoad(grabber)

def standaloneInit(grabber):
    standaloneCheck.img_standalones = {k: cv.imread(f'images/{k}.png', cv.IMREAD_GRAYSCALE) for k in STANDALONE_CLICKS}

def lookAndClickInit(grabber):
    lookAndClick.lastMatch = ''
    lookAndClick.lastMatchCnt = 0

def chatbubbleVisible(ss_all):
    dialog_crop = ss_all[183:203,467:921]
    avg = np.average(dialog_crop, axis=0)
    avg = np.average(avg, axis=0)
    return avg > 254.0

def chatbubbleProcess(grabber):
    clickCnt = 0
    while True:
        clickCnt = clickCnt + 1
        if clickCnt > 30:
            return

        ss_all = grabber.grab()
        if not chatbubbleVisible(ss_all):
            return

        grabber.log('PCK', f'Chat bubble active')
        grabber.click(720, 300) # 720 if maxval > 0.90 else 1280, 300)
        time.sleep(2)

def periodicCheck(grabber):
    CHECK_INTERVAL = 60 * 5
    now = time.monotonic()
    if now - periodicCheck.lastCheck < CHECK_INTERVAL:
        return False
    periodicCheck.lastCheck = now

    ss_all = grabber.grab()
    if ss_all is None:
        return False

    grabber.log('PCK', Fore.BLUE+'~*~*~ Periodic Check ~*~*~'+Fore.WHITE)
    # Periodics are different than standalones because only one can fire at a time
    for k in periodicCheck.img_periodic:
        if lookAndClick(grabber, k, ss_all, periodicCheck.img_periodic[k]):
            # Check more quickly for next one
            periodicCheck.lastCheck = now - CHECK_INTERVAL + 60
            return True

    # Check for quest begin/end chat bubbles
    if chatbubbleVisible(ss_all):
        chatbubbleProcess(grabber)
        # check next time for the completion screen
        periodicCheck.lastCheck = 0
        return True

    return False

def periodicInit(grabber):
    periodicCheck.img_periodic = {k: cv.imread(f'images/{k}.png', cv.IMREAD_GRAYSCALE) for k in PERIODIC_CLICKS}
    periodicCheck.lastCheck = 0

def tickleInit(grabber):
    ticklerCheck.img_tickcomplete = cv.imread('images/tickle-complete.png', cv.IMREAD_GRAYSCALE)
    ticklerCheck.img_tickparadecomplete = cv.imread('images/tickle-parade-complete.png', cv.IMREAD_GRAYSCALE)
    ticklerCheck.img_tickactive = cv.imread('images/tickle-active.png', cv.IMREAD_GRAYSCALE)
    ticklerCheck.img_tickqavail = cv.imread('images/tickle-quest-avail.png', cv.IMREAD_GRAYSCALE)
    ticklerCheck.failCnt = 0

def restartAppCheck(grabber):
    # Check for exit-at
    now = datetime.datetime.now()
    if grabber.config.exit_at and now > grabber.config.exit_at:
        grabber.log('MAIN', Fore.GREEN+'Exiting due to exit-at'+Fore.WHITE)
        sys.exit(0)

    now = time.monotonic()
    if now - restartAppCheck.startTime < (3600 * 4):
        return

    restartAppCheck.startTime = now
    grabber.log('MAIN', Fore.GREEN+'Maximum run time reached, restarting'+Fore.WHITE)
    grabber.click(1410, -16) # close
    time.sleep(30)
    grabber.launchApp()

def shutdown():
    if shutdown.keepRunning:
        try:
            global grabber
            shutdown.keepRunning = False
            grabber.activate(interval=0.5)

            global robot
            robot.join(90.0)
            grabber.click(1410, -16, interval=1.0) # close
        except:
            pass

def pauseMainThread(enable):
    pauseMainThread.paused = enable

def mainLoopDelayForNac(noActivityCnt:int) -> int:
    # 500ms for first 0-2s (4x)
    # 2000ms for 2s-10s (4x)
    # else 5000ms
    if noActivityCnt < 4:
        return 500
    if noActivityCnt < 8:
        return 2000
    return 5000

def mainLoop(grabber):
    now = time.monotonic()
    restartAppCheck.startTime = now
    doRandom.lastRun = now
    lastActivity = now
    noActivityCnt = 0
    while shutdown.keepRunning:
        if pauseMainThread.paused:
             time.sleep(5.0)
             lastActivity = time.monotonic()
             continue

        didSomething = standaloneCheck(grabber) # updates window location
        didSomething = periodicCheck(grabber) or didSomething
        if not didSomething and noActivityCnt >= 2: # 2+this=3x delays after
            ticklerResult = ticklerCheck(grabber)
            # Result == 0 no tickle
            # Result == 1 check again next loop (assigned actor)
            if ticklerResult == 1:
                lastActivity = now
                noActivityCnt = 1
            # Result == 2 delay next check
            elif ticklerResult == 2:
                didSomething = True

        now = time.monotonic()
        if didSomething:
            lastActivity = now
            noActivityCnt = 0
        else:
            noActivityCnt += 1
            # If no activity in X seconds, do something random
            if now - lastActivity > 15:
               if doRandom(grabber):
                   noActivityCnt = 0

        delay = mainLoopDelayForNac(noActivityCnt)
        #print(delay)
        key = cv.waitKey(delay)
        if key == ord('q'):
            return
        elif key == ord(' '):
            moveRandom(grabber)
        else:
            restartAppCheck(grabber)

# Setup
grabber = DmkGrabber()
grabber.launchApp()
grabber.log('MAIN', f'Window size is {grabber.width}x{grabber.height}')

#testSearch(grabber, cv.imread('actors/fred/actor.png', cv.IMREAD_GRAYSCALE))

shutdown.keepRunning = True
pauseMainThread.paused = False
actorsInit(grabber)
periodicInit(grabber)
tickleInit(grabber)
standaloneInit(grabber)
lookAndClickInit(grabber)

robot = threading.Thread(target=mainLoop, args=(grabber,), name='Main Robot')
robot.daemon = True
robot.start()

if __name__ == "__main__":
    robot.join()
    cv.destroyAllWindows()

