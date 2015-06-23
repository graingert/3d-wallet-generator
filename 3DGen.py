#!/usr/bin/python3

from libs import qr_tools as qrTools
from libs import TextGenerator as textGen
import bitcoin # sudo pip3 install bitcoin
import argparse
import time
import math
import sys

def parse_args():
	parser = argparse.ArgumentParser(description='Generate an STL file of a 3D-printable bitcoin, litecoin, dogecoin, or other type of coin.', formatter_class=argparse.RawTextHelpFormatter)
	parser.add_argument('-ve', '--version', dest='versionByte', type=int, default=0, help='Version Bit of the address (for other altcoins).\nBitcoin: 0\n Litecoin: 48\n Dogecoin: 30')
	parser.add_argument('-ct', '--coin-title', dest='coinTitle', type=str, default="Bitcoin", help='Title of the coin, used for design purposes')
	parser.add_argument('-ls', '--layout-style', dest='layoutStyle', type=int, default=2, help="Layout style of the wallet.\n1) Address on the Front, Private Key on the back\n2) Private Key Only\n3) Address Only (don't forget to export the Private Keys after)")
	parser.add_argument('-wi', '--width', dest='walletWidth', type=float, default=54.0, help='The width of the wallet in mm. The length is calculated automatically. Default option is approximately standard credit card legnth and width.')
	parser.add_argument('-he', '--height', dest='walletHeight', type=float, default=8.0, help='The height of the wallet in mm.')
	parser.add_argument('-bo', '--black-offset', dest='blackOffset', type=int, default=-30, help='The percentage of the height that the black part of the QR code, and the text, will be raised or lowered by.\nNegative number for lowered, positive for raised.  Option must be greater than -50.')
	parser.add_argument('-ec', '--qr-error-correction', dest='errorCorrection', type=str, default="M", help='The percentage of the QR codes that can be destroyed before they are irrecoverable\nL) 7%\nM) 15%\nQ) 25%\nH) 30%')
	parser.add_argument('-rc', '--round-corners', dest='roundCorners', action='store_true', help="Round the coners (four short edges) of the wallet.")
	parser.add_argument('-co', '--copies', dest='copies', type=int, default=5, help='The number of wallets to generate. These will all be unique and randomly-generate wallets (not copies).')
	parser.add_argument('-o', '--stl-folder', dest='outputSTLFolder', type=str, default="./WalletsOut/", help='The output folder to export the STL files into')
	parser.add_argument('-oc', '--scad-folder', dest='outputSCADFolder', type=str, default='', help='The output folder to store the SCAD generation files in (optional, only used for debugging)')
	parser.add_argument('-ea', '--export-address-csv', dest='exportAddressCSV', type=str, default='', help='The output CSV file to export the address list to (optional)')
	parser.add_argument('-ep', '--export-privkey-csv', dest='exportPrivkeyCSV', type=str, default='', help='The output CSV file to export the private key list to (optional)')
	parser.add_argument('-eap', '--export-address-privkey-csv', dest='exportAPCSV', type=str, default='', help='The output CSV file to export the address and private key list to, in the format of "address,privkey" (optional)')
	parser.add_argument('-epa', '--export-privkey-address-csv', dest='exportPACSV', type=str, default='', help='The output CSV file to export the address and private key list to, in the format of "privkey,address" (optional)')
	return parser.parse_args()

args = parse_args()

# Generate the addresses
if args.copies < 1:
	print("Please enter a valid number of copies (-co flag), and try again.")
	sys.exit()
else: # Use an else statement here just in case we add the option to import a CSV file with the keys (generated somewhere else)
	walletDataList = []
	for i in range(args.copies):
		thisData = {}

		# Generate the addresses with keys
		thisData["privateKey"] = bitcoin.main.random_key() # Secure: uses random library, time library and proprietary function
		thisData["wif"] = bitcoin.encode_privkey(thisData["privateKey"], "wif", args.versionByte)
		thisData["address"] = bitcoin.privkey_to_address(thisData["privateKey"], args.versionByte)

		# Generate the QR codes
		if args.errorCorrection.upper() not in ["L","M","Q","H"]:
			print("Please select a valid QR Error Correction value (L, M, Q, or H).")
			sys.exit()
		thisData["wifQR"] = qrTools.getQRArray(thisData["wif"], args.errorCorrection.upper())
		thisData["addressQR"] = qrTools.getQRArray(thisData["address"], args.errorCorrection.upper())

		# Append ALL the wallet information, just in case we want to do something with it later
		walletDataList.append(thisData) 

# Validate other args and set some constants
walletWidth = args.walletWidth
walletHeight = args.walletHeight
if args.layoutStyle == 1 or args.layoutStyle == 2 or args.layoutStyle == 3:
	walletLength = walletWidth*1.6 # Approximately the same ratio as a credit card
else:
	print("Please choose a valid layout style option.")
	sys.exit()
if args.blackOffset < -50.0:
	print("Please ensure that --black-offset (-bo flag) is set correctly, and is greater than -50.")
	sys.exit()
textDepth = (args.blackOffset/100) * walletHeight

# Set the master SCAD variable
masterSCAD = "// SCAD Code Generated By 3DGen.py - 3D Wallet Generator\n\n" # The beginning of the wallet are identical
scadOutputs = [] # Generated from loop for each wallet (different addresses)

# Include some modules at the beginning
masterSCAD += "// Import some modules\n"
moduleFile = open("scad/roundCornersCube.scad","r")
masterSCAD += moduleFile.read()
masterSCAD += "\n\n"
moduleFile.close()

# Draw the main prism
if args.roundCorners:
	mainCube = "roundCornersCube(" + str(walletLength) + "," + str(walletWidth) + "," + str(walletHeight) + ");"
else:
	mainCube = "cube([" + str(walletLength) + "," + str(walletWidth) + "," + str(walletHeight) + "]);"
mainCube += "\n\n"

# Init a variable to keep all the additive/subtractive parts
finalParts = []

# Break into the loop for each wallet
for data in walletDataList:
	# 'data' = wif, address, wifQR, addressQR

	# Generate the texts
	addressLine1 = data["address"][:math.ceil(len(data["address"])/2.0)]
	addressLine2 = data["address"][math.ceil(len(data["address"])/2.0):]
	wifLine1 = data["wif"][:17]
	wifLine2 = data["wif"][17:34]
	wifLine3 = data["wif"][34:]

	addressLine1Dots = textGen.getArray(addressLine1)
	addressLine2Dots = textGen.getArray(addressLine2)
	wifLine1Dots = textGen.getArray(wifLine1)
	wifLine2Dots = textGen.getArray(wifLine2)
	wifLine3Dots = textGen.getArray(wifLine3)

	bigTitle = textGen.getArray("3D " + args.coinTitle + " Wallet")
	addressTitle = textGen.getArray("Address")
	privkeyTitle = textGen.getArray("Private Key")

	# Create the big title union so that it can be sized and moved
	bigTitleUnion = "union(){"
	for rowIndex in range(len(bigTitle)):
		row = bigTitle[rowIndex]
		for colIndex in range(len(row)):
			if row[colIndex] == '1':
				translateHeight = walletHeight if textDepth>0 else walletHeight+textDepth
				bigTitleUnion += "translate([colIndex,rowIndex,translateHeight]){cube([1,1,textDepth]);}".replace('colIndex',str(colIndex)).replace('rowIndex',str(rowIndex)).replace('textDepth',str(abs(textDepth))).replace('translateHeight',str(translateHeight))
	bigTitleUnion += "}"

	# Translate the title to where it goes
	bigTitleFinal = "translate([(1/17)*length,(14/17)*width,0]){resize([(15/17)*length,0,0],auto=[true,true,false]){bigTitleUnion}}".replace('length',str(walletLength)).replace('width',str(walletWidth)).replace('bigTitleUnion',bigTitleUnion)
	if args.layoutStyle == 1:
		# Need to copy it on to the backside as well - rotate then move it, and then create a union of the two titles (front and back)
		bigTitle2 = "translate([length,0,height]){rotate(180,v=[0,1,0]){bigTitleFinal}}".replace('length',str(walletLength)).replace('height',str(walletHeight)).replace('bigTitleFinal',bigTitleFinal).replace('translateHeight',str(translateHeight))
		bigTitleFinal = "union(){\n" + bigTitleFinal + "\n" + bigTitle2 + "\n}\n\n"
	finalParts.append(bigTitleFinal)
	
	# Draw the word "Address" on the front, and draw on the actual address
	if args.layoutStyle == 1 or args.layoutStyle == 3:
		# Draw the address on the front
		addressParts = []

		# Create the address title union so that it can be sized and moved
		addressTitleUnion = "union(){"
		for rowIndex in range(len(addressTitle)):
			row = addressTitle[rowIndex]
			for colIndex in range(len(row)):
				if row[colIndex] == '1':
					translateHeight = walletHeight if textDepth>0 else walletHeight+textDepth
					addressTitleUnion += "translate([colIndex,rowIndex,translateHeight]){cube([1,1,textDepth]);}".replace('colIndex',str(colIndex)).replace('rowIndex',str(rowIndex)).replace('textDepth',str(abs(textDepth))).replace('translateHeight',str(translateHeight))
		addressTitleUnion += "}"
		addressTitleFinal = "translate([(11.25/17)*length,(7/11)*width,0]){resize([0,(3/55)*width,0],auto=[true,true,false]){addressTitleUnion}}\n\n".replace('length',str(walletLength)).replace('width',str(walletWidth)).replace('addressTitleUnion',addressTitleUnion)
		addressParts.append(addressTitleFinal)

		# Create the first line of the address
		addressLine1Union = "union(){"
		for rowIndex in range(len(addressLine1Dots)):
			row = addressLine1Dots[rowIndex]
			for colIndex in range(len(row)):
				if row[colIndex] == '1':
					translateHeight = walletHeight if textDepth>0 else walletHeight+textDepth
					addressLine1Union += "translate([colIndex,rowIndex,translateHeight]){cube([1,1,textDepth]);}".replace('colIndex',str(colIndex)).replace('rowIndex',str(rowIndex)).replace('textDepth',str(abs(textDepth))).replace('translateHeight',str(translateHeight))
		addressLine1Union += "}"
		addressLine1Final = "translate([(10/17)*length,(6/11)*width,0]){resize([0,(2/55)*width,0],auto=[true,true,false]){addressLine1Union}}\n\n".replace('length',str(walletLength)).replace('width',str(walletWidth)).replace('addressLine1Union',addressLine1Union)
		addressParts.append(addressLine1Final)

		# Create the second line of the address
		addressLine2Union = "union(){"
		for rowIndex in range(len(addressLine2Dots)):
			row = addressLine2Dots[rowIndex]
			for colIndex in range(len(row)):
				if row[colIndex] == '1':
					translateHeight = walletHeight if textDepth>0 else walletHeight+textDepth
					addressLine2Union += "translate([colIndex,rowIndex,translateHeight]){cube([1,1,textDepth]);}".replace('colIndex',str(colIndex)).replace('rowIndex',str(rowIndex)).replace('textDepth',str(abs(textDepth))).replace('translateHeight',str(translateHeight))
		addressLine2Union += "}"
		addressLine2Final = "translate([(10/17)*length,(5.5/11)*width,0]){resize([0,(2/55)*width,0],auto=[true,true,false]){addressLine2Union}}\n\n".replace('length',str(walletLength)).replace('width',str(walletWidth)).replace('addressLine2Union',addressLine2Union)
		addressParts.append(addressLine2Final)

		# Create the QR code
		addressQRUnion = "union(){"
		for rowIndex in range(len(data["addressQR"])):
			row = data["addressQR"][rowIndex]
			for colIndex in range(len(row)):
				if row[colIndex] == 0:
					translateHeight = walletHeight if textDepth>0 else walletHeight+textDepth
					addressQRUnion += "translate([colIndex,rowIndex,translateHeight]){cube([1,1,textDepth]);}".replace('colIndex',str(colIndex)).replace('rowIndex',str(rowIndex)).replace('textDepth',str(abs(textDepth))).replace('translateHeight',str(translateHeight))
		addressQRUnion += "}"
		addressQRFinal = "translate([(1.4/17)*length,(1.4/11)*width,0]){resize([0,(7/12)*width,0],auto=[true,true,false]){addressQRUnion}}\n\n".replace('length',str(walletLength)).replace('width',str(walletWidth)).replace('addressQRUnion',addressQRUnion)
		addressParts.append(addressQRFinal)
		
		finalParts.extend(addressParts)

		print(masterSCAD,end="")
		print(mainCube,end="")
		print("".join(finalParts))

	break

