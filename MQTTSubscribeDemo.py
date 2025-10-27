import network
import time
from umqtt.simple import MQTTClient
import secrets

# Wi-Fi credentials
SSID = secrets.SSID
PASSWORD = secrets.PWD

# MQTT settings
MQTT_BROKER = "10.5.11.224"  # Your server's IP - find it from your network settings
MQTT_PORT = 1883 # you may have to configure your port in your conf file in your broker - check with the broker
CLIENT_ID = "esp32_client"
TOPIC_PUB = "ME35/class"
TOPIC_SUB = "ME35/milan"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(SSID, PASSWORD)
        timeout = 10
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
        
    if wlan.isconnected():
        print("WiFi Connected! IP:", wlan.ifconfig()[0])
        return True
    else:
        print("WiFi connection failed!")
        return False


def sub_cb(topic, msg):
    print(f"Received message on topic '{topic.decode()}' : '{msg.decode()}'")


def mqtt_connect():
    try:
        client = MQTTClient(CLIENT_ID, MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.set_callback(sub_cb)
        client.connect()
        client.subscribe(TOPIC_SUB) # change this to the topic you want to subscribe
        print("MQTT Connected successfully!")
        return client
    except OSError as e:
        print(f"MQTT Connection failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

if connect_wifi():
    client = mqtt_connect()
    if client:
        while True:
            try:
                client.check_msg()
                time.sleep(1)
            
            except Exception: #as e:
                pass
                #print(f"Checking message failed: {e}")

        
            
          
