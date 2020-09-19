
from __future__ import print_function
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import StringVar
import argparse
import pyzbar.pyzbar as pyzbar
import numpy as np
import cv2
import os
import re
import subprocess
import RPi.GPIO as GPIO
import threading
import picamera
import pytesseract


bilder = "demo.jpg"
flag = 0
delete_flag = 0

os.system("sudo modprobe bcm2835-v4l2") # to recognize PiCamera as video0

def do_picam(app):
    global toScan
    global shot
    global texte
    global texmed
    global delete_flag
    global txt_display
    camera = picamera.PiCamera()
    #camera.awb_mode = 'auto'
    camera.brightness = 50
    #camera.rotation= 90
    camera.resolution = (1024, 400) 
    camera.capture(bilder)
    camera.stop_preview()
    camera.close() # close Picamera to free resources  to restart the video stream
    shot = bilder
    app.tesseractAnalysis()
    delete_flag = 1
    app.vs.open(0) # restarting video stream from Pi Camera
    txt_display = " " + shot[0:18]
    
      
class Application:
    def __init__(self, output_path = "./"):
        """ Initialize application which uses OpenCV + Tkinter. It displays
            a video stream in a Tkinter window and stores current snapshot on disk """
        self.vs = cv2.VideoCapture(0) # capture video frames, 0 is your default video camera
        self.output_path = output_path  # store output path
        self.current_image = None  # current image from the camera
        self.root = tk.Tk()  # initialize root window
        self.root.attributes('-fullscreen',True)
        defaultbg = self.root.cget('bg') # set de default grey color to use in labels background
        w = 800 # width for the Tk root
        h = 600 # height for the Tk root
        self.root .resizable(0, 0)
        ws = self.root .winfo_screenwidth() # width of the screen
        hs = self.root .winfo_screenheight() # height of the screen
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.root .geometry('%dx%d+%d+%d' % (w, h, x, y))
        self.root.title("    SCAN HEALTH PASSPORT     ")  # set window title
        self.root.protocol('WM_DELETE_WINDOW', self.destructor)
        
        self.panel = tk.Label(self.root,width= 800, height=250)  # initialize image panel
        self.panel.grid(row=0,rowspan=10,columnspan = 25,column=0,padx=0, pady=20)
        
        self.botShoot = tk.Button(self.root,width=20,height=4,bd=4,font=('arial', 14, 'bold'),  text="CAPTURE ID", activebackground="green" )
        self.botShoot.grid(row=12, column=20,pady=6)
        self.botShoot.configure(command=self.picam)        

        self.botQuit = tk.Button(self.root,width=20,height=4,bd=4,font=('arial', 14, 'bold'), text="CLOSE", activebackground="red")
        self.botQuit.grid(row=14,column=20,pady=5)
        self.botQuit.configure(command=self.destructor)      
        self.video_loop()
        
    def video_loop(self):
        global test
        global flag
        """ Get frame from the video stream and show it in Tkinter """
        ok, frame = self.vs.read()  # read frame from video stream
        if ok:  # frame captured without any errors
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)  # convert colors from BGR to RGBA
            self.current_image = Image.fromarray(cv2image)  # convert image for PIL
            imgtk = ImageTk.PhotoImage(image=self.current_image)  # convert image for tkinter
            test = cv2image
            self.panel.imgtk = imgtk  # anchor imgtk so it does not be deleted by garbage-collector
            self.panel.config(image=imgtk)  # show the image

        self.root.after(30, self.video_loop)  # call the same function after 30 milliseconds
        if flag ==0:
            flag = 1
            #self.show_thumb()
            
    def picam(self):
        self.vs.release() # release the camera to get all resources
        t = threading.Thread(target=do_picam, args=(self,))
        t.start()
                           
    def enable_buttons(self):
        self.botShoot.configure(state="normal")
        self.botQuit.configure(state="normal")
        
    def destructor(self):
        self.root.destroy()
        self.vs.release()  # release pi camera
        cv2.destroyAllWindows()  # it is not mandatory in this application
    
          
    #OCR and Decode QR-Code and Barcode (Function under constraction)
    def tesseractAnalysis(self):
        
        # Find barcodes and QR codes
        decodedObjects = pyzbar.decode(cv2.imread(bilder))
        # Print results on Window (Text)
        get_barcode = ""
        to_display_data = ""
        #for obj in decodedObjects:        
            #get_barcode = obj.data   
        ocr_text = pytesseract.image_to_string(Image.open(bilder), lang="eng")
        ocr_text_split = ocr_text.split(", ",1) #splitting text with comma into two values array
        #print(ocr_text_split[0])
        last_value_ocr_text_split = ocr_text_split[1]
        last_value_ocr_text_splitted = last_value_ocr_text_split.splitlines() 
        #print(last_value_ocr_text_splitted[0])
        to_display_data = ocr_text_split[0] + ", " + last_value_ocr_text_splitted[0]
        print(to_display_data)
        ocr_text_tkinter = tk.StringVar()
        ocr_text_tkinter.set(to_display_data)    
        self.Output = tk.Label(self.root,textvariable = ocr_text_tkinter,font=('arial', 16, 'normal'),height = 6, width = 40,bg="light cyan")
        self.Output.grid(row=12,column=4,pady=12)
# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-o", "--output", default="./Pictures",
help="path to output directory to store snapshots (default: current folder")
args = vars(ap.parse_args())

# start the app
pba = Application(args["output"])
pba.root.mainloop()

