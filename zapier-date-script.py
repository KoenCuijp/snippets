from datetime import datetime, timedelta

# Convert to a datetime objects
challenge_date_str = input_data.get('challenge_date')
date_known = challenge_date_str is not None

start_time_str = input_data.get('start_time')
time_known = start_time_str is not None

if date_known:
    challenge_date = datetime.strptime(challenge_date_str, "%Y-%m-%dT%H:%M:%S%z")

if time_known:
    start_time = datetime.strptime(start_time_str, "%H:%M")
    # Calculate end time by adding 2.5 hours
    duration = timedelta(hours=2.5)
    end_time = start_time + duration

# Convert end time back to a string
end_time_str = end_time.strftime("%H:%M") if time_known else "'tijd nog niet bekend'"
challenge_date_human_readable = challenge_date.strftime("%A %d %B") if date_known else "'datum nog niet bekend'"

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

return {"end_time": end_time_str, "challenge_date_human_readable": translate_date(challenge_date_human_readable), "en_challenge_date_human_readable": challenge_date_human_readable}