from BLE_library import Yell, Listen
import time
import json

def callback(data):
    print(data.decode())
        
def peripheral(name): 
    try:
        p = Yell(name, interval_us=30000, verbose = True)
        if p.connect_up():
            p.callback = callback
            print('Connected')
            time.sleep(1)
            i = 0
            message = {'test':12}
            while p.is_connected:
                i += 1
                message['test']=i
                payload = str(json.dumps(message))
                p.send(payload)
                time.sleep(1)
        print('lost connection')
    except Exception as e:
        print('Error: ',e)
    finally:
        p.disconnect()
        print('closing up')
         
peripheral('Katie')

