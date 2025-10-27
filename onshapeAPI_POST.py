
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


def post_assembly_mates(document_id, workspace_id, element_id, angle1, angle2, angle3, angle4, angle5, angle6):
    url = f"{ONSHAPE_HOST}/api/v12/assemblies/d/{document_id}/w/{workspace_id}/e/{element_id}/matevalues"
    
    
    text = {
        "mateValues": [
        {
          "featureId": "MAAwSflCPC11eLZtK",
          "jsonType": "Revolute",
          "mateName": "wrist_3_joint",
          "rotationZ": angle1
        },
        {
          "featureId": "MPK0dohBVMQR4IWPt",
          "jsonType": "Revolute",
          "mateName": "wrist_2_joint",
          "rotationZ": angle2
        },
        {
          "featureId": "MaRcIWoBQm2cpYAQk",
          "jsonType": "Revolute",
          "mateName": "shoulder_pan_joint",
          "rotationZ": angle3
        },
        {
          "featureId": "MerKA/NyqIJ7v88mJ",
          "jsonType": "Revolute",
          "mateName": "shoulder_lift_joint",
          "rotationZ": angle4
       },
        {
          "featureId": "MfvLXbpG82CcM6fFi",
          "jsonType": "Revolute",
          "mateName": "wrist_1_joint",
          "rotationZ": angle5
           },
        {
          "featureId": "MqCDGHes8xP0FjWzW",
          "jsonType": "Revolute",
          "mateName": "elbow_joint",
          "rotationZ": angle6
           },
        
        
          ]
        }


    headers = {
        "Authorization": create_auth_header(),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        print(f"Making request to: {url}")
        response = urequests.post(url, headers=headers, data = json.dumps(text))
        
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

    document_id = "c2df165c49cc196112e1d6ea"
    workspace_id = "0f4bcb1df4ca213b87216747"
    element_id = "b14f65af9afe02398ea5eaf8"    
    
    response = post_assembly_mates(document_id, workspace_id, element_id,0,0,1,0,1,0)

if __name__ == "__main__":
    main()