from datetime import datetime, timezone
import pytz

SPLIT_DELIMITERS = ["#", "/", "\\", "|", ":", ";", "-", "(", ")", "[", "]"]

def get_width(value):
    return len(str(int(value)))

def public_to_dict(obj, filter_callable=False):
    dictionary = {}
    public = filter(lambda x: not str(x).startswith("_"), dir(obj))
    if filter_callable:
        for attr in public:
            attr_tmp = getattr(obj, attr)
            if not callable(attr_tmp):
                dictionary[attr] = getattr(obj, attr)
    else:
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

def sanitize_name(name: str):
    out_name = name
    for delimiter in SPLIT_DELIMITERS:
        out_name = out_name.replace(delimiter, "")
    return out_name

def split_names(name: str):
    names_list = []
    delimieter_found = False
    for delimiter in SPLIT_DELIMITERS:
        if name.find(delimiter) >= 0:
            delimieter_found = True
            for sub_name in name.split(delimiter):
                names_list.append(sanitize_name(sub_name).strip().lower())
    if not delimieter_found:
        names_list.append(sanitize_name(name).strip().lower())

    return names_list

def get_all_names(name_list: list):
    full_name_list = []
    for name in name_list:
        full_name_list.extend(split_names(name))

    return full_name_list