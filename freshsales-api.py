import requests
import json

from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from credentials import FRESHSALES_TOKEN

# Freshsales API URL and headers
base_url = 'https://utrechtphotochallenge.myfreshworks.com/crm/sales/api'
headers = {
    'Authorization': f'Token token={FRESHSALES_TOKEN}',
    'Content-Type': 'application/json',
}

# Deal ID
deal_id = '31004077273'

# Setup a session with retries
SESSION = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[
                429, 477, 500, 502, 503, 504, 521, 522, 523, 524, 525, 526
            ]
        )
SESSION.mount('https://', HTTPAdapter(max_retries=retries))


# Get the deal
print(f'GET /deal/{deal_id}')
deal_response = SESSION.get(f'{base_url}/deals/{deal_id}?include=contacts', headers=headers)
print(deal_response.status_code)
deal_data = deal_response.json()
print(f'DEAL DATA = {deal_data}')

# Extract the contact and company associated with the deal
contact = deal_data['contacts'][0] if deal_data['contacts'] else None
company = contact['sales_accounts'][0] if contact and contact['sales_accounts'] else None

contact_id = contact['id'] if contact else None
first_name = contact['first_name'] if contact else None
last_name = contact['last_name'] if contact else None
email = contact['email'] if contact else None
company_name = company['name'] if company else None

# Update the deal with the contact & company details
deal_update = {
    'deal': {
        'custom_field': {
            'cf_quote_requester_first_name': first_name,
            'cf_quote_requester_last_name': last_name,
            'cf_quote_requester_email': email,
            'cf_quote_requester_company': company_name,},
    }
}
print(f'PUT /deal/{deal_id} with data = {deal_update}')
update_response = SESSION.put(f'{base_url}/deals/{deal_id}', headers=headers, data=json.dumps(deal_update))
print(update_response.status_code)
print(update_response.json())