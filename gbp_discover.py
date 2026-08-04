import os, json, urllib.request, sys
sys.path.insert(0, '.')
import gbp_post

token = gbp_post._resolve_access_token()

# Newer account management API
req = urllib.request.Request(
    'https://mybusinessaccountmanagement.googleapis.com/v1/accounts',
    headers={'Authorization': 'Bearer ' + token}
)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read())

print('Raw accounts response:', json.dumps(data, indent=2))

for acct in data.get('accounts', []):
    acct_name = acct['name']
    print('\nAccount:', acct_name)
    loc_url = ('https://mybusinessbusinessinformation.googleapis.com/v1/'
               + acct_name + '/locations?readMask=name,title')
    req2 = urllib.request.Request(loc_url, headers={'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.urlopen(req2) as r2:
            locs = json.loads(r2.read())
        for loc in locs.get('locations', []):
            print('  Location:', loc.get('name'), '|', loc.get('title', ''))
    except Exception as e:
        print('  Error fetching locations:', e)
