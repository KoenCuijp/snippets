import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from datetime import datetime, timedelta

# # Enable dictionary below when debugging locally.
# # Resembles the input_data dict that Zapier provides
# input_data = {
#     "DEAL_ID": "12738903762",
#     "DEAL_NAME": "Utrecht Photo Challenge 2024",
#     "NUMBER_OF_PERSONS": 45,
# }

# Hubspot template for the quote
TEMPLATE_ID = 115428778483

class HubspotAPI:
    """
    Wrapper class to contain all Hubspot API requests
    """
    def __init__(self, token):
        self.TOKEN = token
        self.SESSION = None
        self.BASE_URL = 'https://api.hubapi.com'
        self.QUOTE_ENDPOINT = 'crm/v3/objects/quotes'
        self.QUOTE_PROPERTIES_ENDPOINT = 'crm/v3/properties/quotes'
        self.LINE_ITEMS_ENDPOINT = 'crm/v3/objects/line_items'
        self.QUOTE_TEMPLATES_ENDPOINT = 'crm/v3/objects/quote_template?properties=hs_name'
        self.DEALS_ENDPOINT = 'crm/v3/objects/deals'
        self.HEADERS = {
            'Authorization': f'Bearer {self.TOKEN}',
            'Content-Type': 'application/json'
        }

    def get_session(self) -> requests.Session:
        """
        Returns a requests session with retries, creates one if it doesn't exist
        """
        if self.SESSION is not None:
            return self.SESSION

        self.SESSION = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[
                429, 477, 500, 502, 503, 504, 521, 522, 523, 524, 525, 526
            ]
        )
        self.SESSION.mount('https://', HTTPAdapter(max_retries=retries))
        return self.SESSION

    def get_url(self, endpoint: str) -> str:
        return f'{self.BASE_URL}/{endpoint}'
    
    def do_hubspot_request(
            self,
            method: str,
            url: str,
            params: str = None,
            payload: dict | list[dict] = None,
        ) -> requests.Response:
        """
        Main method to do a request to the Hubspot API, includes retries
        """
        session = self.get_session()

        if method == 'GET':
            response = session.get(
                url=url,
                headers=self.HEADERS,
                params=params
            )
        elif method == 'PUT':
            response = session.put(
                url=url,
                headers=self.HEADERS,
                json=payload
            )
        elif method == 'PATCH':
            response = session.patch(
                url=url,
                headers=self.HEADERS,
                json=payload
            )
        elif method == 'POST':
            response = session.post(
                url=url,
                headers=self.HEADERS,
                json=payload
            )
        else:
            raise Exception(f'Invalid method: {method}')

        return response

    def get_existing_deal(self, deal_id: str) -> dict:
        """
        Get an existing deal from Hubspot and return it
        """
        response = self.do_hubspot_request(
            method='GET',
            url=f'{self.get_url(self.DEALS_ENDPOINT)}/{deal_id}',
            params="associations=contacts,line_items"
        )
        existing_deal = response.json()
        print(f'Got existing deal {deal_id} [status {response.status_code}]: {existing_deal}')
        return existing_deal

    def get_line_item(self, line_item_id: str) -> dict:
        """
        Get an existing line item from Hubspot and return it
        """
        response = self.do_hubspot_request(
            method='GET',
            url=f'{self.get_url(self.LINE_ITEMS_ENDPOINT)}/{line_item_id}?properties=name',
        )
        line_item = response.json()
        print(f'Got line item {line_item_id} [status {response.status_code}]: {line_item}')
        return line_item
    
    def update_line_item(self, line_item_id: str, number_of_persons: int) -> None:
        """
        Update the amount of persons for a line item
        """
        response = self.do_hubspot_request(
            method='PATCH',
            url=f'{self.get_url(self.LINE_ITEMS_ENDPOINT)}/{line_item_id}',
            payload={
                "properties": {
                    "quantity": number_of_persons
                }
            }
        )
        print(f'Updated line item {line_item_id} with amount {number_of_persons}: Status {response.status_code}')

    def create_quote(self, quote_title: str, quote_slug: str) -> int:
        """
        Create a quote in Hubspot and return its id
        """
        response = self.do_hubspot_request(
            method='POST',
            url=self.get_url(self.QUOTE_ENDPOINT),
            payload=self.create_quote_payload(quote_title, quote_slug)
        )
        result = response.json()
        print(f'Created quote [status {response.status_code}]: {result}')
        return result['id']

    def create_quote_payload(self, quote_title: str, quote_slug) -> dict[str, dict[str, str]]:
        """
        Creates a Hubspot quote playload for the given quote title & sluge
            note: slug is used as the last part of the URL for the quote
        """
        expiration_date = datetime.now() + timedelta(days=30)
        return {
            "properties": {
                "hs_title": quote_title,
                "hs_slug": quote_slug,
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
    
    def activate_quote(self, quote_id: int) -> None:
        """
        Create a quote in Hubspot and return its id
        """
        response = self.do_hubspot_request(
            method='PATCH',
            url=f'{self.get_url(self.QUOTE_ENDPOINT)}/{quote_id}',
            payload={
                "properties": {
                    "hs_status": "APPROVAL_NOT_NEEDED",
                    "hs_slug": f'{quote_id}{datetime.now().strftime("%Y%m%d%H%M%S")}',
                }
            }
        )
        print(f'Activated quote {quote_id} [Status {response.status_code}]: {response.json()}')

    def associate_quote_to(self, quote_id: int, object_type: str, object_id: str) -> None:
        """
        Associate a quote to the given other Hubspot object (e.g. deal, contact, etc)
        """
        url = f'{self.BASE_URL}/crm/v4/objects/quotes/{quote_id}/associations/default/{object_type}/{object_id}'
        response = self.do_hubspot_request(method='PUT', url=url)
        print(f'Associated quote to {object_type} {object_id}: {response.status_code}')
    
    def associate_quote_to_signer(self, quote_id: int, contact_id: str) -> None:
        """
        Associate a quote to the contact that has to sign the quote
        """
        url = f'{self.BASE_URL}/crm/v4/objects/quote/{quote_id}/associations/contact/{contact_id}'
        response = self.do_hubspot_request(
            method='PUT',
            url=url,
            payload=[
                {
                    # Association: Quote-to-contract-signer
                    "associationCategory": "HUBSPOT_DEFINED",
                    "associationTypeId": 702
                }
            ]
        )
        print(f'Associated quote to signer {contact_id}: {response.status_code}')

"""
START OF LOGIC

FLOW:
    1. Get the existing deal that triggered this Zap (deal=created by hubspot form automation)
    2. Get the line items of this deal, and correct the amount of persons of the line item
        a. Hubspot automation doesn't allow for dynamic line item amounts, so we have to correct this
    3. Create a quote with a title, expiration & esign enabled, TODO: add photochallenge properties
    4. Associate quote w/ quote template
    5. Associate quote w/ deal
    6. Associate quote w/ lineitem
    7. Associate quote w/ contact
    8. Associate quote w/ quote signer (https://developers.hubspot.com/beta-docs/guides/api/crm/commerce/quotes#associating-quote-signers)
    9. Activate the quote
"""

HUBSPOT_API = HubspotAPI(token='pat-eu1-b3414dd4-2d72-4832-a44b-b728368e2a2b')

# 1. GET EXISTING DEAL DATA
existing_deal = HUBSPOT_API.get_existing_deal(deal_id=input_data['DEAL_ID'])

# TODO: this is not robust, handle non-existing associations
line_item_ids = {line_item['id'] for line_item in existing_deal['associations']['line items']['results']}
contact_id = existing_deal['associations']['contacts']['results'][0]['id']

for line_item_id in line_item_ids:
    # 2. Get line item, and correct the amount of persons
    line_item = HUBSPOT_API.get_line_item(line_item_id)
    challenge_name = line_item["properties"]["name"]
    HUBSPOT_API.update_line_item(line_item_id, number_of_persons=input_data["NUMBER_OF_PERSONS"])

    # 3. CREATE QUOTE
    quote_id = HUBSPOT_API.create_quote(
        quote_title=f'{challenge_name} - {input_data["DEAL_NAME"]}',
        quote_slug=f'{line_item_id}{datetime.now().strftime("%Y%m%d%H%M%S")}'
    )

    # 4. ASSOCIATE w/ TEMPLATE
    HUBSPOT_API.associate_quote_to(
        quote_id=quote_id,
        object_type='quote_template',
        object_id=TEMPLATE_ID
    )

    # 5. ASSOCIATE w/ DEAL
    HUBSPOT_API.associate_quote_to(
        quote_id=quote_id,
        object_type='deals',
        object_id=input_data["DEAL_ID"]
    )

    # 6. ASSOCIATE w/ LINE_ITEM
    HUBSPOT_API.associate_quote_to(
        quote_id=quote_id,
        object_type='line_items',
        object_id=line_item_id
    )

    # 7. ASSOCIATE w/ CONTACT
    HUBSPOT_API.associate_quote_to(
        quote_id=quote_id,
        object_type='contacts',
        object_id=contact_id
    )

    # 8. ASSOCIATE w/ SIGNER
    HUBSPOT_API.associate_quote_to_signer(quote_id, contact_id)

    # 9. ACTIVATE QUOTE
    HUBSPOT_API.activate_quote(quote_id)
