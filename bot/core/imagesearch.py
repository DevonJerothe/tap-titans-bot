import numpy as np
import random
import cv2


def image_search_area(
    window,
    image,
    x1,
    y1,
    x2,
    y2,
    precision=0.8,
    im=None,
):
    """
    Searches for an image within an area
    """
    if im is None:
        im = window.screenshot(region=(x1, y1, x2, y2))

    img_rgb = np.array(im)
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)

    if isinstance(image, str):
        template = cv2.imread(image, 0)
    else:
        template = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val < precision:
        return [-1, -1]
    return max_loc


def click_image(
    window,
    image,
    position,
    button,
    clicks=1,
    interval=0.0,
    offset=5,
    pause=0,
):
    """
    Click on the center of an image with a bit of randomness.
    """
    img = cv2.imread(image)
    height, width, channels = img.shape

    point = int(position[0] + r(width / 2, offset)), int(position[1] + r(height / 2, offset))
    window.click(point=point, clicks=clicks, interval=interval, button=button, offset=offset, pause=pause)


def r(num, rand):
    return num + rand * random.random()
