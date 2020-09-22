
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
    camera.brightness = 50
    camera.resolution = (1296,506) #This resolution works better for barcode decoding
    camera.color_effects = (128,128) #Turn camera to black and white
    #camera.crop = (0.0,0.0,3.1,0.53) #crop image to take label only  
    camera.capture(bilder)
    os.system("convert -density 360 /home/pi/Documents/demo.jpg /home/pi/Documents/demo.jpg")
    camera.stop_preview()
    camera.close() # close Picamera to free resources  to restart the video stream
    shot = bilder
    app.tesseractAnalysis()
    delete_flag = 1
    #app.vs.open(0) # restarting video stream from Pi Camera
    txt_display = " " + shot[0:18]
      
class Application:
    def __init__(self, output_path = "./"):
        """ Initialize application which uses OpenCV + Tkinter. It displays
            a video stream in a Tkinter window and stores current snapshot on disk """
        self.vs = cv2.VideoCapture(0) # capture video frames, 0 is your default video camera
        #Setting the live screen frame
        self.vs.set(cv2.CAP_PROP_FRAME_WIDTH,640)
        self.vs.set(cv2.CAP_PROP_FRAME_HEIGHT,250)
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
        
        self.panel = tk.Label(self.root,width= 800, height=250)  # initialize image panel
        self.panel.grid(row=0,rowspan=10,columnspan = 25,column=0,padx=0, pady=20)
        
        self.botShoot = tk.Button(self.root,width=12,height=4,bd=4,font=('arial', 14, 'bold'),  text="CAPTURE", activebackground="light blue",bg = "cyan")
        self.botShoot.grid(row=12, column=18,pady=20)
        self.botShoot.configure(command=self.picam)        
        
        #!!Button to be changed to save function soon
        self.botQuit = tk.Button(self.root,width=12,height=4,bd=4,font=('arial', 14, 'bold'), text="SAVE", activebackground="light blue",bg = "light green")
        self.botQuit.grid(row=13,column=18)
        self.botQuit.configure(command=self.destructor)
        
        self.Output = tk.Label(self.root,text = "Insert Health Passport",font=('arial', 25, 'normal'),height = 7, width = 30,bg="light cyan")
        self.Output.grid(row=12,column=4,rowspan=8,columnspan=1)
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
        
        validMonths = set(['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'])
        verified_id = ""
        # Find barcode and Decode
        decodedObjects = pyzbar.decode(cv2.imread(bilder))
        for obj in decodedObjects:
            get_id = str(obj.data)
        split_get_id = get_id.split("'")
        id_only = split_get_id[1]
        #print(id_only)
        #Extracring OCR Data
        ocr_text = pytesseract.image_to_string(Image.open(bilder), lang="eng")
        #print(ocr_text)
        ocr_text_split = ocr_text.split(", ",1) #splitting text with coMonthOfBirtha into two values array
        print(ocr_text_split)
        ocr_text_splitted = ocr_text_split[0].split("\n")
        print(ocr_text_splitted)
        full_name = ocr_text_splitted[0] #get the full name from first line
        split_full_name = full_name.split(" ")
        first_name = split_full_name[0]
        last_name = split_full_name[1]
        print(first_name + " " +last_name)
        
        take_date = ocr_text_splitted[1].split(" ")
        get_id_ocr = take_date[0].replace("-","") #Getting id from OCR to later compare with one from barcode 
        #checking barcode id and OCR id
        if get_id_ocr == id_only:
            print("OCR is Okay ")
            verified_id = take_date[0]
            print(verified_id)
        else:
            print("OCR is Poor")
            
        #Processing Date Validation   
        date_taken = take_date[1].split("/")
        DayOfBirth = date_taken[0] #Extract Day from date
        MonthOfBirth = date_taken[1] #Extract Month from date
        print(date_taken)
        take_year = date_taken[2].split("(")
        YearOfBirth = take_year[0] #Extract Year from date        
        # Validating the Year Captured from OCR
        if "?" in YearOfBirth:
            YearOfBirth = "????"
            print(YearOfBirth)        
        else:
            YearOfBirth = int(YearOfBirth)
            if YearOfBirth < 1920 or YearOfBirth > 2025:
                YearOfBirth = "????"
                print(YearOfBirth)         
        # Validating the Month Captured from OCR
        if MonthOfBirth.upper() not in validMonths:
           MonthOfBirth = "???"
        print(MonthOfBirth)     
        # Validating the Day Captured from OCR
        if "?" in DayOfBirth:
            DayOfBirth = "??"
            print(DayOfBirth)
        else :
            DayOfBirth = int (DayOfBirth)
            if(MonthOfBirth==1 or MonthOfBirth==3 or MonthOfBirth==5 or MonthOfBirth==7 or MonthOfBirth==8 or MonthOfBirth==10 or MonthOfBirth==12):
                maxDay=31
            elif(MonthOfBirth==4 or MonthOfBirth==6 or MonthOfBirth==9 or MonthOfBirth==11):
                maxDay=30
            elif(YearOfBirth%4==0 and YearOfBirth%100!=0 or YearOfBirth%400==0):
                maxDay=29
            else:
                maxDay=28
            if(DayOfBirth<1 or DayOfBirth>maxDay):
                DayOfBirth = "??"
                print(DayOfBirth)
                
        #processing Gender
        gender = take_year[1].rstrip(")")
        print(gender)
        #Start coding from here !!!
        # Process District 
        district = ocr_text_splitted[2]
        print(district)
        
        #Process village
        home_village  = ocr_text_split[1].split("\n")
        village = home_village[0]
        print(village)
        
        #Data to display on user Interface
        to_display_data = first_name + " " + last_name + "\n" + verified_id + " " + str(DayOfBirth) +"/" + str(MonthOfBirth) +"/" + str(YearOfBirth) +"(" + gender + ")" + "\n" + district + ", " + village
        print(to_display_data)
        ocr_text_tkinter = tk.StringVar()
        ocr_text_tkinter.set(to_display_data)    
        self.Output = tk.Label(self.root,textvariable = ocr_text_tkinter,font=('arial', 25, 'normal'), bg="light cyan", justify='left')
        self.Output.grid(row=12,column=4,rowspan=8,columnspan=1)
# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-o", "--output", default="./Pictures",
help="path to output directory to store snapshots (default: current folder")
args = vars(ap.parse_args())

# start the app
pba = Application(args["output"])
pba.root.mainloop()

