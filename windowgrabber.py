import ctypes
from datetime import datetime
import time
import cv2 as cv
import mss
import numpy as np
import pyautogui
import pyautogui._pyautogui_win as pyagplat
import sendinput
import win32gui
import win32con
import pytesseract
from colorama import Fore, Back, Style
from imutils.object_detection import non_max_suppression

class WindowGrabber:
    def __init__(self, WndClass=None, WndTitle=None, ForceSize=None):
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        self._wnd_class = WndClass
        self._wnd_title = WndTitle
        self._force_size = ForceSize # Tuple
        self._sys_title = ctypes.windll.user32.GetSystemMetrics(31) # SM_CYSIZE
        self._sys_frame = ctypes.windll.user32.GetSystemMetrics(33) # SM_CYSIZEFRAME
        self.sct = mss.mss()
        self.wnd_place = None

    def _updateWndPlace(self, hWnd):
        self.wnd_place = win32gui.GetWindowRect(hWnd)
        self.wnd_place = (
            self.wnd_place[0] + self._sys_frame,
            self.wnd_place[1] + self._sys_frame + self._sys_title,
            self.wnd_place[2] - self._sys_frame,
            self.wnd_place[3] - self._sys_frame
        )

    def _gethWnd(self):
        hWnd = win32gui.FindWindow(self._wnd_class, self._wnd_title)
        if hWnd == 0:
            raise Exception(f'Window not found {self._wnd_class}+{self._wnd_title}')
        return hWnd

    def _updatePlace(self, Force=False):
        needPlace = self.wnd_place ==  None or Force
        if not needPlace:
            return
        hWnd = self._gethWnd()
        self._updateWndPlace(hWnd)
        if self._force_size != None \
            and (self.width != self._force_size[0] or self.height != self._force_size[1]):
            self.log('GRB', f'Resizing window to requested size from {self.width}x{self.height}')
            win32gui.SetWindowPos(hWnd, 0, 0, 0, \
                self._force_size[0] + 2*self._sys_frame, self._force_size[1] + 2*self._sys_frame + self._sys_title, \
                win32con.SWP_NOMOVE + win32con.SWP_NOZORDER)
            self._updateWndPlace(hWnd)

    def activate(self) -> None:
        win32gui.SetForegroundWindow(self._gethWnd())

    @property
    def isRunning(self) -> bool:
        try:
            self._updatePlace(True)
        except:
            return False
        return True

    def isForeground(self):
        return self._gethWnd() == win32gui.GetForegroundWindow()

    @property
    def left(self) -> int:
        self._updatePlace()
        return self.wnd_place[0]

    @property
    def top(self) -> int:
        self._updatePlace()
        return self.wnd_place[1]

    @property
    def width(self) -> int:
        self._updatePlace()
        return self.wnd_place[2] - self.wnd_place[0]

    @property
    def height(self) -> int:
        self._updatePlace()
        return self.wnd_place[3] - self.wnd_place[1]

    @property
    def bounds(self) -> tuple[int]:
        self._updatePlace()
        return self.wnd_place

    def grab(self, UpdatePlace=False, bounds=None, color=False) -> np.array:
        self._updatePlace(UpdatePlace)

        capture_rect = self.wnd_place
        if not bounds is None:
            capture_rect = (
                capture_rect[0] + bounds[0],
                capture_rect[1] + bounds[1],
                capture_rect[0] + bounds[2],
                capture_rect[1] + bounds[3]
            )

        img = np.asarray(self.sct.grab(capture_rect))
        if color:
            return img
        else:
            return cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    # grab an area and return the average color (R,G,B,255)
    def grabColor(self, bounds) -> np.array:
        needle = self.grab(bounds=bounds, color=True)
        #cv.imshow('Result', needle)
        avg = np.average(needle, axis=0)
        avg = np.average(avg, axis=0)
        return avg

    def press(self, keys):
        pyautogui.press(keys)

    def click(self, x, y, interval=0.0):
        self._updatePlace()
        pyautogui.click(x + self.wnd_place[0], y + self.wnd_place[1], interval=interval)
        # self.mouseDown(x, y)
        # time.sleep(0.033)
        # self.mouseUp(x, y)
        # time.sleep(interval)

    def scroll(self, amt, x=None, y=None):
        if not (x is None or y is None):
            self.moveTo(x, y)
        # negative for down
        pyautogui.scroll(amt)

    def moveTo(self, x, y, duration=0.0):
        self._updatePlace()
        pyautogui.moveTo(x + self.wnd_place[0], y + self.wnd_place[1], duration)
        #evt = pyagplat.MOUSEEVENTF_MOVE + pyagplat.MOUSEEVENTF_ABSOLUTE
        #pyagplat._sendMouseEvent(evt, x + self.wnd_place[0], y + self.wnd_place[1])
        #evt = pyagplat.MOUSEEVENTF_MOVE
        #pyagplat._sendMouseEvent(evt, x, y)
        #sendinput.mouseMove(x, y)
        #sendinput._sendMouseEvent(0, 0, sendinput.MOUSEEVENTF_LEFTDOWN)
        #sendinput._sendMouseEvent(200, 200, sendinput.MOUSEEVENTF_MOVE)
        #sendinput._sendMouseEvent(0, 0, sendinput.MOUSEEVENTF_LEFTUP)

    def mouseDown(self, x, y):
        self._updatePlace()
        pyautogui.mouseDown(x + self.wnd_place[0], y + self.wnd_place[1])

    def mouseUp(self, x, y):
        self._updatePlace()
        pyautogui.mouseUp(x + self.wnd_place[0], y + self.wnd_place[1])

    def dragTo(self, x, y, duration=0.0):
        self._updatePlace()
        pyautogui.dragTo(x + self.wnd_place[0], y + self.wnd_place[1], duration)

    def windowDrag(self, startPos: tuple, dirVector: tuple, cnt: int):
        self.mouseDown(*startPos)
        time.sleep(0.067)

        for i in range(cnt):
            sendinput._sendMouseEvent(*dirVector, sendinput.MOUSEEVENTF_MOVE) # relative move
            time.sleep(0.034)
        sendinput._sendMouseEvent(0, 0, sendinput.MOUSEEVENTF_LEFTUP)
        time.sleep(0.067)

    def search(self, haystack, needle, mode=cv.TM_CCOEFF_NORMED, returnCenter=False):
        match = cv.matchTemplate(haystack, needle, mode)
        _, maxval, _, maxloc = cv.minMaxLoc(match)

        if returnCenter:
            img_center = (needle.shape[1] // 2, needle.shape[0] // 2)
            maxloc = (maxloc[0] + img_center[0], maxloc[1] + img_center[1])

        return match, maxval, maxloc

    def searchAll(self, haystack, needle, threshold:float, mode=cv.TM_CCOEFF_NORMED, returnCenter=False):
        # Return an array of non-overlapping rects where the needle was found
        match = cv.matchTemplate(haystack, needle, mode)
        # Find all matching positions
        (yCoords, xCoords) = np.where(match >= threshold)

        # Generate rects for each position
        rects = []
        (tH, tW) = needle.shape[:2]
        for (x, y) in zip(xCoords, yCoords):
            #print(f'({x}, {y}) = {match[y][x]}')
            rects.append((x, y, x + tW, y + tH))

        # find non overlapping positions
        pick = non_max_suppression(np.array(rects))
        if returnCenter:
            pick = map(lambda r: ((r[0] + r[2]) // 2, (r[1] + r[3]) // 2),  pick)
        else:
            pick = map(lambda r: (r[0], r[1]), pick)
        return list(pick)

    def log(self, facil, msg):
        t = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f'{Style.BRIGHT}{t}{Style.NORMAL} [{Style.DIM}{facil}{Style.NORMAL}] {msg}')

    def image_to_string(self, img) -> str:
        return pytesseract.image_to_string(img)
