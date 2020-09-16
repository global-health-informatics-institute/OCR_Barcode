from __future__ import print_function
import pyzbar.pyzbar as pyzbar
import numpy as np
import cv2
import picamera
from time import sleep
from PIL import Image
import pytesseract
import os

def decode(im) : 
  # Find barcodes and QR codes
  decodedObjects = pyzbar.decode(im)

  # Print results
  for obj in decodedObjects:
    print('Type : ', obj.type)
    print('Data : ', obj.data,'\n')
    
  return decodedObjects

def imageCapture():
    #create object for picamera class
    camera = picamera.PiCamera()
    #ser resolution
    camera.resolution = (1024, 768)
    camera.brightness = 50
    camera.start_preview()
    sleep(5)
    #store image
    camera.capture('demo.jpg')
    camera.stop_preview()

def tesseractAnalysis():
    print(pytesseract.image_to_string(Image.open("demo.jpg"), lang="eng"))
# Main 
if __name__ == '__main__':
    
  imageCapture()
  tesseractAnalysis()
  # Read image
  im = cv2.imread('demo.jpg')
  decodedObjects = decode(im)
  os.remove("demo.jpg")