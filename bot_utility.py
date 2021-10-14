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


def get_date_from_timestamp(
    timestamp, tzone=pytz.timezone("Europe/Paris"), fmt="%b %d %a %H:%M"
):
    return datetime.fromtimestamp(timestamp, tz=tzone).strftime(fmt)


def timestamp_now(round_output=False):
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

    
def dict_strlen(dict_):
    l = 0
    for each_key in dict_:
        if isinstance(dict_[each_key], dict):
            # Recursive call
            l += dict_strlen(dict_[each_key])
        if isinstance(dict_[each_key], list):
            # Recursive call
            for element in dict_[each_key]:
                l += dict_strlen(element)
        elif isinstance(dict_[each_key], int):
            l += 4
        else:
            l += len(dict_[each_key])
    return l

def embed_dict_len(embed):
    field_count = 0
    l = 0

    title = embed.get('title')
    if isinstance(title, str):
        l += len(title)

    description = embed.get('description')
    if isinstance(description, str):
        l += len(description)

    footer = embed.get('footer')
    if isinstance(footer, dict):
        text = footer.get('text')
        if isinstance(text, str):
            l += len(text)

    author = embed.get('author')
    if isinstance(author, dict):
        name = author.get('name')
        if isinstance(name, str):
            l += len(name)

    fields = embed.get('fields')
    if isinstance(fields, list):
        for field in fields:
            field_count = field_count + 1
            l += len(field['name'])
            l += len(field['value'])

    print(title, l, field_count)