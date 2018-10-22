from __future__ import print_function
import datetime
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import requests
from lxml import html
import json
from pathlib import Path


SCOPES = 'https://www.googleapis.com/auth/calendar'
CALENDAR_ID = ''

LOGIN_URL = 'https://polaris.plano.gov/Polaris/logon.aspx?header=1'
USERNAME_FIELD_NAME = 'ctl00$BodyMainContent$textboxBarcodeUsername'
PASSWORD_FIELD_NAME = 'ctl00$BodyMainContent$textboxPassword'
SUBMIT_BUTTON_FIELD_NAME = 'ctl00$BodyMainContent$buttonSubmit'
VIEW_STATE_NAME = "__VIEWSTATE"
VIEW_STATE_GENERATOR_NAME = "__VIEWSTATEGENERATOR"
EVENT_VALIDATION_NAME = "__EVENTVALIDATION"
ITEMS_OUT_URL = 'https://polaris.plano.gov/polaris/patronaccount/itemsout.aspx'

def load_credentials():
    credentials_path = Path('library-credentials.json')
    if credentials_path.is_file:
        with open(credentials_path) as f:
            credentials = json.load(f)
        return credentials
    elif:
        # TODO log error, quit program?
    

def get_due_dates():
    session_requests = requests.session()
    result = session_requests.get(LOGIN_URL)
    tree = html.fromstring(result.text)

    view_state = list(set(tree.xpath("//input[@name='__VIEWSTATE']/@value")))[0]
    view_state_generator = list(set(tree.xpath("//input[@name='__VIEWSTATEGENERATOR']/@value")))[0]
    event_validation = list(set(tree.xpath("//input[@name='__EVENTVALIDATION']/@value")))[0]

    # Attempt login
    payload = {
        USERNAME_FIELD_NAME: credentials['username'],
        PASSWORD_FIELD_NAME: credentials['password'],
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

    foo = 3
    return ['blah']

def get_calendar_service():
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    return build('calendar', 'v3', http=creds.authorize(Http()))

def main():
    credentials = load_credentials()

    due_dates = get_due_dates()

    # Remove existing events
    events_response = service.events().list(calendarId=credentials['calendarId']).execute()
    events = events_response.get('items', [])

    # for event in events:
    #     service.events().delete(calendarId=CALENDAR_ID,
    #                             eventId=event['id']).execute()

    # for due_date in due_dates:


if __name__ == '__main__':
    main()
