import os
import requests
import json

def get_auth0_management_token():
    url = "https://dev-ltmkusi0krsffl3x.eu.auth0.com/oauth/token"
    payload = {
        "client_id": "XYhuec5rL33WZ7b2SspKKQWuGXD3bTF8",
        "client_secret": "IGPX13CGznmyKga-8WmlRXQp8gfKw7_twsQOoEUigR276cyzoewRssGY_sZ12BOo",
        "audience": "https://dev-ltmkusi0krsffl3x.eu.auth0.com/api/v2/",
        "grant_type": "client_credentials"
    }
    headers = {'content-type': 'application/json'}
    
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    
    # Debugging information
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload)}")
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Content: {response.content}")

    response.raise_for_status()  # Raise an error for bad status codes
    return response.json()['access_token']

if __name__ == "__main__":
    token = get_auth0_management_token()
    print(f"Auth0 Management API Token: {token}")
