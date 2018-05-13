import logging
import logging.config

from PIL import Image

from cv2 import cv2
import numpy as np
from os import listdir

logging.config.fileConfig('logging.conf')
logger = logging.getLogger('PokemonGo')

class CalcyIVButtonNotFoundError(Exception):
    pass

class Calibration(object):
    def __init__(self, debug=False):
        self.debug = debug

    def __hue_360_to_255(self, h):
        return 255.0/360*h

    def find_calcyIV_button(self, image):
        width, height = image.size

        if self.debug:
            rgb_image = image.convert('RGB')
            rgb_px = rgb_image.load()

        hsv_image = image.convert('HSV')
        hsv_px = hsv_image.load()
        h_bound1 = self.__hue_360_to_255(65)
        h_bound2 = self.__hue_360_to_255(295)
        xs = set()
        ys = set()
        for x in range(0, width):
            for y in range(0, height):
                h, s, _ = hsv_px[x, y]
                red_hue = h < h_bound1 or h > h_bound2
                white = h == 0 and s == 0
                desaturated = s < 5
                if red_hue and not white and not desaturated:
                    xs.add(x)
                    ys.add(y)
                else:
                    if self.debug:
                        rgb_px[x, y] = (0, 0, 0)

        if len(xs) == 0 or len(ys) == 0:
            raise CalcyIVButtonNotFoundError

        minX = min(xs)
        maxX = max(xs)
        minY = min(ys)
        maxY = max(ys)
        is_continuous_x_pixels = (len(xs.difference(range(minX, maxX+1))) == 0)
        is_continuous_y_pixels = (len(ys.difference(range(minY, maxY+1))) == 0)

        if is_continuous_x_pixels and is_continuous_y_pixels:
            foundX = int(float(minX+maxX)/2)
            foundY = int(float(minY+maxY)/2)
        else:
            raise CalcyIVButtonNotFoundError

        if self.debug:
            if foundX and foundY:
                for x in range(foundX - 5, foundX + 5):
                    for y in range(foundY - 5, foundY + 5):
                        rgb_px[x, y] = (0, 255, 0)
            rgb_image.show()

        return (foundX, foundY)