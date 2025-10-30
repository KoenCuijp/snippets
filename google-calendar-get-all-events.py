import csv
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

def get_access_token():
    credentials = service_account.Credentials.from_service_account_file(
        "urban-klik-google-service-account.json",
        scopes=["https://www.googleapis.com/auth/calendar"],
        subject="info@urbanklik.com"  # <--- user to impersonate
    )
    credentials.refresh(Request())
    return credentials.token

def fetch_all_events(calendar_id):
    access_token = get_access_token()
    url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
    headers = {"Authorization": f"Bearer {access_token}"}

    events, page_token = [], None
    while True:
        params = {
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": 2500,
            "pageToken": page_token,
        }
        resp = requests.get(url, headers=headers, params=params)
        data = resp.json()
        print(data)
        events.extend(data.get("items", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return events

def export_to_csv(events, output_file="calendar_events.csv"):
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Date", "Time", "Title", "Description"])
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date"))
            if "T" in start:
                date, time = start.split("T")
                time = time.replace("Z", "")
            else:
                date, time = start, ""
            writer.writerow([
                e.get("id", ""),
                date,
                time,
                e.get("summary", ""),
                e.get("description", "")
            ])
    print(f"✅ Exported {len(events)} events to {output_file}")

if __name__ == "__main__":
    calendar_id = "c_273e06c78d0c1b3f40b938f645c73ead3c951be4f560284a6253949dd5d88360@group.calendar.google.com"
    events = fetch_all_events(calendar_id)
    print(events)
    export_to_csv(events)
