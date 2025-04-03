import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)

TRIG = 23
ECHO = 13

print("DIstance measurement in progress")

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)



my_distance = 200000

while my_distance > 4:
    
    GPIO.output(TRIG, False)
    print("Waiting for sensor to settle")
    time.sleep(2)


    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = 0
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()

    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
        
    pulse_duration = pulse_end - pulse_start

    distance = pulse_duration * 17150

    distance= round(distance, 2)
    
    my_distance = distance

    print("Distance:", distance, "cm")
    
print("Distance:", distance, "cm")

GPIO.cleanup()
    


