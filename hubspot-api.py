import requests

from datetime import datetime, timedelta

# TODO: replace before running in Zapier
input_data = {
    "DEAL_ID": "12738903762",
    "DEAL_NAME": "Utrecht Photo Challenge 2024"
}

DEAL_ID = input_data['DEAL_ID']
TEMPLATE_ID = 115428778483

TOKEN = 'pat-eu1-b3414dd4-2d72-4832-a44b-b728368e2a2b'
HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}
BASE_URL = 'https://api.hubapi.com'
QUOTE_ENDPOINT = 'crm/v3/objects/quotes'
QUOTE_PROPERTIES_ENDPOINT = 'crm/v3/properties/quotes'
LINE_ITEMS_ENDPOINT= 'crm/v3/objects/line_items'
QUOTE_TEMPLATES_ENDPOINT = 'crm/v3/objects/quote_template?properties=hs_name'
DEALS_ENDPOINT = 'crm/v3/objects/deals'


def get_url(endpoint: str) -> str:
    return f'{BASE_URL}/{endpoint}'


def create_quote_payload(deal_name: str) -> dict[str, dict[str, str]]:
    """
    Creates a Hubspot quote playload for the given deal name
    """
    expiration_date = datetime.now() + timedelta(days=30)
    return {
        "properties": {
            "hs_title": deal_name,
            "hs_expiration_date": expiration_date.strftime('%Y-%m-%d'), # Example: 2024-12-10
            "hs_esign_enabled": "true",
            "hs_status": "DRAFT",
            "hs_language": "nl",
            "hs_domain": "utrechtphotochallenge-144420208.hs-sites-eu1.com",
            "hs_sender_firstname": "Nathalie",
            "hs_sender_lastname": "van der Linden",
            "hs_sender_email": "info@utrechtphotochallenge.com",
            "hs_sender_company_name": "Utrecht Photo Challenge",
        }
    }


def associate_quote_to(object_type: str, object_id: str) -> None:
    url = f'{BASE_URL}/crm/v4/objects/quotes/{QUOTE_ID}/associations/default/{object_type}/{object_id}'
    response = requests.put(url=url, headers=HEADERS)
    print(f'Associated quote to {object_type} {object_id}: {response.status_code}')


"""
REQUESTS STARTING

FLOW:
    1. Create a quote with a title, expiration esign enabled, TODO: add photochallenge properties
    2. Associate quote w/ quote template
    3. Associate quote w/ deal
    4. Associate quote w/ lineitem
    5. Associate quote w/ contact
    6. Associate quote w/ quote signer (https://developers.hubspot.com/beta-docs/guides/api/crm/commerce/quotes#associating-quote-signers)
"""
# 0. GET EXISTING DEAL DATA
response = requests.get(
    url=f'{get_url(DEALS_ENDPOINT)}/{DEAL_ID}',
    headers=HEADERS,
    params="associations=contacts,line_items"
)

existing_deal = response.json()
print(f'Existing deal: {existing_deal}\n')

# TODO: this is not robust, handle non-existing associations
LINE_ITEM_IDS = {line_item['id'] for line_item in existing_deal['associations']['line items']['results']}
CONTACT_ID = existing_deal['associations']['contacts']['results'][0]['id']
print(f'LINE ITEM IDS {LINE_ITEM_IDS}\n')

for LINE_ITEM_ID in LINE_ITEM_IDS:
    response = requests.get(
        url=f'{get_url(LINE_ITEMS_ENDPOINT)}/{LINE_ITEM_ID}?properties=name',
        headers=HEADERS
    )
    line_item = response.json()

    # 1. CREATE QUOTE
    response = requests.post(
        url=get_url(QUOTE_ENDPOINT),
        headers=HEADERS,
        json=create_quote_payload(deal_name=f'{line_item["properties"]["name"]} - {input_data["DEAL_NAME"]}')
    )
    QUOTE_ID = response.json()['id']

    # 2. ASSOCIATE w/ TEMPLATE
    associate_quote_to(object_type='quote_template', object_id=TEMPLATE_ID)

    # 3. ASSOCIATE w/ DEAL
    associate_quote_to(object_type='deals', object_id=DEAL_ID)

    # 4. ASSOCIATE w/ LINE_ITEM
    associate_quote_to(object_type='line_items', object_id=LINE_ITEM_ID)

    # 5. ASSOCIATE w/ CONTACT
    associate_quote_to(object_type='contacts', object_id=CONTACT_ID)

    # 6. ASSOCIATE w/ SIGNER
    url = f'{BASE_URL}/crm/v4/objects/quote/{QUOTE_ID}/associations/contact/{CONTACT_ID}'
    response = requests.put(
        url=url,
        headers=HEADERS,
        json=[
            {
                # Association: Quote-to-contract-signer
                "associationCategory": "HUBSPOT_DEFINED",
                "associationTypeId": 702
            }
        ]
    )