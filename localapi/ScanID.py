#	This program functions as a document scanner and reader. It expects input to be passed in to the program
#	in the form of a jpg or png filetype. The program will identify what kind of document has been submitted and
#	read in its info, then assign the data to an object for further processing.

 
import imutils
import os
import cv2
import sys
import Document as document
import Transform as transform
import numpy as np
import Config as config
import json
from PIL import Image

#start of main
#	This function serves as a driver by passing images into various methods and modules, and directing the
#	responses into the correct modules and functions. Returns an object for the respective doctype that holds
#	the data found in the image.
def passed(npimg):
	#print(imgpath)
	#fullpath='D:/temp/test_image.jpg'
	img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
	#cv2.imshow(img)
	#img = cv2.imread(npimg)
	
	#add file extension if the entry did not already have it.
	#if fullPath.endswith(".png") or fullPath.endswith(".jpg") or fullPath.endswith(".jpeg"):
		#img = cv2.imread(fullPath)
         #print("etst")
	#else:
		#if os.path.isfile(fullPath + ".png"):
			#img = cv2.imread(fullPath + ".png")
		#elif os.path.isfile(fullPath + ".jpg"):
			#img = cv2.imread(fullPath + ".jpg")
		#elif os.path.isfile(fullPath + ".jpeg"):
			#img = cv2.imread(fullPath + ".jpeg")
		#elif fullPath.endswith(".pdf"):
			#img = None	
		#elif os.path.isfile(fullPath + ".pdf"):
			#img = None
		#else:
			#img = None
	
	if img is None:
		print("Image could not be opened.")
		sys.exit(0)


    
	#call to removeBorder, removes border from image and warps perspective if edges can be detected
	#removeBorder() will return false if the image contains background, or true if removeBorder()
	#was not able to locate the document, and the document still has the original background..
	imgNoBackground, background = transform.removeBackground(img)	
		
	#prescreen
	if preScreen(imgNoBackground) is False:
		print("Image quality too low, try retaking.")
		sys.exit(0)

	#search for best template match, image object assigned to the template variable, template name stored in docType
	template, docType = selectTemplate(imgNoBackground, background)
	#line up the input image with the selected template so that the data will be exactly where we expect
	imgAligned = alignToTemplate(img, template)
	#call to the document 'constructor', which will set up the object and read ROIs based on the info. passed
	myDoc = document.documentFromImage(imgAligned, docType)
	#call to object's toString() method.
	#print("\n" + myDoc.__str__())
	return myDoc.__str__()
#end of main


#start of preScreen()
#	This function performs a very simple prelim check on the image before template match/align is attempted. It
#	takes the result from the call to removeBorder() and measures the darkness and blur of the image. If one of
#	these values is too low, the method returns false to the calling function. Else, returns true
def preScreen(img):
	#convert image to greyscale, get the variance of laplacian distribution
	gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	focusMeasure = cv2.Laplacian(gray, cv2.CV_64F).var()
	
#	print("Focus measure: {}".format(focusMeasure))
	
	#check whether the value is above or beneath the threshold for blur
	if focusMeasure < config.BLUR_THRESHOLD:
		return False

	#measure the mean darkness level for the image
	#(more true to document readability when background is successfully removed)
	light = np.mean(img)

#	print("Darkness level: {}".format(light))	

	if light < config.DARKNESS_THRESHOLD:
		return False

	return True
#end of preScreen

	
#start of selectTemplate
#	This function is passed an image, the flag returned from removeBorder() and the location of the folder containing the tepmlates
#	file system. The program first checks if the background is still in the image. If there is not a background, the function
#	can tell without using any searching/matching process whether the license is vertical or horizontal based on aspect ratio.
#	Then, the function loops through all the identifiers that distinguish each category of document. After this search, the 
#	function checks whether it has enough information to identify the document it has. If it does, it returns the template and
#	the corresponding name of the template. If it does not, it performs a secondary search which looks for unique identifiers
#	for each derived form of the document, then returns the best match.
def selectTemplate(img, background, location=config.SRC_PATH):
	h,w = img.shape[:2]
	orientation = ""
   

	#check if image still contains background. If it does not, we can figure out whether the document submitted is horizontal or
	#vertical based on ratio of h:w
	if not background:
		h,w = img.shape[:2]
		if h > w: #document is vertical
			orientation = "_V"
		elif w > h: #document is horizontal
			orientation = "_H"


	form = multiScaleTemplateSelect(img, location, background).split('.')[0]
    

	#update location to be the subdirectory containing all of the images for the specified form
	location = location + form + "/"
	#update form so that it will contain the filename and orientation if orientation was already determined
	form += orientation	
	
	#check if the file we're looking for with the specified form and orientation exists.
	if os.path.isfile(location + form + ".jpg"):
		bestTemplate = cv2.imread(location + form + ".jpg")
	elif os.path.isfile(location + form + ".png"):
		bestTemplate = cv2.imread(location + form + ".png")
	elif background is True:
		#Folder will have a /Features subdirectory if there is more than one form of the doctype
		if os.path.exists(location + "Features/"):
			#go into features subdirectory, this contains all the unique features for each license type.
			#The best match will contain
			bestFeatureMatch = multiScaleTemplateSelect(img, location + "Features/", background)
			form = form + "_" +  bestFeatureMatch.split("_")[1].split('.')[0]
		#Else, the only image in the directory should be the correct form.
		else:
			for filename in os.listdir(location):
				if filename.endswith(".png") or filename.endswith (".jpg"):
					form  = filename.split(".")[0]

		#now that we have form name, attempt to read the CORRECT template from the /Templates/State/ folder.
		bestTemplate = None
		bestTemplate = cv2.imread(location + form + ".jpg")
		if bestTemplate is None:
			bestTemplate = cv2.imread(location + form + ".png")

	print("FORM: {}".format(form))
	return bestTemplate, form
#end of selectTemplate
		

def multiScaleTemplateSelect(img, location, background):
	grayImg = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	grayImg = cv2.GaussianBlur(grayImg, (3,3), 0)
	
	#resize to help the algorithm run faster
	if grayImg.shape[0] > grayImg.shape[1]: #if height > width
		grayImg = imutils.resize(grayImg, height=500)
	elif grayImg.shape[1] > grayImg.shape[0]:
		grayImg = imutils.resize(grayImg, width=500)

	bestScore = 0
	bestMatch = None

	#Loop through all files in the subdirectory stored in the variable location
	for filename in os.listdir(location):
		if filename.endswith(".png") or filename.endswith(".jpg"): #All the templates expected to be jpg/png files
			if bestMatch is None:
				bestMatch = filename			

			template = cv2.imread(location + filename)
			template = imutils.resize(template, height=35)
			grayTemplate = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
			grayTemplate = cv2.GaussianBlur(grayTemplate, (1,1), 0)
			(tH, tW) = template.shape[:2]

			#Loops through 30 different scaled images in the range from 100% to 10% the image's size.
			for scale in np.linspace(0.1, 1.0, 30)[::-1]:
				resized = imutils.resize(grayImg, width=int(grayImg.shape[1] * scale))

				#Break if the resized image is smaller than the template.	
				if resized.shape[0] < tH or resized.shape[1] < tW:
					break

				#Edge detection
				edgedImg = cv2.Canny(resized, 50, 250)
				edgedTemplate = cv2.Canny(grayTemplate, 50, 250)
				
				#get list of matches, compare best match score to bestScore
				result = cv2.matchTemplate(edgedImg, edgedTemplate, cv2.TM_CCORR_NORMED)
				minScore,maxScore,_,_ = cv2.minMaxLoc(result)	
					
				if maxScore > bestScore:
					bestScore = maxScore
					bestMatch = filename
					#more than a 50% match is a pretty good match. This is to save time on the search.
					if maxScore > 0.5:
#						print("BEST MATCH: {}, SCORE: {},".format(bestMatch,bestScore)) #TODO remove -- debug
						return bestMatch

#	print("BEST MATCH: {}, SCORE: {}".format(bestMatch, bestScore)) #TODO remove-- this was for debug
	return bestMatch
#end of multiScaleTemplateSelect


def alignToTemplate(img, template):
	#image prep to improve OCR and alignment
	imgClean = cleanImage(img)
	templateClean = cleanImage(template)
	# Detect image keypoints & descriptors using the BRISK algorithm
	brisk = cv2.BRISK_create()
	imgKeypoints, imgDescriptors = brisk.detectAndCompute(imgClean, None)
	templateKeypoints, templateDescriptors = brisk.detectAndCompute(templateClean, None)
	# Match corresponding features between the images
	descriptorMatcher = cv2.DescriptorMatcher_create(cv2.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING)
	matches = descriptorMatcher.match(imgDescriptors, templateDescriptors, None)
	# Sort matches by score, and we only want to care about the best x% of matches.
	matches.sort(key=lambda m: m.distance, reverse=False)
	numGoodMatches = int(len(matches) * config.GOOD_MATCH_PERCENT)
	matches = matches[:numGoodMatches]	
	# Pull the coordinates of the best matches
	imgPoints = np.zeros((len(matches), 2), dtype=np.float32)
	templatePoints = np.zeros((len(matches), 2), dtype=np.float32)
	
	for i, match in enumerate(matches):
		imgPoints[i,:] = imgKeypoints[match.queryIdx].pt
		templatePoints[i,:] = templateKeypoints[match.trainIdx].pt
	
	# find homography matrix
	h, _ = cv2.findHomography(imgPoints, templatePoints, cv2.RANSAC)

	# make sure calculated matrix doesn't attempt to perform an invalid warp
	if checkHomography(h, img.shape[1], img.shape[0]) is False:
		print("Invalid results. Please try re-submitting.")	
		sys.exit(0)
	
	# apply homography, warping the image to appear as if it were directly below the camera.
	height, width, channels = template.shape
	imgAligned = cv2.warpPerspective(img, h, (width, height))
	return imgAligned
#end of alignToTemplate


def checkHomography(h, imWidth, imHeight):
	#initialize each point as a 1x3 matrix (so that it can be multiplied by the 3x3 homography).
	a = np.array([0,0,1]) # top L
	b = np.array([imWidth,0,1]) # top R
	c = np.array([imWidth,imHeight,1]) # bottom R
	d = np.array([0,imHeight,1]) # bottom L
	#multiply each point by the homography, store the points the transformation produced
	warped = np.array([h.dot(a)[:2], h.dot(b)[:2], h.dot(c)[:2], h.dot(d)[:2]])
	#call to orderPoints, which orders a set of 4 points clockwise starting with the Top Left point at index 0
	ordered = transform.orderPoints(warped)
	#now, we'd expect that even though the warped array may start on a different element, the order should not have changed.
	start = warped[0]
	j = 0
	for point in ordered:
		if isclose(start[0],point[0]) and isclose(start[1], point[1]):
			break
		else:
			j += 1
	#first loop breaks when the start index in the ordered array is found
	#next, walk through both arrays array, check that order is the same.
	for i in range(0,4):
		if j > 3:
			j = 0
		#check the two points for 'close to' equality to account for rounding errors.
		if isclose(warped[i][0], ordered[j][0]) and isclose(warped[i][1], ordered[j][1]):
			j += 1
		else:
			return False
	return True
#end of checkHomography()


def isclose(a,b,rel_tol=.05,abs_tol=0.0):
	return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
#end of isclose()


def drawBoxes(img, docType):
	templateData = getattr(templates, docType)
	# coordinates of each field are stored as a tuple in the corresponding class for the DL
	# dob
	coords = getattr(templateData, "dob")
	cv2.rectangle(img, coords[0], coords[1], (0,255,0), 3)
	# name
	coords = getattr(templateData, "name")
	cv2.rectangle(img, coords[0], coords[1], (0,255,0), 3)
	# address
	coords = getattr(templateData, "address")
	cv2.rectangle(img, coords[0], coords[1], (0,255,0), 3)	
	# expiration
	coords = getattr(templateData, "expiration")
	cv2.rectangle(img, coords[0], coords[1], (0,255,0), 3)
	return img
#end of drawBoxes


def cleanImage(img):
        # img prep (color, blur correction, noise removal)
	imgClean = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	imgClean = cv2.GaussianBlur(imgClean, (5,5), 0) 
	return imgClean
#end of cleanImage


#call to main
#if __name__ == "__main__":
 #   main()	
