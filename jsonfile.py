import json

def save(settings, filename):
  with open(filename, "w") as f:
    json.dump(settings, f)

def load(filename):
  try:
    with open(filename) as f:
      return json.load(f)
  except FileNotFoundError:
    return {}
  except json.decoder.JSONDecodeError:
    return {}