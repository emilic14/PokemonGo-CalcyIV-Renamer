#!python

import pokemonlib
import argparse

import logging
import logging.config

logging.config.fileConfig('logging.conf')

logger = logging.getLogger('PokemonGo')

skip_count = 0

parser = argparse.ArgumentParser(description='Pokemon go renamer')
parser.add_argument('--device_id', type=str, default=None,
                    help="Optional, if not specified the phone is automatically detected. Useful only if you have multiple phones connected. Use adb devices to get a list of ids")
parser.add_argument('--adb_path', type=str, default="adb",
                    help="If adb isn't on your PATH, use this option to specify the location of adb")
parser.add_argument('--nopaste', action='store_const', const=True, default=False,
                    help="Use this switch if your device doesn't support the paste key, for example if you're using a Samsung")
parser.add_argument('--no-rename', action='store_const', const=True, default=False,
                    help="Don't rename, useful for just loading every pokemon into calcy IV history for CSV export.")
parser.add_argument('--wait-after-error', action='store_const', const=True, default=False,
                    help="Upon calcy IV error, wait for user input")
parser.add_argument('--max-retries', type=int, default=5,
                    help="Maximum retries, set to 0 for unlimited")

args = parser.parse_args()

p = pokemonlib.PokemonGo(args.device_id)

while True:
    p.click_calcyIV_button()
    try:
        p.check_calcy_iv()
        skip_count = 0
    except pokemonlib.CalcyIVError:
        logger.info("CalcyIVError")
        skip_count = skip_count + 1
        if args.wait_after_error:
            input("CalcyIVError, Press enter to continue")
        if skip_count > args.max_retries and args.max_retries != 0:
            logger.info(
                "CalcyIVError 5 times in a row, skipping to next pokemon")
            p.swipe_next()
            skip_count = 0
        continue

    if not args.no_rename:
        p.dismiss_calcyIV_overlay()
        p.click_rename_button()
        if args.nopaste:
            p.select_text_in_rename_input()
            p.click_paste_button()
        else:
            p.paste_into_rename()
        p.hide_keyboard()
        p.click_ok_on_rename_dialog()
    p.swipe_next()
