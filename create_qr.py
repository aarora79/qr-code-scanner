import os
import re
import glob
import qrcode
import logging
import argparse
import unicodedata
import urllib.parse
import pandas as pd
import qrcode.image.svg
from typing import Dict

'''
Start with a simple console logger until we process the configuration. Then
we will reconfigure the logging as configured. This at least gives some console
logging while processing configuration.
'''

logging.basicConfig(format='%(asctime)s,%(levelname)s,%(module)s,%(message)s', level=logging.ERROR)
logger = logging.getLogger(__name__)

# global constants
APP_NAME = "create_qr"
LAMBDA_URL = "<your-lambda-function-url-here>"
QR_CODES_DIR = "qr_codes"
PARTICIPANT_LIST = "registrants.csv"

def parse_args(args):
    # create the main top-level parser
    top_parser = argparse.ArgumentParser()
    
    # Common parameters for produce and consume sub-commands
    top_parser = argparse.ArgumentParser(add_help=True)
    top_parser.add_argument(
         '--file-path',
         type=str,
         required=False,
         default=PARTICIPANT_LIST,
         help=f'Path of the filename containing participants data, default={PARTICIPANT_LIST}')
    
    top_parser.add_argument(
         '--lambda-url',
         type=str,
         default=LAMBDA_URL,
         required=False,
         help=f'URL for the Lambda function to store participant info, default={LAMBDA_URL}.')
    
    top_parser.add_argument(
         '--qr-code-dir-path',
         type=str,
         default=QR_CODES_DIR,
         required=False,
         help=f'Directory path for storing QR codes, default={QR_CODES_DIR}.')
    
    return top_parser.parse_args()

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')

def _create_qr_code(row: Dict, config: Dict):
    try:
        params = {'firstname': row['First Name'], 'lastname': row['Last Name'], 'company': row['Company'], 'title': row['Title'], 'email': row['Email'] }
        param_str = urllib.parse.urlencode(params)
        url = f"{config.lambda_url}?{param_str}"
        logger.info(url)
        participant = slugify(f"{params['firstname']}_{params['lastname']}_{params['company']}")
        logger.info(f"going to create qr code for participant {participant}")
        img = qrcode.make(url, image_factory=qrcode.image.svg.SvgImage)
        os.makedirs(config.qr_code_dir_path, exist_ok=True)
        qr_fpath = os.path.join(config.qr_code_dir_path, f"{participant}.svg")
        with open(qr_fpath, 'wb') as qr:
            logger.info(f"saving qr code for \"{participant}\" in file={qr_fpath}")
            img.save(qr)
    except Exception as e:
        logger.error(f"QR code not generated for {row}, exception={e}")
    
def main(args=None):
    """
    generate QR codes
    """
    config = parse_args(args)    
    logger.info('Starting %s', APP_NAME)
    # Dump the full config being used to the log file for reference
    logger.info(repr(config))

    df = pd.read_csv(config.file_path)
    shape_before_drop_dups = df.shape
    df = df.drop_duplicates()
    shape_after_drop_dups = df.shape
    if shape_after_drop_dups[0] < shape_before_drop_dups[0]:
        logger.error(f"the file {config.file_path} contained some {shape_before_drop_dups[0] - shape_after_drop_dups[0]} values, these were dropped")


    df.apply(_create_qr_code, axis=1, args=(config,))

    # make sure we generated as many QR codes as there are registrants..
    qr_code_files = glob.glob(os.path.join(config.qr_code_dir_path, "*.svg"))
    if len(qr_code_files) != df.shape[0]:
        logger.error(f"number of QR codes generated is {len(qr_code_files)} which is different from dataframe length {df.shape[0]}, why???")
    else:
        logger.error(f"number of QR codes generated is {len(qr_code_files)} which is same as dataframe length {df.shape[0]}, good!")


            
            
###########################################################
# MAIN
###########################################################

if __name__ == '__main__':
    main()
