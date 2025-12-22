import json

def ensure_keys(obj: dict, keys: list):
    for k in keys:
        if k not in obj:
            raise ValueError(f"Missing key: {k}")

def pretty(obj):
    return json.dumps(obj, indent=2)