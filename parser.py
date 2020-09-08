# import argparse

# parser = argparse.ArgumentParser(description='Process commands.')
# parser.add_argument(
#     'command', metavar='command', type=str, help='Actual command', nargs='?', default=None)
# #parser.add_argument(
# #    'param', metavar='param', type=str, help='Command parameter', nargs='?', default=None)
# parser.add_argument('varargs', metavar='varargs', type=str,
#                                        help='All other string values will be put here', nargs='*', default=None)


# args = parser.parse_args("First second".split())

# print(args)

# print(args.command)
# print(" ".join(args.varargs))

import re

item = "mind flayer"

i_f = re.compile(item, flags=re.IGNORECASE)

x = i_f.search("Mish'Undare, Circlet of The Mind Flayer")

print(x)