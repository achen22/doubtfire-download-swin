import requests, jsonfile
from bs4 import BeautifulSoup
from getpass import getpass
from pathlib import Path

SAVEFILE = "savedata.json"
settings = jsonfile.load(SAVEFILE)

def get_host_error(url):
  try:
    r = requests.get(url)
    if r.status_code != 200:
      return "Incorrect status code returned by connection"
    if r.headers['Content-Type'][:9] != 'text/html':
      return "Content retrieved has incorrect Content-Type"

    soup = BeautifulSoup(r.content, 'html.parser')
    ng = soup.html.get('ng-app')
    if ng != 'doubtfire':
      return "No Doubtfire app found"
  except requests.exceptions.ConnectionError:
    return "Unable to connect to server"

def get_host(msg = "Please enter the address of the Doubtfire login page, or leave empty to exit: "):
  while True:
    url = input(msg)
    if not url:
      return
    if url[:4] != 'http':
      url = "https://" + url

    print(f"Checking {url}...")
    err = get_host_error(url)
    if not err:
      return url
    print(err)

def get_auth_request_json(host, endpoint, token):
  # I've never seen this endpoint return any content on success
  r = requests.get(host + endpoint, {'auth_token': token})
  return r.json()

def get_auth_token(url):
  while True:
    print(f"Log in to {url}")
    formdata = { 'remember': True }
    formdata['username'] = input("Username: ")
    formdata['password'] = getpass("Password: ")

    print("Logging in...")
    r = requests.post(url + "/api/auth", formdata)
    if r.status_code == 401: # Unauthorized
      msg = r.json()['error']
      print(f"Login failed: {msg}")
    elif r.status_code == 201: # Created
      print("Login successful")
      return r.json()['auth_token']
    else: # Unknown status code
      return

def get_unit(projects):
  while True:
    print("Units You Study")
    for i in range(len(projects)):
      project = projects[i]
      unit_code = project['unit_code']
      unit_name = project['unit_name']
      print(f"[{i+1}] {unit_code} - {unit_name}")

    entered = input("\nSelect a unit to download PDFs and resources, or enter [0] to exit: ")
    if not entered:
      return 0
    elif entered.isdigit():
      entered = int(entered)
      if entered <= len(projects):
        return entered
    print("Invalid input!\n")

if __name__ == "__main__":
  # check saved host
  if 'host' in settings:
    host = settings['host']
    err = get_host_error(host)
    if err:
      print(f"Error connecting to '{host}': {err}")
      settings = {}
      jsonfile.save(settings, SAVEFILE)

  if 'auth_token' in settings:
    auth_token = settings['auth_token']
    # I haven't seen this endpoint return any content on success
    err = get_auth_request_json(host, "/api/unit_roles", auth_token)
    if err and 'error' in err:
      print(f"Authentication token error: {err['error']}")
      del settings['auth_token']
      jsonfile.save(settings, SAVEFILE)
      
  while True:
    if 'host' not in settings:
      host = get_host()
      if host:
        print("Doubtfire server found!\n")
        settings['host'] = host
        jsonfile.save(settings, SAVEFILE)
      else:
        break # exit program
        
    if 'auth_token' not in settings:
      auth_token = get_auth_token(settings['host'])
      if auth_token:
        settings['auth_token'] = auth_token
        jsonfile.save(settings, SAVEFILE)
      else:
        break # exit program
    
    host = settings['host']
    token = settings['auth_token']

    projects = get_auth_request_json(host, "/api/projects", token)
    projects.sort(key = lambda p: p['unit_id'], reverse = True)
    unit = get_unit(projects)
    if not unit:
      break
    unit_id = projects[unit - 1]['unit_id']
    unit = get_auth_request_json(host, f"/api/units/{unit_id}", token)

    folder = f"./download/{unit['code']}"
    Path(folder).mkdir(parents=True, exist_ok=True)
    with open(folder + "/Tasks.md", "w") as f:
      f.write(f"# {unit['code']} - {unit['name']}\n")

      tasks = unit['task_definitions']
      for task in tasks:
        print(task['abbreviation'])
        f.write(f"\n## {task['name']}\n")
        f.write(f"{task['description']}\n")
        requirements = task['upload_requirements']
        for r in requirements:
          f.write(f"- [{r['type']}] {r['name']}\n")
        if task['has_task_pdf']:
          url = f"{host}/api/units/{unit_id}/task_definitions/{task['id']}/task_pdf.json"
          r = requests.get(url, {'auth_token': token})
          fname = r.headers['Content-Disposition']
          if fname[:21] == "attachment; filename=":
            with open(folder + "/" + fname[21:], "wb") as pdf:
              pdf.write(r.content)
        if task['has_task_resources']:
          url = f"{host}/api/units/{unit_id}/task_definitions/{task['id']}/task_resources.json"
          r = requests.get(url, {'auth_token': token})
          fname = r.headers['Content-Disposition']
          if fname[:21] == "attachment; filename=":
            with open(folder + "/" + fname[21:], "wb") as resources:
              resources.write(r.content)
        