from machine import Pin, PWM, Timer

class Count(object):
    def __init__(self,A,B):
        self.A = Pin(A, Pin.IN)
        self.B = Pin(B, Pin.IN)
        self.counter = 0

        self.A.irq(self.cb,self.A.IRQ_FALLING|self.A.IRQ_RISING) #interrupt on line A
        self.B.irq(self.cb,self.B.IRQ_FALLING|self.B.IRQ_RISING) #interrupt on line B


    def cb(self,msg):
        other,inc = (self.B,1) if msg == self.A else (self.A,-1) #define other line and increment
        self.counter += -inc if msg.value()!=other.value() else  inc 
        
    def value(self):
        #print(self.counter)
        return self.counter
    
class Motor(Count):
    def __init__(self,m1,m2, A, B):
        self.enc = Count(A,B)
        self.M1 = PWM(m1, freq=100, duty_u16=0)
        self.M2 = PWM(m2, freq=100, duty_u16=0)
        self.stop()
                    
        self.oldpos = 0
        self.newpos = 0
        self.velocity = 0
        self.T = 500
        self.RPM = 0
        
        tim = Timer(0)  # Use Timer 0
        tim.init(mode=Timer.PERIODIC, period=self.T, callback=self.find_velocity) # T m-second interval
    

    def find_velocity(self,p):
        self.newpos = self.pos()
        self.velocity = (self.newpos - self.oldpos)/self.T
        self.RPM = self.velocity * 1000 * 60  / 3840  # since 1 rot = 3840 counts, and velocity = counts/ ms
        self.oldpos = self.newpos
    
    def show_velocity(self):
        return self.velocity
    
    def show_RPM(self):
        return self.RPM
    
    
    def pos(self):
        return self.enc.value()
        #        print(self.enc.value())        
            
    def stop(self):
        self.M1.duty_u16(0) 
        self.M2.duty_u16(0) 

    def start(self, direction = 0, speed = 50):
        if direction:
            self.M1.duty_u16(int(speed*65535/100)) 
            self.M2.duty_u16(0)
        else:
            self.M1.duty_u16(0)
            self.M2.duty_u16(int(speed*65535/100)) 
     
    def setSpeed(self,direction = 0, speed = 100): #percentage
        if direction:
            self.M1.duty_u16(int(speed*65535/100)) 
            self.M2.duty_u16(0)
        else:
            self.M1.duty_u16(0)
            self.M2.duty_u16(int(speed*65535/100))
    

            


    

#count = Count(32,39)
#print(count.value())

#setting up motor with encoder
#Motor1 = Motor(14,27, 32,39)
#Motor1.pos() # to read the encoder value for Motor 1

