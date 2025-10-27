
import network
import urequests
import ubinascii
import time
import secrets
import json


#Example from https://docs.micropython.org/en/latest/esp8266/tutorial/network_basics.html 
def wifi_connect():
    import network #imports network library to connect to wifi
    import secrets #imports lib that has ssid and pwd
    sta_if = network.WLAN(network.WLAN.IF_STA)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(secrets.SSID, secrets.PWD)
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ipconfig('addr4'))
    



# Onshape API credentials
ACCESS_KEY = secrets.onshape_api_key
SECRET_KEY = secrets.onshape_secret_key

# double check if you are using Enterprise account
ONSHAPE_HOST = "https://cad.onshape.com"

def create_auth_header():
    credentials = ACCESS_KEY + ":" + SECRET_KEY
    encoded = ubinascii.b2a_base64(credentials.encode()).decode().strip()
    return "Basic " + encoded

def get_assembly_mates(document_id, workspace_id, element_id):
    url = f"{ONSHAPE_HOST}/api/v12/assemblies/d/{document_id}/w/{workspace_id}/e/{element_id}/matevalues"

    headers = {
        "Authorization": create_auth_header(),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        print(f"Making request to: {url}")
        response = urequests.get(url, headers=headers)
        
        print(f"Response code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response data:")
            print(data)
            return data
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            
        response.close()
        
    except Exception as e:
        print(f"Request failed: {e}")
        return None

        
def main():
    wifi_connect()
    time.sleep(2)
    
    
    # For example
    # For URL = https://cad.onshape.com/api/v12/assemblies/d/1daa84665ebf3705bcd3c52f/w/6e9de45d2b7a6c2ebacbc588/e/ab80c4f3562f1d7ccc7818af/matevalues

    document_id = "d5d09a7edd2d9573f08c1aef"
    workspace_id = "cab0346ac5794cd34ee6ff7a"
    element_id = "e568dc6f93d17e0174fabff9"    

    response = get_assembly_mates(document_id, workspace_id, element_id)


if __name__ == "__main__":
    main()