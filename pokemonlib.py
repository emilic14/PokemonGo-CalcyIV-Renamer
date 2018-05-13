import sys
import time
import argparse
import subprocess
import configparser
import logging
from enum import Enum, auto
from PIL import Image
from io import BytesIO
import calibration

logger = logging.getLogger('PokemonGo')


class CalcyIVError(Exception):
    pass


class PhoneNotConnectedError(Exception):
    pass


class RenameButtonNotFoundError(Exception):
    pass


class CalcyIVStatus(Enum):
    # CalcyIV overlay found
    OK = auto()
    # CalcyIV error found
    KO = auto()
    # CalcyIV overlay NOT found
    NOTHING = auto()


class PokemonGo(object):
    __check_calcy_iv_retries = 3

    def __init__(self, device_id):
        devices = self.__get_devices()
        if devices == [] or (device_id is not None and device_id not in devices):
            raise PhoneNotConnectedError
        if device_id is None:
            self.device_id = devices[0]
        else:
            self.device_id = device_id

        self.__load_config()

        self.use_fallback_screenshots = False

        self.__auto_config()

    def __load_config(self):
        self.__config = configparser.ConfigParser()
        self.__config.read(['config_default.ini', 'config.ini'])

        if not self.__config.has_section(self.device_id):
            self.__config.add_section(self.device_id)
            self.__write_config()
            self.__load_config()
        else:
            self.config = self.__config[self.device_id]

    def __write_config(self):
        with open('config.ini', 'w') as config_file:
            self.__config.write(config_file)

    def __auto_config(self):
        self.screencap()
        try:
            self.__find_rename_button_y()
        except RenameButtonNotFoundError:
            sys.exit(
                "Couldn't find rename button. Are you on a pokemon detail screen?")
        self.click_rename_button()
        self.hide_keyboard()
        self.screencap()
        self.__find_calcyIV_button()
        self.__dismiss_rename_dialog()

    def __find_calcyIV_button(self):
        try:
            calcyIV_button_coords = calibration.Calibration().find_calcyIV_button(self.image)
        except calibration.CalcyIVButtonNotFoundError:
            sys.exit(
                "Couldn't find CalcyIV button. Have you launched CalcyIV?")
        self.calcyIV_button_coords = calcyIV_button_coords
        logger.info('Found CalcyIV button {}'.format(
            self.calcyIV_button_coords))

    def __adb(self, args):
        start = time.time()
        p = subprocess.Popen([str(arg)
                              for arg in args], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        logger.debug("Run (%d - %fs): %s", p.returncode,
                     time.time() - start, args)
        return (p.returncode, stdout, stderr)

    def screencap(self):
        if not self.use_fallback_screenshots:
            _, stdout, _ = self.__adb(
                ["adb", "-s", self.device_id, "exec-out", "screencap", "-p"])
            try:
                image = Image.open(BytesIO(stdout))
            except OSError as err:
                logger.debug(
                    "Screenshot failed, using fallback method: %s", err)
                self.use_fallback_screenshots = True
        if self.use_fallback_screenshots:
            self.__adb(["adb", "-s", self.device_id, "shell",
                        "screencap", "-p", "/sdcard/screen.png"])
            self.__adb(["adb", "-s", self.device_id,
                        "pull", "/sdcard/screen.png", "."])
            image = Image.open("screen.png")

        self.image = image
        return image

    def get_x(self, percent):
        width, _ = self.image.size
        return int((width / 100.0) * percent)

    def get_y(self, percent):
        _, height = self.image.size
        return int((height / 100.0) * percent)

    def click_calcyIV_button(self):
        logger.info("Click CalcyIV button")
        x, y = self.calcyIV_button_coords
        self.__tap(x, y, self.config.getfloat('SleepLong'))

    def dismiss_calcyIV_overlay(self):
        logger.info("Dismiss CalcyIV overlay")
        self.__tap(self.get_x(50), self.get_y(70))

    def click_rename_button(self):
        logger.info("Click rename button")
        renameButtonX = self.__find_rename_button_x()
        self.__tap(
            renameButtonX,
            self.__renameButtonY,
            self.config.getfloat('SleepShort')
        )

    def click_paste_button(self):
        logger.info("Click paste button")
        self.__tap(
            self.get_x(self.config.getfloat('PasteButtonX')),
            self.get_y(self.config.getfloat('PasteButtonY')),
            self.config.getfloat('SleepShort')
        )

    def paste_into_rename(self):
        logger.info("Paste into rename")
        self.__key(279)

    def hide_keyboard(self):
        logger.info("Hide keyboard")
        self.__tap(self.get_x(50), self.get_y(10))

    def __dismiss_rename_dialog(self):
        logger.info("Dismiss rename dialog")
        self.__tap(self.get_x(50), self.get_y(10))

    def click_ok_on_rename_dialog(self):
        logger.info("Click OK on rename dialog")
        self.__tap(
            self.get_x(50),
            self.get_y(51.35),
            self.config.getfloat('SleepLong')
        )

    def __tap(self, x, y, sleep=0):
        self.__adb(["adb", "-s", self.device_id,
                    "shell", "input", "tap", x, y])
        time.sleep(sleep)

    def __key(self, key, sleep=0):
        self.__adb(["adb", "-s", self.device_id,
                    "shell", "input", "keyevent", key])
        time.sleep(sleep)

    def swipe_next(self):
        logger.info("Swipe to next pokemon")
        self.__swipe(90, 70, 10, 70, 0)

    def select_text_in_rename_input(self):
        logger.info("Select text in rename input")
        # Use swipe to simulate a long press to bring up copy/paste dialog
        x = self.config.getfloat('EditLineX')
        y = self.config.getfloat('EditLineY')
        self.__swipe(x, y, x, y, self.config.getfloat('SleepShort'), 600)

    def swipe(self, x1, y1, x2, y2, sleep, duration=None):
        self.__swipe(x1, y1, x2, y2, sleep, duration)

    def __swipe(self, x1, y1, x2, y2, sleep, duration=None):
        args = [
            "adb",
            "-s",
            self.device_id,
            "shell",
            "input",
            "swipe",
            self.get_x(x1),
            self.get_y(y1),
            self.get_x(x2),
            self.get_y(y2)
        ]
        if duration:
            args.append(duration)
        self.__adb(args)
        time.sleep(sleep)

    def __find_line_with_enough_pixels_of_color(self, rgb_image, color_to_match, nb_matching_pixels_threshold, bounds=(0, 1, 0, 1)):
        width, height = rgb_image.size

        minX = int(bounds[0] * width)
        maxX = int(bounds[1] * width)
        minY = int(bounds[2] * height)
        maxY = int(bounds[3] * height)
        for y in range(minY, maxY):
            nb_matching_pixels = 0
            for x in range(minX, maxX):
                pixel = rgb_image.getpixel((x, y))
                nb_matching_pixels += 1 if pixel == color_to_match else 0
                if nb_matching_pixels > nb_matching_pixels_threshold:
                    return y
        return None

    def __check_calcy_iv_img(self, rgb_image):
        width, _ = rgb_image.size

        # Color (grey-blue) of the CalcyIV overlay border
        calcyIV_overlay_border_color = (68, 105, 108)
        # Threshold over which the number of matching pixels in one line is considered as the CalcyIV overlay bottom border
        nb_matching_pixels_threshold = 0.50 * width

        bounds = (
            # Do not scan from the first pixel on the left (perf improvement)
            .20,
            # Do not scan to the last pixel on the right (perf improvement)
            .80,
            # Do not scan up to the top (perf improvement)
            .78,
            # Start from 90% of the screen height (bypasses first lines from the bottom)
            .90
        )

        if self.__find_line_with_enough_pixels_of_color(
            rgb_image,
            calcyIV_overlay_border_color,
            nb_matching_pixels_threshold,
            bounds
        ):
            return CalcyIVStatus.OK

        # Color (grey) of the CalcyIV error overlay
        calcyIV_error_overlay_color = (132, 132, 132)
        if self.__find_line_with_enough_pixels_of_color(
            rgb_image,
            calcyIV_error_overlay_color,
            nb_matching_pixels_threshold,
            bounds
        ):
            return CalcyIVStatus.KO

        return CalcyIVStatus.NOTHING

    def check_calcy_iv(self):
        retries = self.__check_calcy_iv_retries
        calcyIV_status = CalcyIVStatus.NOTHING
        while retries > 0 and calcyIV_status == CalcyIVStatus.NOTHING:
            rgb_image = self.screencap().convert('RGB')
            calcyIV_status = self.__check_calcy_iv_img(rgb_image)
        if calcyIV_status is not CalcyIVStatus.OK:
            raise CalcyIVError

    def __find_rename_button_y(self):
        try:
            # Try to find the rename button on the previous screenshot (before CalcyIV overlay dismiss)
            # Depending on the phone resolution and overlay height, the rename button could be found (or hidden by the overlay)
            self.__do_find_rename_button_y()
        except RenameButtonNotFoundError:
            # Re-try with a new screenshot (after CalcyIV overlay dismiss)
            self.screencap()
            self.__do_find_rename_button_y()

    def __do_find_rename_button_y(self):
        y = self.__find_line_with_enough_pixels_of_color(
            self.image.convert('RGB'),
            (217, 217, 217),
            4,
            (.50, .90, .20, .50)
        )
        if y == None:
            raise RenameButtonNotFoundError
        self.__renameButtonY = y
        logger.info('Found rename button Y coordinate: {}'.format(
            self.__renameButtonY))

    def __find_rename_button_x(self):
        try:
            # Try to find the rename button on the previous screenshot (before CalcyIV overlay dismiss)
            # Depending on the phone resolution and overlay height, the rename button could be found (or hidden by the overlay)
            return self.__do_find_rename_button_x()
        except RenameButtonNotFoundError:
            # Re-try with a new screenshot (after CalcyIV overlay dismiss)
            self.screencap()
            return self.__do_find_rename_button_x()

    def __do_find_rename_button_x(self):
        rgb_image = self.image.convert('RGB')
        y = self.__renameButtonY
        xMax = self.get_x(90)
        xMin = self.get_x(55)
        search_color = (217, 217, 217)
        for x in range(xMax, xMin, -1):
            img_rgb = rgb_image.getpixel((x, y))
            if img_rgb == search_color:
                logger.debug("Rename button X: %d", x)
                return x
        raise RenameButtonNotFoundError

    def __get_devices(self):
        _, stdout, _ = self.__adb(["adb", "devices"])
        devices = []
        for line in stdout.decode('utf-8').splitlines()[1:-1]:
            device_id, _ = line.split('\t')
            devices.append(device_id)
        return devices
