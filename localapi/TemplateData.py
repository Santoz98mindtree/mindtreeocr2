# This class stores the vertices of the text boxes in which the data field
# is expected to be AFTER the image has been aligned with its proper template.
#
# key::
#	x1,y1 ------
#	|          |	field = ((x1, y1), (x2, y2))
#	|          |
#	|          |
#      	--------x2,y2
#
# Name of the class is formatted ST_O, where ST is a placeholder for the
# state/document's shortened abbreviation and O represents the orientation of the
# document or driver's license (V or H)
#
# The integer member of each class called "nameFormat" represents how many lines the
# name takes up in the image.
# 1 -> name takes up 1 line, assumed to be FN LN
# 2 -> name takes up 1 line, assumed to be LN, FN (comma separated)
# 3 -> name takes up 2 lines, LN on first line, FN on second.
# 4 -> name takes up 2 lines, FN on first line, LN on second.


    
class SA_H:
	state = "SOUTHERN AUSTRALIA"
	orientation = "HORIZONTAL"
	dob = ((585,311), (964,415))
	name = ((144,656), (723,742))
	address = ((152,745), (828,921))
	expiration = ((1110,318), (1488,411))
	nameFormat = 1
	
	
    
class WA_H:
	state = "WESTERN AUSTRALIA"
	orientation = "HORIZONTAL"
	dob = ((188,247), (336,284))
	name = ((15,142), (208,189))
	address = ((14,185), (249,230))
	expiration = ((15,245,), (168,289))
	nameFormat = 3