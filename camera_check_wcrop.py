from picamera import PiCamera #Pi camera load lib
from picamera import Color
import datetime as dt

from time import sleep
import RPi.GPIO as GPIO #Pi LIB GPIO
from PIL import Image #used for cropping image




#Turn on LED while camera is warming up
GPIO.setmode (GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(17,GPIO.OUT)#sets GPIO17 as an output pin
GPIO.output(17,GPIO.HIGH)#sets LED ON
sleep(2)#sleep for LED being on




camera = PiCamera()
sleep(2)
camera.resolution = (1920, 1080)
camera.brightness = 50
camera.contrast = 10

# now = datetime.now()
# dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

camera.start_preview()
camera.annotate_text_size = 60
camera.annotate_foreground = Color('black')
camera.annotate_background = Color('white')
camera.annotate_text = dt.datetime.now().strftime('Athena Fridge - %Y-%m-%d %H:%M:%S')

sleep(2)#sleep for camera preview
camera.capture ('image.png')#takes still from camera
camera.stop_preview()#stops view from camera

sleep(2)

im=Image.open('image.png')
width, height = im.size
print (width)
print (height)
left = 350 #width/2
top = 0 #height/2
right = 1570 #(3*(width/2))
bottom = 1080 #(3* (height/2))

im1=im.crop((left, top, right, bottom))

im1.save('image1.png')



GPIO.output(17,GPIO.LOW)#turns off LED



camera.stop_preview()#stops view from camera        