import os
import time
import datetime
import random
from windowgrabber import WindowGrabber

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

class DmkGrabber(WindowGrabber):
    _instance = None

    def __init__(self):
        random.seed()
        self.parseCmdLine()

        super().__init__('ApplicationFrameWindow', 'Disney Magic Kingdoms', (1440, 665))

    def parseCmdLine(self):
        import argparse
        parser = argparse.ArgumentParser(
            prog='dmk',
            description='Disney Magic Kindgoms bot'
        )
        parser.add_argument('-x', '--exit-at', type=parseExitAt,
                            help='Exit the script at this time (hhnn or hh:nn)')

        self.config = parser.parse_args()

        if self.config.exit_at:
            self.log('MAIN', 'Will exit-at ' + self.config.exit_at.strftime('%Y-%b-%d %H:%M (%a)'))

    def launchApp(self):
        if self.isRunning:
            self.activate(interval=0.100)
            return
        self.log('MAIN', 'Application not running launching...')
        os.system('explorer.exe shell:appsFolder\A278AB0D.DisneyMagicKingdoms_h6adky7gbf63m!App')
        time.sleep(60)
        # zoom out
        self.activate()
        self.moveTo(700, 300)
        self.scroll(-2000)
