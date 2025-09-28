from machine import Pin, PWM
import time

# Set up servo on a specific pin
servo_pin = 19  # Change this to your ESP32 GPIO pin connected to the servo
servo = PWM(Pin(servo_pin))
servo.freq(50)  # Standard servo frequency is 50Hz

# Function to set servo angle (0-180 degrees)
def set_servo_angle(angle):
    min_duty = 26  # Duty cycle for 0 degrees (0.5ms at 50Hz)
    max_duty = 128  # Duty cycle for 180 degrees (2.5ms at 50Hz)
    
    # Calculate duty cycle based on angle
    duty = min_duty + (max_duty - min_duty) * (angle / 180)
    servo.duty(int(duty))

# Example usage
try:
    # Move servo to different positions
    print("Moving to 0 degrees")
    set_servo_angle(0)
    time.sleep(1)
    
    print("Moving to 90 degrees")
    set_servo_angle(90)
    time.sleep(1)
    
    print("Moving to 180 degrees")
    set_servo_angle(180)
    time.sleep(1)
    
    print("Sweeping from 0 to 180 degrees")
    for angle in range(0, 181, 5):
        set_servo_angle(angle)
        time.sleep(0.1)
    
    # Return to center position
    set_servo_angle(90)
    
except Exception as e:
    print("Error:", e)
finally:
    # Clean up
    servo.deinit()
    print("Servo control ended")
