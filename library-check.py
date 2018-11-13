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

def get_user_credentials():
    credentials_path = Path('user-credentials.json')
    logger.info('Loading user credentials from %s ' % credentials_path)
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

    logger.info('Logging in')
    result = session_requests.post(
        LOGIN_URL, 
        data = payload, 
        headers = dict(referer=LOGIN_URL)
    )
    if result.status_code != 200:
        logger.error('Error logging in: %d - %s' % (result.status_code, result.reason))
    else:
        logger.info('Login successful')

    logger.info('Navigating to items out page')
    result = session_requests.get(
        ITEMS_OUT_URL
    )
    if result.status_code != 200:
        logger.error('Error retrieving items out page: %d - %s' % (result.status_code, result.reason))
    else:
        logger.info('Navigation successful')

    tree = html.fromstring(result.content)
    items = []

    # Get number of items and search for the zero-indexed IDs of data we need 
    rows = list(set(tree.xpath("//table[@class='patrongrid']/tr[@class='patron-account__grid-row' or @class='patron-account__grid-alternating-row']")))
    for i in range(0, len(rows)):
        title = list(set(tree.xpath('//*[@id="BodyMainContent_GridView1_labelTitle_' + str(i) + '"]/a')))[0].text
        
        date = list(set(tree.xpath('//*[@id="BodyMainContent_GridView1_labelDueDate_' + str(i) + '"]')))[0].text
        date = datetime.datetime.strptime(date, '%m/%d/%Y')
        date = date.strftime('%Y-%m-%d')

        renewals_left = list(set(tree.xpath('//*[@id="BodyMainContent_GridView1_labelRenewalsLeft_' + str(i) + '"]')))[0].text
        renewals_left = int(renewals_left)
        item = {
            'title': title,
            'date': date,
            'renewals_left': renewals_left
        }
        logger.info('Found due date: \'%s\' is due %s (%d renewals left)' % (title, date, renewals_left))
        items.append(item)
    return items

def get_calendar_service():
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    return build('calendar', 'v3', http=creds.authorize(Http()))

def main():
    user_credentials = get_user_credentials()

    due_dates = get_due_dates(user_credentials)

    service = get_calendar_service()

    # Remove existing events
    logger.info('Finding existing events')
    events_response = service.events().list(calendarId=user_credentials['calendarId']).execute()
    events = events_response.get('items', [])
    logger.info('Found %s events to remove' % len(events))
    for event in events:
        service.events().delete(calendarId=user_credentials['calendarId'], eventId=event['id']).execute()
        logger.info('Removed event with ID %s' % event['id'])        

    for due_date in due_dates:
        logger.info('Creating event for %s' % due_date['title'])
        event = {
            'summary': due_date['title'],
            'description': due_date['title'] + ' - Renewals left: ' + str(due_date['renewals_left']),
            'start': {
                'date': due_date['date'],
            },
            'end': {
                'date': due_date['date'],
            }
        }
        created_event = service.events().insert(calendarId = user_credentials['calendarId'], body=event).execute()
        logger.info('Created event: ' + created_event.get('htmlLink'))
    logger.info('Finished')

if __name__ == '__main__':
    main()
