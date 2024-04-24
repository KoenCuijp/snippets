import requests

from datetime import datetime, timedelta

# TODO: replace before running in Zapier
input_data = {
    "DEAL_ID": "12738903762",
    "DEAL_NAME": "Utrecht Photo Challenge 2024"
}

TEMPLATE_ID = 115428778483

class HubspotAPI:
    """
    Wrapper class to contain all Hubspot API requests
    """
    def __init__(self, token):
        self.TOKEN = token
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

    def get_url(self, endpoint: str) -> str:
        return f'{self.BASE_URL}/{endpoint}'
    
    def get_existing_deal(self, deal_id: str) -> dict:
        """
        Get an existing deal from Hubspot and return it
        """
        response = requests.get(
            url=f'{self.get_url(self.DEALS_ENDPOINT)}/{deal_id}',
            headers=self.HEADERS,
            params="associations=contacts,line_items"
        )
        return response.json()

    def get_line_item(self, line_item_id: str) -> dict:
        """
        Get an existing line item from Hubspot and return it
        """
        response = requests.get(
            url=f'{self.get_url(self.LINE_ITEMS_ENDPOINT)}/{line_item_id}?properties=name',
            headers=self.HEADERS
        )
        return response.json()
    
    def create_quote(self, quote_title: str) -> int:
        """
        Create a quote in Hubspot and return its id
        """
        response = requests.post(
            url=self.get_url(self.QUOTE_ENDPOINT),
            headers=self.HEADERS,
            json=self.create_quote_payload(quote_title)
        )
        return response.json()['id']

    def create_quote_payload(self, quote_title: str) -> dict[str, dict[str, str]]:
        """
        Creates a Hubspot quote playload for the given quote title
        """
        expiration_date = datetime.now() + timedelta(days=30)
        return {
            "properties": {
                "hs_title": quote_title,
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
    
    def associate_quote_to(self, quote_id: int, object_type: str, object_id: str) -> None:
        """
        Associate a quote to the given other Hubspot object (e.g. deal, contact, etc)
        """
        url = f'{self.BASE_URL}/crm/v4/objects/quotes/{quote_id}/associations/default/{object_type}/{object_id}'
        response = requests.put(url=url, headers=self.HEADERS)
        print(f'Associated quote to {object_type} {object_id}: {response.status_code}')
    
    def associate_quote_to_signer(self, quote_id: int, contact_id: str) -> None:
        """
        Associate a quote to the contact that has to sign the quote
        """
        url = f'{self.BASE_URL}/crm/v4/objects/quote/{quote_id}/associations/contact/{contact_id}'
        requests.put(
            url=url,
            headers=self.HEADERS,
            json=[
                {
                    # Association: Quote-to-contract-signer
                    "associationCategory": "HUBSPOT_DEFINED",
                    "associationTypeId": 702
                }
            ]
        )


"""
START OF LOGIC

FLOW:
    1. Create a quote with a title, expiration & esign enabled, TODO: add photochallenge properties
    2. Associate quote w/ quote template
    3. Associate quote w/ deal
    4. Associate quote w/ lineitem
    5. Associate quote w/ contact
    6. Associate quote w/ quote signer (https://developers.hubspot.com/beta-docs/guides/api/crm/commerce/quotes#associating-quote-signers)
"""

HUBSPOT_API = HubspotAPI(token='pat-eu1-b3414dd4-2d72-4832-a44b-b728368e2a2b')

# 0. GET EXISTING DEAL DATA
existing_deal = HUBSPOT_API.get_existing_deal(deal_id=input_data['DEAL_ID'])

# TODO: this is not robust, handle non-existing associations
line_item_ids = {line_item['id'] for line_item in existing_deal['associations']['line items']['results']}
contact_id = existing_deal['associations']['contacts']['results'][0]['id']

for line_item_id in line_item_ids:
    # 0. Get line item for Challenge name
    line_item = HUBSPOT_API.get_line_item(line_item_id)
    challenge_name = line_item["properties"]["name"]

    # 1. CREATE QUOTE
    quote_id = HUBSPOT_API.create_quote(quote_title=f'{challenge_name} - {input_data["DEAL_NAME"]}')

    # 2. ASSOCIATE w/ TEMPLATE
    HUBSPOT_API.associate_quote_to(
        quote_id=quote_id,
        object_type='quote_template',
        object_id=TEMPLATE_ID
    )

    # 3. ASSOCIATE w/ DEAL
    HUBSPOT_API.associate_quote_to(
        quote_id=quote_id,
        object_type='deals',
        object_id=input_data["DEAL_ID"]
    )

    # 4. ASSOCIATE w/ LINE_ITEM
    HUBSPOT_API.associate_quote_to(
        quote_id=quote_id,
        object_type='line_items',
        object_id=line_item_id
    )

    # 5. ASSOCIATE w/ CONTACT
    HUBSPOT_API.associate_quote_to(
        quote_id=quote_id,
        object_type='contacts',
        object_id=contact_id
    )

    # 6. ASSOCIATE w/ SIGNER
    HUBSPOT_API.associate_quote_to_signer(quote_id, contact_id)
