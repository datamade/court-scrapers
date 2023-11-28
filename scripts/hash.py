# From https://www.doc.ic.ac.uk/~nuric/coding/how-to-hash-a-dictionary-in-python.html

import hashlib
import json


def dict_hash(dictionary):
    """MD5 hash of a dictionary."""
    dhash = hashlib.md5()
    encoded = json.dumps(dictionary, sort_keys=True).encode()
    dhash.update(encoded)
    return dhash.hexdigest()
