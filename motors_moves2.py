from machine import PWM, Pin
import time
servo = PWM(Pin(19), freq=50, duty_u16=0)


#Using duty_ns
print("0 Degrees")
servo.duty_ns(500*1000)
time.sleep(1)
print("90 Degrees")
servo.duty_ns(int(1500*1000))
time.sleep(1)
print("180 Degrees")
servo.duty_ns(int(2500*1000))
time.sleep(1)
#Using duty_u16
max = 65,535
min = 0
# 0 = 0.5 ms
# 90 = 1.5 ms
#180 = 2.5 ms
