import argparse
import json
import os
import requests
import traceback

from datetime import datetime
from typing import Any

import pytz

from google.oauth2 import service_account
from google.auth.transport.requests import Request
from tenacity import retry, stop_after_attempt, wait_exponential

from credentials import FRESHSALES_TOKEN, FRESHSALES_DOMAIN, CALENDAR_ID_UTRECHT, CALENDAR_ID_ROTTERDAM

GOOGLE_TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
TIMESTAMP_WITHOUT_TIMEZONE = GOOGLE_TIMESTAMP_FORMAT.replace('%z', '')
AMSTERDAM_TIMEZONE = pytz.timezone('Europe/Amsterdam')
PARENT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(PARENT_DIR, 'upc-google-service-account.json')
VERBOSE_LOGGING = os.getenv('VERBOSE_LOGGING', 'False').lower() == 'true'
DEAL_LOST_STAGE = 31000967492

# Global variable to store credentials
credentials = None

def get_google_access_token():
    global credentials
    if credentials is None:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/calendar'],
            # impersonate urban klik user to send emails from this email address
            subject='info@urbanklik.com'
        )

    if credentials.token is None or not credentials.valid:
        if VERBOSE_LOGGING:
            print('Refreshing Google access token')
        credentials.refresh(Request())
    return credentials.token


def make_request_ignore_errors(url, method='GET', headers=None, data=None, params=None):
    try:
        return make_request(url, method=method, headers=headers, data=data, params=params)
    except Exception:
        return {}


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
def make_request(url, method='GET', headers=None, data=None, params=None):
    response = requests.request(method=method, url=url, headers=headers, data=data, params=params)
    try:
        response.raise_for_status()
    except Exception as e:
        if VERBOSE_LOGGING:
            print(f'Request to {url} failed with exception: {e}')
            print(response.status_code)
            print(response.text)
        raise e
    return response.json()


def get_freshsales_deals(api_key: str, domain: str) -> list[dict[str, Any]]:
    """
    Fetches all deals from Freshsales within the main sales view.
    Uses pagination.
    """
    deals = []
    page = 1
    page_size = 100
    url = f'https://{domain}/api/deals/view/31007998271?per_page={page_size}'
    headers = {
        'Authorization': f'Token token={api_key}',
        'Content-Type': 'application/json'
    }

    done_fetching = False
    while not done_fetching:
        page_url = f'{url}&page={page}'
        if VERBOSE_LOGGING:
            print(f'GET {page_url}')
        data = make_request(page_url, headers=headers)
        max_page = data['meta']['total_pages'] if data.get('meta', {}).get('total_pages') else 1
        done_fetching = page >= max_page
        deals.extend(data['deals'])
        page += 1

    return deals


def get_google_calendar_event(event_id: int, calendar_id: str) -> dict[str, Any]:
    """
    Fetches the Google Calendar event by ID
    """
    access_token = get_google_access_token()
    url = f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    return make_request(url, headers=headers)


def update_google_calendar_event(event_id: str, event_data: dict[str, Any], calendar_id: str) -> None:
    access_token = get_google_access_token()
    url = f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}?sendUpdates=all'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    make_request_ignore_errors(url, method='PATCH', headers=headers, data=json.dumps(event_data))


def delete_google_calendar_event(event_id: str, calendar_id: str) -> None:
    access_token = get_google_access_token()
    url = f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    try:
        make_request(url, method='DELETE', headers=headers)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404 or e.response.status_code == 410:
            if VERBOSE_LOGGING:
                print(f'Calendar event {event_id} not found, skipping delete\n')
            return
        raise e


def extract_fields_from_deal(deal: dict[str, Any]) -> tuple[datetime, datetime, str]:
    """
    Returns the start and end datetime of the deal and the Google Calendar event ID

    If there's no date, starting time, or end time, returns None for all fields,
    there's no point in syncing the deal with the calendar in this case.
    """
    date_str_raw = deal['custom_field']['cf_date']
    date_str = date_str_raw.split('T')[0] if 'T' in date_str_raw else date_str_raw

    starting_time = deal['custom_field']['cf_starting_time']
    end_time = deal['custom_field']['cf_end_time']
    calendar_event_id = deal['custom_field']['cf_google_calendar_id']

    if not date_str or not starting_time or not end_time:
        return None, None, calendar_event_id

    deal_start_str = f'{date_str}T{starting_time}:00'
    deal_start = datetime.strptime(deal_start_str, TIMESTAMP_WITHOUT_TIMEZONE)
    deal_start = AMSTERDAM_TIMEZONE.localize(deal_start)

    deal_end_str = f'{date_str}T{end_time}:00'
    deal_end = datetime.strptime(deal_end_str, TIMESTAMP_WITHOUT_TIMEZONE)
    deal_end = AMSTERDAM_TIMEZONE.localize(deal_end)

    return deal_start, deal_end, calendar_event_id


def should_update_calendar_event(
        deal_start: datetime,
        event_start: datetime,
        deal_end: datetime,
        event_end: datetime
) -> bool:
    """
    Compare the deal & calendar start & end datetimes
    """
    needs_update = deal_start != event_start or deal_end != event_end
    return needs_update


def check_broken_endtime(start: datetime, end: datetime) -> datetime:
    """
    If the end time is before the start time, set the end time to 1 hour after the start time. We do 1 hour instead of
    2.5 hours to make it clear that the end time was autocorrected.
    """
    if end <= start:
        end = start.replace(hour=start.hour + 1)
    return end


def get_calendar_id_by_city(city: str) -> str:
    if city == 'Utrecht':
        return CALENDAR_ID_UTRECHT
    elif city == 'Rotterdam':
        return CALENDAR_ID_ROTTERDAM
    else:
        raise ValueError(f"Unknown city '{city}'")


def handle_lost_deal(deal: dict[str, Any]) -> None:
    """
    Handle a lost deal by deleting the calendar event from Google Calendar and removing the calendar ID from the deal
    """
    google_event_id = deal['custom_field']['cf_google_calendar_id']
    if not google_event_id:
        return

    google_calendar_id = get_calendar_id_by_city(deal['custom_field']['cf_city'])

    try:
        event = get_google_calendar_event(google_event_id, google_calendar_id)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404 or e.response.status_code == 410:
            if VERBOSE_LOGGING:
                print(f'-> Calendar event {google_event_id} not found, skipping delete\n')
                update_deal_empty_calendar_id(deal['id'])
                return
        else:
            raise e

    # Only delete event if it's an OPTIE event
    if 'OPTIE' in event['summary']:
        if VERBOSE_LOGGING:
            print(f'-> Deleting calendar event {google_event_id} for lost deal {deal["id"]} - {deal["name"]}')
        delete_google_calendar_event(google_event_id, google_calendar_id)
        update_deal_empty_calendar_id(deal['id'])


def sync_calendar_with_deal(deal: dict[str, Any]) -> None:
    """
    Checks if the Calendar event matches the start/end datetime of the deal
    """
    if str(deal['deal_stage_id']) == str(DEAL_LOST_STAGE):
        handle_lost_deal(deal)
        return

    deal_start, deal_end, google_event_id = extract_fields_from_deal(deal)

    if not all([deal_start, deal_end]):
        if VERBOSE_LOGGING:
            print('-> Missing date/start/end-time, skipping\n')
        return

    if not google_event_id:
        if VERBOSE_LOGGING:
            print('-> Missing Calendar ID, skipping\n')
        return

    google_calendar_id = get_calendar_id_by_city(deal['custom_field']['cf_city'])

    try:
        event = get_google_calendar_event(google_event_id, google_calendar_id)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            if VERBOSE_LOGGING:
                print(f'-> Calendar event {google_event_id} not found, skipping\n')
            update_deal_empty_calendar_id(deal['id'])
            return
        raise e

    event_start_str= event['start']['dateTime']
    event_start = datetime.strptime(event_start_str, GOOGLE_TIMESTAMP_FORMAT) if event_start_str else None
    event_end_str = event['end']['dateTime']
    event_end = datetime.strptime(event_end_str, GOOGLE_TIMESTAMP_FORMAT) if event_end_str else None
    update_needed = should_update_calendar_event(deal_start, event_start, deal_end, event_end)

    if update_needed:
        if VERBOSE_LOGGING:
            print(f'-> SYNCING: start {event_start}->{deal_start} & end {event_end}->{deal_end}\n')
        deal_end = check_broken_endtime(deal_start, deal_end)
        event_data = {
            'start': {
                'dateTime': deal_start.strftime(GOOGLE_TIMESTAMP_FORMAT)
            },
            'end': {
                'dateTime': deal_end.strftime(GOOGLE_TIMESTAMP_FORMAT)
            }
        }
        update_google_calendar_event(google_event_id, event_data, google_calendar_id)
    else:
        if VERBOSE_LOGGING:
            print(f'-> No updated needed: {event_start.isoformat()=},{deal_start.isoformat()=} & {event_end.isoformat()=},{deal_end.isoformat()=}\n')


def update_deal_empty_calendar_id(deal_id):
    """
    Updates the deal with empty calendar id (for when the calendar event is deleted)
    """
    deal_data = {
        'deal': {
            'custom_field': {
                'cf_google_calendar_id': '',
            }
        }
    }
    url = f'https://{FRESHSALES_DOMAIN}/api/deals/{deal_id}'
    headers = {
        'Authorization': f'Token token={FRESHSALES_TOKEN}',
        'Content-Type': 'application/json'
    }
    if VERBOSE_LOGGING:
        print(f'Updating deal {deal_id} with empty calendar id')
    make_request(url, method='PUT', headers=headers, data=json.dumps(deal_data))


def update_deal_datefields(deal_id, expected_deal_summary, expected_date_readable_nl, expected_date_readable_en):
    deal_data = {
        'deal': {
            'custom_field': {
                'cf_deal_summary': expected_deal_summary,
                'cf_date_with_day': expected_date_readable_nl,
                'cf_date_with_day_en': expected_date_readable_en,
            }
        }
    }
    url = f'https://{FRESHSALES_DOMAIN}/api/deals/{deal_id}'
    headers = {
        'Authorization': f'Token token={FRESHSALES_TOKEN}',
        'Content-Type': 'application/json'
    }
    make_request_ignore_errors(url, method='PUT', headers=headers, data=json.dumps(deal_data))


def sync_deal_date_fields(deal):
    """
    Checks if the deal summary and readable date fields are up-to-date with the date & time fields.
    """
    deal_id = deal['id']

    # Get the current date on deal
    date_str_raw = deal['custom_field']['cf_date']
    date_str = date_str_raw.split('T')[0] if 'T' in date_str_raw else date_str_raw
    deal_datetime = datetime.strptime(date_str, '%Y-%m-%d') if date_str else None

    # Get the actual readable dates & summary
    date_readable_nl = deal['custom_field']['cf_date_with_day'] or ''
    date_readable_en = deal['custom_field']['cf_date_with_day_en'] or ''
    deal_summary = deal['custom_field']['cf_deal_summary']

    # Build up the correct / expected readable dates
    expected_date_readable_en = deal_datetime.strftime('%A %d %B') if deal_datetime else ''
    expected_date_readable_nl = translate_date(expected_date_readable_en)

    # Build up the correct / expected deal summary
    start_time = deal['custom_field']['cf_starting_time']
    end_time = deal['custom_field']['cf_end_time']
    expected_deal_summary = f'{expected_date_readable_nl if expected_date_readable_nl else ''}, {start_time if start_time else ''}-{end_time if end_time else ''} (ID: {deal_id})'

    # Compare the expected & actual to see if we need to update
    if deal_summary != expected_deal_summary or date_readable_nl != expected_date_readable_nl or date_readable_en != expected_date_readable_en:
        if VERBOSE_LOGGING:
            print(f'\nUpdating deal {deal_id}:\n-{deal_summary}->{expected_deal_summary}\n-{date_readable_nl}->{expected_date_readable_nl}\n-{date_readable_en}->{expected_date_readable_en}\n')
        update_deal_datefields(deal_id, expected_deal_summary, expected_date_readable_nl, expected_date_readable_en)
    else:
        if VERBOSE_LOGGING:
            print('No update needed\n')


def sync_deals_datetime_changes(sync_to: str) -> None:
    """
    Takes all deals from Freshsales and checks the date/time to see:
        1. Do we need to update the Deal summary & readable date fields?
        2. Do we need to update the Google Calendar event?
    """
    deals = get_freshsales_deals(FRESHSALES_TOKEN, FRESHSALES_DOMAIN)

    if sync_to == 'freshsales_fields':
        for deal in deals:
            if VERBOSE_LOGGING:
                print(f'CHECK FRESHSALES {deal["id"]} - {deal["name"]}')
            sync_deal_date_fields(deal)

    if sync_to == 'google_calendar':
        for deal in deals:
            if VERBOSE_LOGGING:
                print(f'CHECK CALENDAR {deal["id"]} - {deal["name"]}')
            sync_calendar_with_deal(deal)


def translate_date(date_str):
    tranlations = {
        'Monday': 'maandag',
        'Tuesday': 'dinsdag',
        'Wednesday': 'woensdag',
        'Thursday': 'donderdag',
        'Friday': 'vrijdag',
        'Saturday': 'zaterdag',
        'Sunday': 'zondag',
        'January': 'januari',
        'February': 'februari',
        'March': 'maart',
        'April': 'april',
        'May': 'mei',
        'June': 'juni',
        'July': 'juli',
        'August': 'augustus',
        'September': 'september',
        'October': 'oktober',
        'November': 'november',
        'December': 'december',
    }
    for english, dutch in tranlations.items():
        date_str = date_str.replace(english, dutch)

    return date_str


# TODO: Test with Rotterdam test event
# TODO: deploy new credentials to server, together with updated script

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description='Sync the date/time in freshsales to either google calendar or to other fields in freshsales')
        parser.add_argument('sync_to', choices=['google_calendar', 'freshsales_fields'], help='Where to sync the date/time to')
        args = parser.parse_args()
        sync_deals_datetime_changes(args.sync_to)
    except Exception as e:
        print(f'Sync {args.sync_to} failed with exception: {e}')
        traceback.print_exc()