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
import requests
import subprocess
import sys
import RPi.GPIO as GPIO
import threading
import picamera
import pytesseract

patient_details = []
bilder = "demo.jpg"
flag = 0
delete_flag = 0
url = 'http://192.168.0.134:12000/api/ocr_demographics'
os.system("sudo modprobe bcm2835-v4l2") # to recognize PiCamera as video0

def keep_alphanumerical(data):
    alphanumeric = ""
    for character in data:
        if character.isalnum():
            alphanumeric += character
    return alphanumeric;

def restart_program():
    """ helps restart program after hitting recapture button without saving data"""
    python = sys.executable
    os.execl(python, python, * sys.argv)
def do_picam(app):
    global toScan
    global shot
    global texte
    global texmed
    global delete_flag
    global txt_display
    camera = picamera.PiCamera()
    camera.brightness = 50
    camera.resolution = (1920,720) #This resolution works better for barcode decoding
    camera.color_effects = (128,128) #Turn camera to black and white
    #camera.crop = (0.0,0.0,3.1,0.53) #crop image to take label only  
    camera.capture(bilder)
    os.system("convert -density 360 /home/pi/Documents/demo.jpg /home/pi/Documents/demo.jpg")
    camera.stop_preview()
    camera.close() # close Picamera to free resources  to restart the video stream
    shot = bilder
    app.tesseractAnalysis()
    app.video_loop()
    delete_flag = 1

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
        
        self.botShoot = tk.Button(self.root,width=12,height=4,bd=4,font=('arial', 14, 'bold'),  text="CAPTURE", activebackground="cyan",bg = "cyan")
        self.botShoot.grid(row=12, column=18,pady=20)
        self.botShoot.configure(command=self.picam)        
        
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
            self.panel.config(image=imgtk)  # show the imag
        self.root.after(1, self.video_loop)  # call the same function after 30 milliseconds
        if flag ==0:
            flag = 1
            #self.show_thumb()
            
    def picam(self):
        self.vs.release() # release the camera to get all resources
        t = threading.Thread(target=do_picam, args=(self,))
        t.start()
                           
    def enable_buttons(self):
        self.botShoot.configure(state="normal")
        self.botSave.configure(state="normal")
        
    #sending the data to the server   
    def save_process(self):
        patient_info = {'first_name' : patient_details[0],'middle_name' : patient_details[2],'last_name' : patient_details[2],'npid' : patient_details[3],'dob': patient_details[4], 'gender' : patient_details[5],'gender' : patient_details[6]}
        x = requests.post(url, data = patient_info)
        print(x)     
    #OCR and Decode QR-Code and Barcode (Function under constraction)
    def tesseractAnalysis(self):
        self.botRestart = tk.Button(self.root,width=12,height=4,bd=4,font=('arial', 14, 'bold'),  text="RE-CAPTURE", activebackground="cyan",bg = "cyan")
        self.botRestart.grid(row=12, column=18,pady=20)
        self.botRestart.configure(command=restart_program)   
        self.vs.set(cv2.CAP_PROP_FRAME_WIDTH,640)
        self.vs.set(cv2.CAP_PROP_FRAME_HEIGHT,200)
        validMonths = set(['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'])
        invalidYear = "????"
        invalid_Day_or_Month = "??"
        verified_id = ""
        get_id = ""
        
        # Find barcode and Decode
        decodedObjects = pyzbar.decode(cv2.imread(bilder))
        for obj in decodedObjects:
            get_id = str(obj.data)
        split_get_id = get_id.split("'")
        id_only = split_get_id[1]
        print(id_only)
        #Extracring OCR Data
        ocr_text = pytesseract.image_to_string(Image.open(bilder), lang="eng")
        print(ocr_text)
        ocr_text_split = ocr_text.split(", ",1) #splitting text with comma into two values array
        if not ocr_text_split:
            print("List not Valid")    
        ocr_text_splitted = ocr_text_split[0].split("\n")
        if not ocr_text_splitted:
            print("List not Valid")
        print(ocr_text_splitted)
        while("" in ocr_text_splitted):
            ocr_text_splitted.remove("")
        full_name = ocr_text_splitted[0] #get the full name from first line
        split_full_name = full_name.split(" ")
        if not split_full_name:
            print("List not Valid")
        if len(split_full_name) < 3:
            first_name = keep_alphanumerical(split_full_name[0]);
            middle_name = ""
            last_name = keep_alphanumerical(split_full_name[1]);      
        else:
            first_name = keep_alphanumerical(split_full_name[0]);
            middle_name = keep_alphanumerical(split_full_name[1]);
            last_name = keep_alphanumerical(split_full_name[2]);
               
        print(first_name + " " +last_name)
        
        take_date = ocr_text_splitted[1].split(" ")
        if not take_date:
            print("List not Valid")
        
        get_id_ocr = take_date[0].replace("-","") #Getting id from OCR to later compare with one from barcode 
        #print(get_id_ocr)
        #checking barcode id and OCR id
        new_verified_id = id_only[:5] + '-' + id_only[5:]
        verified_id = new_verified_id[:10] + '-' + new_verified_id[10:] 
        
        if get_id_ocr == id_only:
            print("OCR is Okay ")
        else:
            print("OCR is Poor")
        #Processing Date Validation   
        date_taken = take_date[1].split("/")
        if not date_taken:
            print("List not Valid")
        else:
            DayOfBirth = date_taken[0] #Extract Day from date
            MonthOfBirth = date_taken[1] #Extract Month from date
            print(date_taken)
            take_year = date_taken[2].split("(")
            if not take_year:
                print("List not Valid")
            YearOfBirth = take_year[0] #Extract Year from date        
            # Validating the Year Captured from OCR
            if "?" in YearOfBirth:
                YearOfBirth = invalidYear
                print(YearOfBirth)        
            else:
                YearOfBirth = int(YearOfBirth)
                if YearOfBirth < 1920 or YearOfBirth > 2025:
                    YearOfBirth = invalidYear
                    print(YearOfBirth)         
            # Validating the Month Captured from OCR
            MonthOfBirth = MonthOfBirth.upper()
            if MonthOfBirth not in validMonths:
               MonthOfBirth = invalidYear           
            print(MonthOfBirth)
            # Validating the Day Captured from OCR
            if "?" in DayOfBirth:
                DayOfBirth = invalid_Day_or_Month
                print(DayOfBirth)
            else :
                if YearOfBirth != invalidYear:
                    if MonthOfBirth != invalid_Day_or_Month:
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
                            DayOfBirth = invalid_Day_or_Month
                            print(DayOfBirth)
                    else: DayOfBirth = invalid_Day_or_Month
                else: DayOfBirth = invalid_Day_or_Month
                        
            #processing Gender
            gender = keep_alphanumerical(take_year[1].rstrip(")"));
            print(gender)
            #Start coding from here !!!
            # Process District 
            district = ocr_text_splitted[2];
            district = re.sub(r'[^A-Za-z0-9 ]+', '', district) #Check alphanumerical and observe any space spaces
            print(district)
            
            #Process village
            home_village  = ocr_text_split[1].split("\n")
            village = keep_alphanumerical(home_village[0]);
            print(village)
            address = district + ", " + village
            
            #Creating an Array to pass data to Server
            patient_details.append(first_name)
            patient_details.append(middle_name)
            patient_details.append(last_name)
            patient_details.append(verified_id)
            patient_details.append(str(DayOfBirth) +"/" + str(MonthOfBirth) +"/" + str(YearOfBirth)) #Date of Birth
            patient_details.append(gender)
            patient_details.append(address)
            patient_details.append(village)
            print(patient_details)
            #Data to display on user Interface
            to_display_data = first_name + " " + middle_name + " " + last_name + "\n" + verified_id + " " + str(DayOfBirth) +"/" + str(MonthOfBirth) +"/" + str(YearOfBirth) +"(" + gender + ")" + "\n" + address
            print(to_display_data)
            ocr_text_tkinter = tk.StringVar()
            ocr_text_tkinter.set(to_display_data)    
            self.Output = tk.Label(self.root,textvariable = ocr_text_tkinter,font=('arial', 25, 'normal'), bg="light cyan", justify='left')
            self.Output.grid(row=12,column=4,rowspan=8,columnspan=1)
                    
            #!!Button to be changed to save function soon
            self.botSave = tk.Button(self.root,width=12,height=4,bd=4,font=('arial', 14, 'bold'), text="SAVE", activebackground="light blue",bg = "light green")
            self.botSave.grid(row=13,column=18)
            self.botSave.configure(command=self.save_process)
# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-o", "--output", default="./Pictures",
help="path to output directory to store snapshots (default: current folder")
args = vars(ap.parse_args())

# start the app
pba = Application(args["output"])
pba.root.mainloop()

