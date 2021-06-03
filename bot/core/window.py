from bot.core.exceptions import (
    WindowNotFoundError,
    StoppedException,
)

from PIL import Image
from ctypes import windll

from threading import Lock
from enum import Enum

import win32gui
import win32ui
import win32api
import win32con

import pyautogui
import random
import time
import math


_screenshot_lock = Lock()


class Window(object):
    """
    Window objects encapsulate all of the functionality that handles background window screenshots, clicks, drags.
    """
    FORM_CLASS = "Qt5QWindowToolSaveBits"

    class ClickEvent(Enum):
        left = [
            win32con.WM_LBUTTONDOWN,
            win32con.WM_LBUTTONUP,
        ]
        right = [
            win32con.WM_RBUTTONDOWN,
            win32con.WM_RBUTTONUP,
        ]
        middle = [
            win32con.WM_MBUTTONDOWN,
            win32con.WM_MBUTTONUP,
        ]

    # Local references to the win32con library constants
    # that are used by the windows object.
    class Event(Enum):
        MOUSE_MOVE = win32con.WM_MOUSEMOVE

    def __init__(
        self,
        hwnd,
    ):
        """
        Initialize a new window object with the specified hwnd value.
        """
        self.get_persistence = None
        self.force_stop_func = None
        # Hard code/set these to handle some additional work
        # done while taking screenshots and calculating points...
        self.emulator_width = 480
        self.emulator_height = 800
        # "hwnd" is used throughout to send signals
        # to the window in question...
        self.hwnd = int(hwnd)

    def configure(
        self,
        instance,
        get_persistence,
        force_stop_func,
    ):
        """
        Configure the given window, ensuring the expected settings are included.
        """
        self.instance = instance
        self.get_persistence = get_persistence
        self.force_stop_func = force_stop_func
        self.form = Window(win32gui.FindWindowEx(None, win32gui.FindWindowEx(None, None, self.FORM_CLASS, None), self.FORM_CLASS, None))

    def __str__(self):
        return "%(text)s (X: %(x)s, Y: %(y)s, W: %(w)s, H: %(h)s)" % {
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "w": self.width,
            "h": self.height,
        }

    @property
    def text(self):
        """
        Retrieve the text (title) value for the window.
        """
        return win32gui.GetWindowText(self.hwnd)

    @property
    def rectangle(self):
        """
        Retrieve the client rectangle for the window.
        """
        return win32gui.GetWindowRect(self.hwnd)

    @property
    def x(self):
        """
        Retrieve the x value for the window.
        """
        return self.rectangle[0]

    @property
    def y(self):
        """
        Retrieve the y value for the window.
        """
        return self.rectangle[1]

    @property
    def width(self):
        """
        Retrieve the width for the window.
        """
        return self.rectangle[2] - self.x

    @property
    def height(self):
        """
        Retrieve the height for the window.
        """
        return self.rectangle[3] - self.y

    @property
    def y_padding(self):
        """
        Retrieve the amount of y padding for the window.
        """
        return self.height - self.emulator_height

    @staticmethod
    def _gen_offset(point, amount):
        """
        Generate an offset on the given point specified (x, y).
        """
        if not amount:
            # Maybe the amount specified is just 0,
            # return the original point.
            return point

        # Modify our points to use a random value between
        # the original value with amount offset.
        return (
            point[0] + random.randint(-amount, amount),
            point[1] + random.randint(-amount, amount)
        )

    def _failsafe(self):
        """
        Perform the proper failsafe check here (if enabled).
        """
        if self.get_persistence("enable_failsafe"):
            pyautogui.failSafeCheck()

    def _force_stop(self):
        """
        Perform the proper force stop check here (if enabled).
        """
        if self.force_stop_func(instance=self.instance):
            self.force_stop_func(instance=self.instance, _set=True)
            raise StoppedException

    def search(self, value):
        """
        Perform a check to see if a specified value is present within the windows text value.
        """
        if isinstance(value, str):
            value = [value]
        else:
            value = [v for v in value]

        for val in value:
            # Use "lower" so that we don't deal with casing
            # issues when searching for possible emulators.
            if self.text.lower().find(val.lower()) != -1:
                return True

        return False

    def click(self, point, clicks=1, interval=0.0, button="left", offset=5, pause=0.0):
        """
        Perform a click on the window in the background.
        """
        self._failsafe()
        self._force_stop()

        _point = self._gen_offset(point=point, amount=offset)
        _parameter = win32api.MAKELONG(point[0], point[1] + self.y_padding)

        for _ in range(clicks):
            win32api.SendMessage(self.hwnd, self.ClickEvent[button].value[0], 1, _parameter)
            win32api.SendMessage(self.hwnd, self.ClickEvent[button].value[1], 0, _parameter)

            if interval:
                time.sleep(interval)
        if pause:
            time.sleep(pause)

    def drag(self, start, end, button="left", pause=0.0):
        """
        Perform a drag on this window in the background.
        """
        self._failsafe()
        self._force_stop()

        _parameter_start = win32api.MAKELONG(start[0], start[1] + self.y_padding)
        _parameter_end = win32api.MAKELONG(end[0], end[1] + self.y_padding)

        # Moving the mouse to the starting position for the duration of our
        # mouse dragging, button is DOWN after this point.
        win32api.SendMessage(self.hwnd, self.ClickEvent[button].value[0], 1, _parameter_start)

        # Determine which direction our mouse dragging will go,
        # we can go up or down easily, left and right may cause issues.
        direction = start[1] > end[1]
        clicks = start[1] - end[1] if direction else end[1] - start[1]

        time.sleep(0.05)

        for i in range(clicks):
            _parameter = win32api.MAKELONG(start[0], start[1] - i if direction else start[1] + i)

            # Send another message to drag the mouse down start[1] +/- i.
            win32api.SendMessage(self.hwnd, self.Event.MOUSE_MOVE.value, 1, _parameter)
            time.sleep(0.001)

        time.sleep(0.1)
        win32api.SendMessage(self.hwnd, self.Event.MOUSE_MOVE.value, 0, _parameter_end)

        if pause:
            time.sleep(pause)

    def drag_circle(self, radius, button="left", offset=5, loops=5, scale=0.7, interval=0.0001, pause=0.0):
        """
        Perform a circular drag on this window in the background.

        Loops can be specified to determine how many circles should be dragged, the scale
        amount is used to shrink or grow the circle with each subsequent loop.
        """
        self._failsafe()
        self._force_stop()
        # Grab our initial point.
        # This is hardcoded since we always expect
        # our window to be the correct size.
        x, y = (
            int(self.emulator_width / 2),
            int(self.emulator_height / 2 + 40),
        )

        _parameter_initial = win32api.MAKELONG(x, y + self.y_padding)
        _parameter = None

        # Move the mouse to our starting position for the duration
        # of mouse dragging, the button is DOWN after this point.
        win32api.SendMessage(self.hwnd, self.ClickEvent[button].value[0], 1, _parameter_initial)

        for loop in range(loops):
            if loop != 0:
                # Grow/shrink our radius for each subsequent loop after
                # the initial drag.
                radius = radius * scale

            for i in range(360):
                if i % 3 == 0:
                    continue
                if i % 100 == 0:
                    self._failsafe()
                    self._force_stop()
                _parameter = win32api.MAKELONG(
                    int(x + radius * math.cos(math.radians(i))) + random.randint(-offset, offset),
                    int(y + radius * math.sin(math.radians(i))) + random.randint(-offset, offset),
                )
                win32api.SendMessage(self.hwnd, self.Event.MOUSE_MOVE.value, 1, _parameter)
                time.sleep(interval)

            # Ensure we emulate the action of letting go of the mouse.
            # Since we've been dragging this entire time.
            win32api.SendMessage(self.hwnd, self.Event.MOUSE_MOVE.value, 0, _parameter)
            win32api.SendMessage(self.hwnd, self.ClickEvent[button].value[0], 0, _parameter)

        if pause:
            time.sleep(pause)

    def screenshot(self, region=None):
        """
        Perform a screenshot on this window or region within, ignoring any windows in front of the window.
        """
        with _screenshot_lock:
            hwnd_dc = win32gui.GetWindowDC(self.hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()

            save_bitmap = win32ui.CreateBitmap()
            save_bitmap.CreateCompatibleBitmap(mfc_dc, self.width, self.height)

            save_dc.SelectObject(save_bitmap)

            # Store the actual screenshot result here through
            # the use of the windll object.
            windll.user32.PrintWindow(self.hwnd, save_dc.GetSafeHdc(), 0)

            bmp_info = save_bitmap.GetInfo()
            bmp_str = save_bitmap.GetBitmapBits(True)

            # Store the actual Image object retrieved from our windows calls
            # in this variable.
            image = Image.frombuffer("RGB", (bmp_info["bmWidth"], bmp_info["bmHeight"]), bmp_str, "raw", "BGRX", 0, 1)

            # Cleanup any dc objects that are currently in use.
            # This also makes sure when we come back, nothing is in use.
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()

            win32gui.ReleaseDC(self.hwnd, hwnd_dc)
            win32gui.DeleteObject(save_bitmap.GetHandle())

            # Ensure we also remove any un-needed image data, we only
            # want the in game screen, which should be the proper emulator height and width.
            image = image.crop(box=(
                0,
                self.y_padding,
                self.width,
                self.height,
            ))

            # If a region has been specified as well, we should crop the image to meet our
            # region bbox specified, regions should already take into account our expected y padding.
            if region:
                image = image.crop(box=region)

            # Image has been collected, parsed, and cropped.
            # Return the image now, exiting will release our lock.
            return image


class WindowHandler(object):
    """
    Window handler object can encapsulate all of the functionality used to gran and store references to windows.
    """
    DEFAULT_IGNORE_SMALLER = (
        380,
        700,
    )

    def __init__(self):
        """
        Initialize handler and create empty dictionary of available windows.
        """
        self._windows = {}
        self.enumerate()

    def _callback(self, hwnd, extra):
        """
        Callback handler used when windows are enumerated.
        """
        # Make sure out hwnd is coerced into a string
        # so that we can go to and from windows with
        # a single data source for the keys.
        hwnd = str(hwnd)

        if hwnd in self._windows:
            # Hwnd is already present, not totally likely
            # but better to avoid duplicate keys or overwriting.
            pass

        # Hwnd found is not yet present in the dictionary containing
        # all window instances. Add it now.
        self._windows[hwnd] = Window(hwnd=hwnd)

    def enumerate(self):
        """
        Begin enumerating windows and generate window objects if not present in windows dictionary yet.
        """
        win32gui.EnumWindows(self._callback, None)

    def filter(
        self,
        filter_title=None,
        ignore_hidden=True,
        ignore_smaller=DEFAULT_IGNORE_SMALLER,
    ):
        """
        Filter all currently available windows to ones that meet the specified criteria.
        """
        if filter_title:
            _dct = {
                hwnd: window for hwnd, window in self._windows.items() if window.search(value=filter_title)
            }
        else:
            _dct = self._windows

        if ignore_hidden:
            if _dct:
                _dct = {
                    hwnd: window for hwnd, window in _dct.items() if (
                        window.width != 0
                        and window.height != 0
                    )
                }
        if ignore_smaller:
            if _dct:
                _dct = {
                    hwnd: window for hwnd, window in _dct.items() if (
                        window.width > ignore_smaller[0]
                        and window.height > ignore_smaller[1]
                    )
                }
        if _dct:
            return _dct.values()

    def filter_first(self, filter_title):
        """
        Filter the first available window with the specified title.
        """
        window = next(iter(self.filter(
            filter_title=filter_title,
        )))
        if not window:
            raise WindowNotFoundError
        return window
