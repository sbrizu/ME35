# k Nearest Neighbor demo

# [accelerometer, motor position, LED_color]


from machine import Pin
import neopixel
import lis3dh
import encoder
import math
import time


STATE_TRAIN = False
STATE_PLAY = True

#data =[]
count = 0

data = [[0,0,1],[100,50,2], [50,200,3],[2,4,1],[95,45,2], [48,180,3],[8,2,1],[89,30,2], [35,190,3],[20,10,1],[80,65,2], [35,160,3]]
color_LUT = {1:(0,0,100),2:(0,100,0),3:(100,0,0)}


motor = encoder.Motor(27, 14, 32,39)
h3lis331dl = lis3dh.H3LIS331DL(sda_pin=21, scl_pin=22)
np = neopixel.NeoPixel(Pin(15), 2)

button_Train =  Pin(35, Pin.IN, Pin.PULL_UP)
button_Play = Pin(34, Pin.IN, Pin.PULL_UP)

debounce_filter = 100
last_entered_time = 0

def trainButton(p):
    #record the values
    global data
    global count
    
    #to control debounce
    global last_entered_time
    entered_time = time.ticks_ms() # time this function was called
    if((time.ticks_ms() - last_entered_time) < debounce_filter):
        return
    last_entered_time = entered_time
    
    print("pressed")
    data.append([h3lis331dl.read_accl_g()['x']*100, motor.pos() , color_LUT[count%3]])
    count +=1
    
    
def playButton(p):
    #enable play mode
    global STATE_PLAY
    global STATE_TRAIN
    STATE_TRAIN = False
    STATE_PLAY = True
    print(data)

    
    
button_Train.irq(trigger=Pin.IRQ_RISING, handler=trainButton)
button_Play.irq(trigger=Pin.IRQ_RISING, handler=playButton)


#for K = 1
def nearest_neighbor(x,y):
    dist_min = 100000
    for index, d in enumerate(data):
        dist = math.sqrt((x-d[0])**2 + (y-d[1])**2)
        if(dist < dist_min):
            dist_min = dist
            col = d[2]
        
    return col


# for KNN
def k_nearest_neighbor(x,y, k =1):
    dist_min = 100000
    distances = []
    for index, d in enumerate(data):
        dist = math.sqrt((x-d[0])**2 + (y-d[1])**2)
        distances.append([dist,index])
    
    
    distances.sort()
    distances = distances[:k] #get k distances
    print("distances", distances)
    classes = []
    for dist in distances:
        print(data[dist[1]])
        classes.append(data[dist[1]][2])
    print("k classes", classes)
    print("max classes ", max(classes))
    
    col = max(classes)
    return col



while True:
    if(STATE_TRAIN):
        np[0]=color_LUT[count%3]
        np.write()
    if(STATE_PLAY):
        #do something else
        accl_g = h3lis331dl.read_accl_g()['x']
        motor_position = motor.pos()
        
        
        what_color = k_nearest_neighbor(accl_g*100, motor_position, 3)
        np[0]=color_LUT[what_color]
        np.write()
        time.sleep(0.1)
        
    
