import json

from datetime import datetime

webhook_data = input_data['webhook_data']
data = json.loads(webhook_data)

line_items = data['line_items']
if not line_items:
	raise Exception(f'No line_items in {data}')

product = line_items[0]
product_name = product.get('name', '')

challenge_chosen = 'Private Challenge' if 'private' in product_name.lower() else 'Classic Challenge'
company_or_individual = 'Bedrijf (Company)' if ('compan' in product_name.lower() or 'bedrij' in product_name.lower()) else 'Particulier (Individual)'

participants = 0
interval_minutes = 0

date_str = ''
timeslot_str = ''

for meta in product.get('meta_data', []):
	if meta.get('key') == 'Number of players':
		participants = meta.get('value')
	if meta.get('key') == '_wapbk_booking_date':
		# format: "2025-01-04"
		date_str = meta.get('value')
	if meta.get('key') == '_wapbk_time_slot':
		# format: "14:00 - 16:30"
		timeslot_str = meta.get('value')

challenge_date = ''

if date_str:
	challenge_date_obj = datetime.strptime(date_str, "%Y-%m-%d")
	challenge_date = challenge_date_obj.strftime("%d-%m-%Y")
	google_calendar_date = challenge_date_obj.strftime("%m-%d-%Y")
if timeslot_str:
	challenge_from_time, challenge_to_time = timeslot_str.split('-')
	challenge_from_time = challenge_from_time.replace(" ", "")
	challenge_to_time = challenge_to_time.replace(" ", "")

company_name = data['billing']['company'] if data['billing']['company'] else 'No Company'
firstname = data['billing']['first_name']
lastname = data['billing']['last_name']

date_known = challenge_date != ''
challenge_date_human_readable = challenge_date_obj.strftime("%A %d %B") if date_known else "datum nog niet bekend"

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


return {
	'first_name': firstname,
	'last_name': lastname,
	'company': company_name,
    'address': data['billing']['address_1'],
    'city': data['billing']['city'],
	'postal_code': data['billing']['postcode'],
	'country': data['billing']['country'],
	'email': data['billing']['email'],
	'phone': data['billing']['phone'],
	'challenge_chosen': challenge_chosen,
	'challenge_chosen': challenge_chosen,
	'company_or_individual': company_or_individual,
	'deal_name': company_name if 'company' in company_or_individual.lower() else f'{firstname} {lastname}',
	'deal_value': data['total'],
	'challenge_date': challenge_date,
	'challenge_date_google_calendar': google_calendar_date,
	"challenge_date_human_readable": translate_date(challenge_date_human_readable),
	"en_challenge_date_human_readable": challenge_date_human_readable,
	'challenge_from_time': challenge_from_time,
	'challenge_to_time': challenge_to_time,
	'participants': participants,
	'questions_or_wishes': data['customer_note'],
}
