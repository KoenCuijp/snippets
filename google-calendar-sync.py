import json
import requests

from datetime import datetime

from google.oauth2 import service_account
from google.auth.transport.requests import Request
from tenacity import retry, stop_after_attempt, wait_exponential

from credentials import FRESHSALES_TOKEN, FRESHSALES_DOMAIN, GOOGLE_CALENDAR_ID

GOOGLE_TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%S%z'


def get_google_access_token():
    credentials = service_account.Credentials.from_service_account_file(
        'google-service-account.json',
        scopes=['https://www.googleapis.com/auth/calendar']
    )
    credentials.refresh(Request())
    return credentials.token


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
def make_request(url, method='GET', headers=None, data=None, params=None):
    response = requests.request(method=method, url=url, headers=headers, data=data, params=params)
    response.raise_for_status()
    return response.json()


def get_freshsales_deals(api_key, domain):
    deals = []
    page = 1
    page_size = 25
    url = f'https://{domain}/api/deals/view/31007998271?per_page={page_size}'
    headers = {
        'Authorization': f'Token token={api_key}',
        'Content-Type': 'application/json'
    }

    done_fetching = False
    while not done_fetching:
        page_url = f'{url}&page={page}'
        print(f'GET {page_url}')
        data = make_request(page_url, headers=headers)
        max_page = data['meta']['total_pages'] if data.get('meta', {}).get('total_pages') else 1
        done_fetching = page >= max_page
        deals.extend(data['deals'])
        page += 1

    return deals


def get_google_calendar_event(event_id):
    access_token = get_google_access_token()
    url = f'https://www.googleapis.com/calendar/v3/calendars/{GOOGLE_CALENDAR_ID}/events/{event_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    return make_request(url, headers=headers)


def update_google_calendar_event(event_id, event_data):
    access_token = get_google_access_token()
    url = f'https://www.googleapis.com/calendar/v3/calendars/{GOOGLE_CALENDAR_ID}/events/{event_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    response = requests.patch(url, headers=headers, data=json.dumps(event_data))
    return response.json()


def extract_fields_from_deal(deal):
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

    deal_start_str = f'{date_str}T{starting_time}:00+01:00'
    deal_start = datetime.strptime(deal_start_str, GOOGLE_TIMESTAMP_FORMAT)
    deal_end_str = f'{date_str}T{end_time}:00+01:00'
    deal_end = datetime.strptime(deal_end_str, GOOGLE_TIMESTAMP_FORMAT)

    return deal_start, deal_end, calendar_event_id


def should_update_calendar_event(deal_start, event_start, deal_end, event_end):
    needs_update = deal_start != event_start or deal_end != event_end
    return needs_update


def sync_calendar_with_deal(deal):
    print(f'CHECK {deal["id"]} - {deal["name"]}')
    deal_start, deal_end, calendar_event_id = extract_fields_from_deal(deal)
        
    if not all([deal_start, deal_end]):
        print('-> Missing date/start/end-time, skipping\n')
        return

    if not calendar_event_id:
        print('-> Missing Calendar ID, skipping\n')
        return

    event = get_google_calendar_event(calendar_event_id)
    event_start_str= event['start']['dateTime']
    event_start = datetime.strptime(event_start_str, GOOGLE_TIMESTAMP_FORMAT) if event_start_str else None
    event_end_str = event['end']['dateTime']
    event_end = datetime.strptime(event_end_str, GOOGLE_TIMESTAMP_FORMAT) if event_end_str else None
    update_needed = should_update_calendar_event(deal_start, event_start, deal_end, event_end)

    if update_needed:
        print(f'-> SYNCING: start {event_start}->{deal_start} & end {event_end}->{deal_end}\n')
        event_data = {
            'start': {
                'dateTime': deal_start.strftime(GOOGLE_TIMESTAMP_FORMAT)
            },
            'end': {
                'dateTime': deal_end.strftime(GOOGLE_TIMESTAMP_FORMAT)
            }
        }
        update_google_calendar_event(calendar_event_id, event_data)
    else:
        print(f'-> No updated needed: {event_start.isoformat()=},{deal_start.isoformat()=} & {event_end.isoformat()=},{deal_end.isoformat()=}\n')


def sync_freshsales_with_google_calendar():
    deals = get_freshsales_deals(FRESHSALES_TOKEN, FRESHSALES_DOMAIN)

    for deal in deals:
        sync_calendar_with_deal(deal)


if __name__ == "__main__":
    sync_freshsales_with_google_calendar()