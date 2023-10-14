import sys
import os
import time
import datetime
import numpy as np
import cv2 as cv
import pyautogui
import random
import importlib
from windowgrabber import WindowGrabber
from colorama import Fore, Back, Style

STANDALONE_CLICKS = [
    # latency sensitive items go first
    'complete-toon',
    'magic',
    'happy',
    'attract',
    #'catbasket',
    #'catmilk',
    # Static items
    'close-novideo',
    'free',
    'swipe',
    'clear',
    'claim',
    'watchad-bonus',
    'watchad-mystery-parade',
    'watchad-sound',
    'watchad-thanks',
    'claim-calendar',
    'levelup',
    'collect-bronze-silver',
    'levelup-char',
]

PERIODIC_CLICKS = [
    'reward-streak',
    'collect-calendar',
    'claim-gold',
    'claim-milestone',
    'levelup-char-tickle',
    'watchad-gem-tickle',
    'tasks-reward-tickle',
    'close-popupad',
    'close-popupad-01',
    'close-popupad-02',
    'close-popupad-03',
    'watchad-bronze',
    'watchad-magic',
    'watchad-mystery-radiant',
    'quest-end-reward',
    #'aristo-tickle',
    'close-missed-ad',
    'close-chestmenu', # chestmenu and charactermenu (should come last!)
]

config = {}

def clickMoveUp(grabber, loc) -> bool:
    grabber.click(loc[0], loc[1], interval=0.033)
    # To account for the top parade float going behind the EC, drag to the side sometimes
    if random.randrange(4) == 0:
        # clicking the actor portrait takes a while to settle the further you are
        time.sleep(0.800)
        windowDrag(grabber, 2, 200)
    # pyautogui.hotkey('a', interval=0.5)
    return True

def clickAdWait(grabber, loc) -> bool:
    # Click the sound off and then assume a 40s ad, and click close
    grabber.click(loc[0], loc[1], interval=0.020)
    time.sleep(40.0)
    grabber.click(1393, 48, interval=0.020) #sizedep
    return True

def clickRewardStreak(grabber, loc) -> bool:
    img_calendar = grabber.grab(bounds=(0,0, 1050, 630)) #sizedep
    return lookAndClick(grabber, 'collect-calendar', img_calendar, periodicCheck.img_periodic['collect-calendar'], 0.80)

def clickCheckGreen(grabber, loc) -> bool:
    # actually checks that it is not gray
    #bounds = (loc[0] - 90, loc[1] - 25, loc[0] - 45, loc[1] + 25) #sizedep
    #bounds = (loc[0] - 20, loc[1] - 30, loc[0] + 20, loc[1] - 10) #sizedep
    bounds = (loc[0] - 60, loc[1] - 24, loc[0] + 60, loc[1] - 12) #sizedep
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
        grabber.click(1240, 340) #sizedep
    else:
        grabber.click(250, 340) #sizedep
    return True

def clickGemTickle(grabber, loc) -> bool:
    # click the tickle, the screen will scroll over so give it time
    grabber.click(loc[0], loc[1], interval=3.0)
    # click the theater, will open confirmation / not avail message
    grabber.click(715, 290) #sizedep
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
    avg_color = grabber.grabColor((1055, 214, 1205, 227)) #sizedep
    iscollect =  avg_color[0] < 60 and avg_color[1] > 220 and (120 < avg_color[2] < 140)
    #print(f'{avg_color} = {iscollect}')
    #return True

    if iscollect:
        # not season pass, collect button is right on the top
        # "Collect" button on the top left
        grabber.click(1125, 240, interval=1.0) #sizedep
        # Close dialog
        grabber.click(1385, 45, interval=0.033) #sizedep
        # leave window open to get the reward
    else:
        # is season pass, click roughly the center of the free teir list (X=770 for next locked?)
        grabber.click(640, 445, interval=1.0) #sizedep
        # Claim button on "Reward Claimed" popup
        grabber.click(725, 550, interval=0.033) #sizedep

    return True

def clickAristoTickle(grabber, loc) -> bool:
    # open the event dialog
    grabber.click(loc[0], loc[1], interval=1.0)
    # Welcome Fear
    # Watch Ad
    grabber.click(958, 546, interval=1.0) #sizedep
    # Aristocats
    # # click aristo-gift-tickle (the box with the play button, no border)
    # grabber.click(230, 340, interval=1.0) #sizedep
    # # click watchad-mystery-radiant (should be green, why else would we be here)
    # grabber.click(565, 475) #sizedep
    return True

LOOKANDCLICK_CUSTOM = {
    'watchad-bonus': (870, 525), #sizedep
    'claim-calendar': (710, 530), #sizedep
    'claim-gold': (740, 540), #sizedep
    'claim-milestone': (712, 547), #sizedep
    'watchad-thanks': (710, 530), #sizedep
    'levelup': (710, 560), #sizedep
    'tickle-complete': clickMoveUp,
    'tasks-reward-tickle': clickTasksReward,
    'watchad-sound': clickAdWait,
    'reward-streak': clickRewardStreak,
    'collect-bronze-silver': clickCheckGreen,
    'watchad-bronze': clickCheckGreen,
    'watchad-magic': clickCheckGreen,
    #'watchad-mystery-radiant': clickCheckGreen, # not used (aristo-tickle)
    'levelup-char': clickLevelupChar,
    'watchad-gem-tickle': clickGemTickle,
    'tickle-quest-avail': clickQuestStartDialog,
    'quest-end-reward': clickLevelupChar,
    'aristo-tickle': clickAristoTickle,
}

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
            # assume lambda or function name
            # 'xxx': lambda grabber, loc: grabber.log('LAC', 'Lambda {log}')
            retVal = clickpos(grabber, maxloc)

        # Success
        if retVal:
            grabber.log('LAC', f'{name}={maxval:0.3f} at {clickpos}')
            if (lookAndClick.lastMatch == name):
                lookAndClick.lastMatchCnt = lookAndClick.lastMatchCnt + 1
                # If this is hitting over and over, delay the next loop
                if (lookAndClick.lastMatchCnt > 10):
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
        startPos = (150, 320) #sizedep
        moveParams = (MOVE_PER_STEP, 0)
    elif dir == 1:
        # Top to Bottom
        startPos = (573, 65) #sizedep
        moveParams = (0, MOVE_PER_STEP)
    elif dir == 2:
        # Right to Left
        startPos = (1290, 301) #sizedep
        moveParams = (-MOVE_PER_STEP, 0)
    else:
        # Bottom to Top (3)
        startPos = (573, 600) #sizedep
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
    timestr = grabber.image_to_string(haystack).strip()
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
        #print(grabber.image_to_string(haystack))
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

def ticklerCheck(grabber) -> bool:
    ### Tickler corner stuff
    ss_corner = grabber.grab(bounds=(10,10,125,140))
    cv.imshow('Corner', ss_corner)
    if ss_corner is None:
        return False

    # check for any character portrait tickle active
    _, maxval, _ = grabber.search(ss_corner, ticklerCheck.img_tickactive, cv.TM_CCOEFF_NORMED)
    if maxval < 0.99:
        return False

    # Complete Task
    if lookAndClick(grabber, 'tickle-complete', ss_corner, ticklerCheck.img_tickcomplete):
        pass
    elif actorsCheckAssign(grabber, ss_corner):
        # Assign new task if the tickle is gone
        pass
    elif lookAndClick(grabber, 'tickle-quest-avail', ss_corner, ticklerCheck.img_tickqavail):
        # must come after actor check because overlaps with chest/parade
        pass

    return True

def actorsLoad(grabber):
    retVal = {}
    dir = 'actors'
    for a in os.listdir(dir):
        if a == '__pycache__':
            continue
        if os.path.isdir(os.path.join(dir, a)):
            profile_fname = os.path.join(dir, a, 'actor.png')
            if os.path.exists(profile_fname):
                retVal[a] = cv.imread(profile_fname, cv.IMREAD_GRAYSCALE)
    grabber.log('ACT', f'Loaded {len(retVal)} actors')
    return retVal

def actorsCheckAssign(grabber, ss):
    now = time.monotonic()
    if now - actorsCheckAssign.lastActorAssignCheck < (30 if actorsCheckAssign.lastWasSkip else 5):
        return False

    for a in actorsCheckAssign.actors:
        needle = actorsCheckAssign.actors[a]
        match, maxval, maxloc = grabber.search(ss, needle, cv.TM_CCOEFF_NORMED, True)
        #grabber.log('ACA', f'{a}={maxval:0.3f}')
        if maxval > 0.97:
            grabber.click(maxloc[0], maxloc[1], interval=0.5)

            # Prevent running the same actor over and over, but click
            # to see if it advances
            if actorsCheckAssign.lastWasSkip and actorsCheckAssign.lastActor == a:
                break
            actorsCheckAssign.lastActor = a

            closeness = (f'{Fore.RED}CLOSE{Fore.WHITE} ') if maxval < 0.991 else ''
            grabber.log('ACT', f'Assigning action for actor: {closeness}{maxval:0.3f} {a}')
            if os.path.exists(os.path.join('actors', a, '__init__.py')):
                func = importlib.import_module('actors.' + a)
            else:
                func = importlib.import_module('actors.default')
            actorsCheckAssign.lastWasSkip = func.assignTask(a, grabber)
            # Need to run again to refresh ss
            return True
        elif maxval > 0.90:
            grabber.log('CLOSE', f'Actor {a}={maxval}')

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
    dialog_crop = ss_all[183:203,467:921] #sizedep
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
        grabber.click(720, 300) # 720 if maxval > 0.90 else 1280, 300) #sizedep
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
    ticklerCheck.img_tickactive = cv.imread('images/tickle-active.png', cv.IMREAD_GRAYSCALE)
    ticklerCheck.img_tickqavail = cv.imread('images/tickle-quest-avail.png', cv.IMREAD_GRAYSCALE)

def launchApp(grabber):
    if grabber.isRunning:
        return
    grabber.log('MAIN', 'Application not running launching...')
    os.system('explorer.exe shell:appsFolder\A278AB0D.DisneyMagicKingdoms_h6adky7gbf63m!App')
    time.sleep(60)
    # zoom out
    grabber.activate()
    grabber.moveTo(700, 300)
    grabber.scroll(-2000)

def restartAppCheck(grabber):
    # Check for exit-at
    global config
    now = datetime.datetime.now()
    if config.exit_at and now > config.exit_at:
        grabber.log('MAIN', Fore.GREEN+'Exiting due to exit-at'+Fore.WHITE)
        sys.exit(0)

    now = time.monotonic()
    if now - restartAppCheck.startTime < (3600 * 4):
        return

    restartAppCheck.startTime = now
    grabber.log('MAIN', Fore.GREEN+'Maximum run time reached, restarting'+Fore.WHITE)
    grabber.click(1410, -16) # close
    time.sleep(30)
    launchApp(grabber)

def parseExitAt(s: str) -> datetime.datetime:
    l = len(s)
    if l < 4 or l > 5:
        return None

    # hhnn or hh:nn
    h = int(s[:2])
    n = int(s[-2:])

    now = datetime.datetime.now()
    next = now.replace(hour=h, minute=n, second=0, microsecond=0)

    # if next is in the past, then we want tomorrow's
    if next < now:
        next += datetime.timedelta(days=1)

    return next

def parseCmdLine(grabber):
    import argparse
    parser = argparse.ArgumentParser(
        prog='dmk',
        description='Disney Magic Kindgoms bot'
    )
    parser.add_argument('-x', '--exit-at', type=parseExitAt,
                        help='Exit the script at this time (hhnn or hh:nn)')

    global config
    config = parser.parse_args()

    if config.exit_at:
        grabber.log('MAIN', 'Will exit-at ' + config.exit_at.strftime('%Y-%b-%d %H:%M (%a)'))

def mainLoop(grabber):
    now = time.monotonic()
    restartAppCheck.startTime = now
    doRandom.lastRun = now
    lastStandalone = now
    while True:
        didStandalone = standaloneCheck(grabber) # updates window location
        didStandalone = periodicCheck(grabber) or didStandalone
        if not didStandalone:
            didStandalone = ticklerCheck(grabber)

        now = time.monotonic()
        if didStandalone:
            lastStandalone = now

        # If no activity in X seconds, do something random
        if now - lastStandalone > 15:
           didStandalone = doRandom(grabber)

        key = cv.waitKey(500 if didStandalone else 2000)
        if key == ord('q'):
            return
        elif key == ord(' '):
            moveRandom(grabber)
        else:
            restartAppCheck(grabber)

# Setup

random.seed()

grabber = WindowGrabber('ApplicationFrameWindow', 'Disney Magic Kingdoms', (1440, 665))  # 1440x608 (1266, 911)
parseCmdLine(grabber)
launchApp(grabber)
grabber.log('MAIN', f'Window size is {grabber.width}x{grabber.height}')

#testSearch(grabber, cv.imread('actors/fred/actor.png', cv.IMREAD_GRAYSCALE))

actorsInit(grabber)
periodicInit(grabber)
tickleInit(grabber)
standaloneInit(grabber)
lookAndClickInit(grabber)

mainLoop(grabber)

cv.destroyAllWindows()

