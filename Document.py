import cv2
import numpy as np
import TemplateData as templates
import imutils
from unidecode import unidecode
import io
#from google.cloud import vision
import os
os.environ["COMPUTER_VISION_SUBSCRIPTION_KEY"]="8e5751df533b46058bddd9b5cebb6fa5"
os.environ["COMPUTER_VISION_ENDPOINT"]="https://centralindia.api.cognitive.microsoft.com/"
import requests
import sys
import time
from matplotlib.patches import Polygon
from PIL import Image
from io import BytesIO

if 'COMPUTER_VISION_SUBSCRIPTION_KEY' in os.environ:
    subscription_key = os.environ['COMPUTER_VISION_SUBSCRIPTION_KEY']
else:
    print("\nSet the COMPUTER_VISION_SUBSCRIPTION_KEY environment variable.\n**Restart your shell or IDE for changes to take effect.**")
    sys.exit()

if 'COMPUTER_VISION_ENDPOINT' in os.environ:
    endpoint = os.environ['COMPUTER_VISION_ENDPOINT']

ocr_url = endpoint + "vision/v2.1/read/core/asyncBatchAnalyze"
headers = {'Ocp-Apim-Subscription-Key': subscription_key, 'Content-Type': 'application/octet-stream'}
params = {'language': 'unk', 'detectOrientation': 'true'}

#start of Document base class
class Document:
	templateName = ''
	category = ''
#end of Document class


#start of Driver's License Class
class License(Document):
	state = ''
	orientation = ''
	dob = '0/0/0000'
	first = ''
	last = ''
	address = ''
	expiration = ''

	#Driver's License Constructor
	def __init__(self, image, docType):
		#access the template's data for thei given license format
		templateData = getattr(templates, docType)
		self.templateName = docType
		self.category = "DRIVER'S LICENSE"		
		self.orientation = getattr(templateData, "orientation")
		self.state = getattr(templateData, "state")
		
		#get coordinates of ROIS from the document template
		
		#Figure out how to process the full name into the FN/LN fields based
		#on how the name is formatted (order of fields, commas/not, number of lines, etc.)
		nameFormat = getattr(templateData, "nameFormat")
		#crop out each ROI by retrieving coordinates for each field from the template.
		box = getattr(templateData, "name")
		name = image[box[0][1]:box[1][1], box[0][0]:box[1][0]]
		box = getattr(templateData, "dob")
		dob = image[box[0][1]:box[1][1], box[0][0]:box[1][0]]
		box = getattr(templateData, "expiration")
		expiration = image[box[0][1]:box[1][1], box[0][0]:box[1][0]]
		box = getattr(templateData, "address")
		address = image[box[0][1]:box[1][1], box[0][0]:box[1][0]]
		#add a white border to each image
		name = cv2.copyMakeBorder(name, 100, 100, 100, 100, cv2.BORDER_CONSTANT, value=(255,255,255))
		dob = cv2.copyMakeBorder(dob, 100, 100, 100, 100, cv2.BORDER_CONSTANT, value=(255,255,255))
		expiration = cv2.copyMakeBorder(expiration, 100, 100, 100, 100, cv2.BORDER_CONSTANT, value=(255,255,255))
		address = cv2.copyMakeBorder(address, 100, 100, 100, 100, cv2.BORDER_CONSTANT, value=(255,255,255))		
		#compute width of the new image, resize each field so they stack evenly
		maxWidth = max(name.shape[1], dob.shape[1], expiration.shape[1], address.shape[1])
		name = imutils.resize(name, width=maxWidth)		
		dob = imutils.resize(dob, width=maxWidth)
		expiration = imutils.resize(expiration, width=maxWidth)
		address = imutils.resize(address, width=maxWidth)	
		#record the interval where we laid each region so that we can break up the response body.
		nameRegion = (0, name.shape[0])
		dobRegion = (nameRegion[1], nameRegion[1] + dob.shape[0])
		expirationRegion = (dobRegion[1], dobRegion[1] + expiration.shape[0])
		addressRegion = (expirationRegion[1], expirationRegion[1] + address.shape[0])	
		#concatenate each image on top of one another
		combined1 = np.concatenate((name, dob), axis=0)
		combined2 = np.concatenate((expiration, address), axis=0)
		combined = np.concatenate((combined1, combined2), axis=0)		
		
		tempFile = "C:/Users/m1053826/Downloads/microtest/test.png"
		cv2.imwrite(tempFile, combined)


		with io.open(tempFile, 'rb') as image_file:
			content = image_file.read()
			#image = vision.types.Image(content=content)
		response = requests.post(ocr_url, headers=headers,  data = content)
		response.raise_for_status 
		#print(response.json())
		operation_url = response.headers["Operation-Location"]
		analysis = {}
		poll = True
		while (poll):
		    response_final = requests.get(
		        response.headers["Operation-Location"], headers=headers)
		    analysis = response_final.json()
		    #print(analysis)
		    time.sleep(1)
		    if ("recognitionResults" in analysis):
		        poll = False
		    if ("status" in analysis and analysis['status'] == 'Failed'):
		        poll = False
		polygons = []
		if ("recognitionResults" in analysis):
		    polygons = [(line["boundingBox"], line["text"])
		                for line in analysis["recognitionResults"][0]["lines"]]

		nameText1 = "" #first line of name
		nameText2 = "" #second line of name (if applicable)
		dobText = ""
		expText = ""
		addrText = ""
		#get full text body to preserve newlines
		#body = labels[0].description.split("\n")
		#go through each label, map each one to a field based on location
		for polygon in polygons:
			center, text = processLabel(polygon)

			#separate response into different fields based on where we know it should have been located
			if center[1] >=  nameRegion[0] and center[1] <= nameRegion[1]:
				#we expect name to always be the top image, and therefore the first 1-2 lines of the
				#response. Check which line the name appeared in, and add it to the respective string.
				if nameFormat ==1 : #first line
					nameText1 += unidecode(text) + " "
				elif  nameFormat > 2: #second line
					nameText2 += unidecode(text) + " "
			elif center[1] >= dobRegion[0] and center[1] <= dobRegion[1]:
				dobText += unidecode(text)
			elif center[1] >= expirationRegion[0] and center[1] <= expirationRegion[1]:
				expText += unidecode(text)
			elif center[1] >= addressRegion[0] and center[1] <= addressRegion[1]:
				addrText += unidecode(text) + " "
		nameText = nameText1.strip() + "\n" + nameText2.strip()
		#assign text to object
		self.last, self.first = parseName(nameText.strip(), nameFormat)
		self.dob = dobText.strip()
		self.expiration = expText.strip()
		self.address = addrText.strip()
	#end of Driver's License Constructor

	#Driver's License toString()
	def __str__(self):
		temp = ''
		temp = temp + 'TYPE:\t' + self.category + '\n'
        #temp = temp + 'STATE:\t' + self.state + '\n'
		temp = temp + 'ORIEN:\t' + self.orientation + '\n'
		temp = temp + 'FIRST:\t' + self.first + '\n'
		temp = temp + 'LAST:\t' + self.last + '\n'
		temp = temp + 'DOB:\t' + self.dob + '\n'
		temp = temp + 'EXP:\t' + self.expiration + '\n'
		temp = temp + 'ADDR:\t' + self.address + '\n'
		temp=''
		temp='{state:'+self.state+',first_name:'+self.first+',last_name:'+self.last
		temp=temp+',dob:'+self.dob+',expiry:'+self.expiration+',address:'+self.address+'}'
		return temp
	#end of Driver's License toString()
#end of Driver's License class	





def documentFromImage(img, docType):
	if docType.startswith("SSN"): #social security
		document = SocialSecurity(img)
	elif docType.startswith("PP"): #passport
		document = None # TODO create passport constructor
	else: #driver's license
		document = License(img, docType)
	return document
#end of documentFromImage


def parseName(name, nameFormat):
	try:
		if nameFormat == 1: #FN LN
			#If there are no delimiters, the entire string will be returned in the place of the FN.
			names = name.split()
			return names[1].strip(), names[0].strip()
		elif nameFormat == 2: #LN, FN
			names = name.split(",")
			if len(names) == 1:
				#sometimes comma misread as hyphen
				names = name.split("-")
			if len(names) == 1:
				#commas can be misread as a period
				names = name.split(".")
			return names[0].strip().replace(",",""), names[1].strip().replace(",","")
		elif nameFormat == 3: #LN\nFN
			names = name.split(",")
			return names[0].strip(), names[1].strip()
		elif nameFormat == 4: #FN\nLN
			names = name.split("\n")
			return names[1].strip(), names[0].strip()
		else:
			#invalid nameFormat identifier (see templateData.py for correct formats)
			return "", ""
	except:
		return "", name.strip()
#end of parseName


def processLabel(polygon):
	text = polygon[1]
	centerX = 0
	centerY = 0		
	
	#calculate the center of the polygon
	for i in range(0, len(polygon[0]),2):
	    centerX += polygon[0][i]
	    centerY +=  polygon[0][i+1]
	centerX = centerX /(len(polygon[0])/2)
	centerY = centerY /(len(polygon[0])/2)
  #print(centerX)
	return (centerX, centerY), text
#end of processLabel
