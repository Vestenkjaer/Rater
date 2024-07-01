import requests

domain = 'dev-ltmkusi0krsffl3x.eu.auth0.com'
client_id = 'xyP50XgjCpnYey6H4lxFBWIH6NOmjBsm'
client_secret = 'fJpOY4HgODYUgnPMBqWitq3kait2XsKsJqeTl99M0wckQdf8huFlgswR67QJaiAl'

url = f'https://{domain}/oauth/token'
headers = {'content-type': 'application/json'}
data = {
    'client_id': client_id,
    'client_secret': client_secret,
    'audience': f'https://{domain}/api/v2/',
    'grant_type': 'client_credentials'
}

try:
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
    access_token = response.json().get('access_token')
    if access_token:
        print(f"Access Token: {access_token}")
    else:
        print("Failed to retrieve access token. Response content:", response.content)
except requests.exceptions.HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")
except Exception as err:
    print(f"An error occurred: {err}")
