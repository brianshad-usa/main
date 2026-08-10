"""
gbp_discover.py -- ONE-TIME helper: list the GBP account + location IDs the
posting automation needs (GBP_ACCOUNT_ID / GBP_LOCATION_ID secrets).

Needs GBP_CLIENT_ID / GBP_CLIENT_SECRET / GBP_REFRESH_TOKEN in the environment
(run gbp_auth.py first). On an API error this prints Google's actual error JSON
-- which says WHETHER the API is disabled on the project, quota is 0 pending
GBP API access approval, or the account lacks permission -- instead of a bare
HTTPError traceback. Paste that error text (it contains no credentials) when
troubleshooting.
"""
import os, json, urllib.request, urllib.error, sys
sys.path.insert(0, '.')
import gbp_post


def _get(url, token, what):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')
        print(f'\n{what} FAILED: HTTP {e.code}')
        try:
            err = json.loads(body).get('error', {})
            print('  status :', err.get('status'))
            print('  message:', err.get('message'))
            for d in err.get('details', []):
                reason = d.get('reason') or d.get('@type', '')
                if reason:
                    print('  detail :', reason)
        except Exception:
            print('  body   :', body[:500])
        sys.exit(1)


token = gbp_post._resolve_access_token()
if not token:
    print('No GBP credentials in env (need GBP_CLIENT_ID / GBP_CLIENT_SECRET / GBP_REFRESH_TOKEN).')
    sys.exit(2)

data = _get('https://mybusinessaccountmanagement.googleapis.com/v1/accounts',
            token, 'Account lookup')

accounts = data.get('accounts', [])
if not accounts:
    print('No accounts returned. Raw response:', json.dumps(data, indent=2))
    sys.exit(1)

for acct in accounts:
    acct_name = acct['name']                      # "accounts/NNNN"
    print('\nAccount:', acct_name, '|', acct.get('accountName', ''))
    locs = _get('https://mybusinessbusinessinformation.googleapis.com/v1/'
                + acct_name + '/locations?readMask=name,title',
                token, 'Location lookup')
    for loc in locs.get('locations', []):
        print('  Location:', loc.get('name'), '|', loc.get('title', ''))

print('\nSecrets to set: GBP_ACCOUNT_ID = the number after "accounts/",'
      ' GBP_LOCATION_ID = the number after "locations/".')
