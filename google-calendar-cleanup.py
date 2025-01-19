import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

def get_access_token():
    credentials = service_account.Credentials.from_service_account_file(
        'google-service-account.json',
        scopes=['https://www.googleapis.com/auth/calendar']
    )
    credentials.refresh(Request())
    return credentials.token

def get_events(calendar_id, date):
    access_token = get_access_token()
    url = f'https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    params = {
        'timeMin': f'{date}T00:00:00Z',
        'timeMax': f'{date}T23:59:59Z',
        'singleEvents': True
    }
    response = requests.get(url, headers=headers, params=params)
    return response.json()

if __name__ == "__main__":
    calendar_id = 'c_483762361261a15c7296d6383aa5094192161cc2f82f288f255a3a8bb755a307@group.calendar.google.com'
    date = '2024-12-27'
    events = get_events(calendar_id, date)

    for event in events['items']:
        if "<b>Email:</b> test@test.nl" in event['description']:
           print(event['id'], event['summary'])
 