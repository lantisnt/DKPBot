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