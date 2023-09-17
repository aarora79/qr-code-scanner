#!/usr/bin/env python3
"""
Implement a simple HTML form in a Lambda wherein we show the details provided
in the query string in the main page and then based on the submit button action
show a details submitted page.

The pages are stored in html files and contain some template text that is replaced
based on user input (can be done better using Jinja2).
"""
import os
import time
import json
import boto3
import logging
import traceback
from typing import Dict
from pathlib import Path
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def _write_to_s3(content: Dict) -> None:
    """
    Converts the input dictionary to a string and then write
    it to a file in s3. The path follows the usual best practices
    format of partitioning by year/month/day.
    """
    string = json.dumps(content, indent=2)
    encoded_string = string.encode("utf-8")

    bucket_name = os.environ.get('BUCKET')
    file_name = f"{content['firstname']}_{content['lastname']}_{content['company']}_{int(time.time())}.json"
    t = datetime.utcnow()
    s3_path = os.path.join("participants", f"yyyy={t.year}", f"mm={t.month:02}", f"dd={t.day:02}", f"hh={t.hour:02}", file_name)
    logger.info(f"going to write {encoded_string} to bucket={bucket_name}, path={s3_path}")
    s3 = boto3.resource("s3")
    s3.Bucket(bucket_name).put_object(Key=s3_path, Body=encoded_string)
  
def handler(event, context):
  """
  handle an event: either a QR code being scanned or input details being submitted
  """
  try:
    # get the query string parameters, if it has a param called 'source'
    # then it is a form being submitted so execute that code, otherwise 
    # execute the code that shows the participant details and edit box for
    # additional details being input.
    params = event['queryStringParameters']
    source = params.get("source") 
    logger.info(f"source={source}")
    participant = dict(firstname=params['firstname'],
                       lastname=params['lastname'],
                       company=params['company'],
                       title=params['title'],
                       email=params['email'])
                       
    if source is not None:
      logger.info(f"going to write data to S3")
      # we could have done this replacement through {} but that interfered
      # with the css in the html, did not work, so had to do this in the substring
      # replacement way
      body = Path("submit.html").read_text().replace("__PARTICIPANT__", json.dumps(params, indent=2))
      # write to s3
      _write_to_s3(params | dict(timestamp_utc=str(datetime.utcnow())))
    else:
      logger.info(f"going to read data from QR code")
      body = Path("scanner.html").read_text().replace("__PARTICIPANT__", json.dumps(participant, indent=2))
      for k in participant.keys():
        v = participant[k]
        body = body.replace(f"__{k.upper()}__", v)

    return dict(statusCode=200,
                body=body,
                headers={"content-type": "text/html"})
    
  except Exception as e:
    logger.error(e)
    traceback.print_exc()
  return dict(statusCode=500, body=str(e))

