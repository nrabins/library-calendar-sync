from __future__ import print_function
import datetime
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import requests
from lxml import html
import json
from pathlib import Path
import logging.config
import logging
import os
import sys


SCOPES = 'https://www.googleapis.com/auth/calendar'

LOGIN_URL = 'https://polaris.plano.gov/Polaris/logon.aspx?header=1'
USERNAME_FIELD_NAME = 'ctl00$BodyMainContent$textboxBarcodeUsername'
PASSWORD_FIELD_NAME = 'ctl00$BodyMainContent$textboxPassword'
SUBMIT_BUTTON_FIELD_NAME = 'ctl00$BodyMainContent$buttonSubmit'
VIEW_STATE_NAME = "__VIEWSTATE"
VIEW_STATE_GENERATOR_NAME = "__VIEWSTATEGENERATOR"
EVENT_VALIDATION_NAME = "__EVENTVALIDATION"
ITEMS_OUT_URL = 'https://polaris.plano.gov/polaris/patronaccount/itemsout.aspx'


def setup_logging(
    default_path='logging.json',
    default_level=logging.INFO,
    evn_key='LOG_CFG'
):
    path = default_path
    value = os.getenv(evn_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

setup_logging()
logger = logging.getLogger("library-check.py")

logger.info("Activating library check")

def get_credentials():
    credentials_path = Path('user-credentials.json')
    logger.info('Looking for user credentials at ' + str(credentials_path))
    if credentials_path.is_file:
        with open(credentials_path) as f:
            credentials = json.load(f)
            logger.info('Loaded user credentials')
            return credentials
    else:
        logger.error('No user credentials file found, quitting')
        sys.exit()
    

def get_due_dates(user_credentials):
    logger.info('Getting library due dates')
    session_requests = requests.session()
    result = session_requests.get(LOGIN_URL)
    tree = html.fromstring(result.text)

    view_state = list(set(tree.xpath("//input[@name='__VIEWSTATE']/@value")))[0]
    view_state_generator = list(set(tree.xpath("//input[@name='__VIEWSTATEGENERATOR']/@value")))[0]
    event_validation = list(set(tree.xpath("//input[@name='__EVENTVALIDATION']/@value")))[0]

    # Attempt login
    payload = {
        USERNAME_FIELD_NAME: user_credentials['username'],
        PASSWORD_FIELD_NAME: user_credentials['password'],
        SUBMIT_BUTTON_FIELD_NAME: 'Log In', # We need this??
        VIEW_STATE_NAME: view_state,
        VIEW_STATE_GENERATOR_NAME: view_state_generator,
        EVENT_VALIDATION_NAME: event_validation
    }

    result = session_requests.post(
        LOGIN_URL, 
        data = payload, 
        headers = dict(referer=LOGIN_URL)
    )

    result = session_requests.get(
        ITEMS_OUT_URL
    )
    tree = html.fromstring(result.content)

    items = []

    # Get number of items and search for the zero-indexed IDs of data we need 
    rows = list(set(tree.xpath("//table[@class='patrongrid']/tr[@class='patron-account__grid-row' or @class='patron-account__grid-alternating-row']")))
    for i in range(0, len(rows)):
        item = {
            'title': list(set(tree.xpath('//*[@id="BodyMainContent_GridView1_labelTitle_' + str(i) + '"]/a')))[0].text,
            'due_date': list(set(tree.xpath('//*[@id="BodyMainContent_GridView1_labelDueDate_' + str(i) + '"]')))[0].text,
            'renewals_left': list(set(tree.xpath('//*[@id="BodyMainContent_GridView1_labelRenewalsLeft_' + str(i) + '"]')))[0].text
        }
        items.append(item)

    foo = 0
    return ['blah']

def get_calendar_service():
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    return build('calendar', 'v3', http=creds.authorize(Http()))

def main():
    user_credentials = get_credentials()

    due_dates = get_due_dates(user_credentials)

    # Remove existing events
    events_response = service.events().list(calendarId=credentials['calendarId']).execute()
    events = events_response.get('items', [])

    # for event in events:
    #     service.events().delete(calendarId=CALENDAR_ID,
    #                             eventId=event['id']).execute()

    # for due_date in due_dates:


if __name__ == '__main__':
    main()
