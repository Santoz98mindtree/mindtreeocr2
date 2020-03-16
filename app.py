import ScanID
from flask import Flask, request
import cv2
import numpy
from PIL import Image


#from flask_restful import Resource, Api
app = Flask(__name__)

@app.route('/RequestImageWithMetadata', methods=['POST'])
def post():
    #request_data = request.form['some_text']
    #print(request_data)
    #s = StringIO()
    imagefile = request.files.get('imagefile', '')
    if imagefile:
        extension = imagefile.filename.split(".")[-1]
        if extension not in ('png', 'jpg', 'jpeg'):
            return {"result" : 0, "message": "File Format Error"}
        #imagefile.save(s)
    #cv2.imshow(imagefile)
    #im=Image.open(s)
    filestr = request.files['imagefile'].read()
    npimg = numpy.fromstring(filestr, numpy.uint8)
    #imagefile.save('D:/temp/test_image.jpg')

    return  {"data":ScanID.passed(npimg)} 

app.run(port=5000)