from datetime import datetime, timezone
import pytz

def public_to_dict(obj):
    dictionary = {}
    public = filter(lambda x: not str(x).startswith("_"), dir(obj))
    for attr in public:
        dictionary[attr] = getattr(obj, attr)
    return dictionary

def to_dict(obj):
    dictionary = {}
    ppp = dir(obj)
    for attr in ppp:
        dictionary[attr] = getattr(obj, attr)
    return dictionary


def get_date_from_timestamp(timestamp, tzone=pytz.timezone("Europe/Paris"), fmt = "%b %d %a %H:%M"):
    return datetime.fromtimestamp(timestamp, tz=tzone).strftime(fmt)

def timestamp_now(round_output = False):
    now = datetime.now(tz=timezone.utc).timestamp()
    if round_output:
        return int(now)
    else:
        return now
