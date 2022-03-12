# -*- coding: utf-8 -*-
# Macro to create a mesh for a hang glider wing suitable for flattening to produce sailmaking patterns
#V0.0
	#-Basic functionality creates single mesh for single aerofoil data file and set of wing sweeps, twists and dihedrals
	#-just uses base sections, no interpolation
version = 0

import Draft
import DraftGeomUtils
import math, os
import Part
from FreeCAD import Vector
import Mesh
import pandas as pd
import numpy as np
import FreeCAD as App

doc = App.ActiveDocument
config = doc.Spreadsheet

dirname = os.path.dirname(os.path.abspath(__file__))
aerofoil_file = os.path.join(dirname, config.aerofoilcsv)
OP_file = os.path.join(dirname, config.OPcsv)
print(aerofoil_file)
nameFile = aerofoil_file.split("/")[-1][:-4]
print(nameFile)

#sectionsgroup = doc.getObject("SectionsGroup")
#if not sectionsgroup:
#	sectionsgroup = app.addObject("App::DocumentObjectGroup", "SectionsGroup")
#else:
	

secs = eval(config.secs)
semi_span = secs[-1]
sweeps = angToPlacement(eval(config.sweeps), secs)
dihedrals = angToPlacement(eval(config.dihedrals), secs)
chords = eval(config.chords)
twists = eval(config.twists)
doubleSurfs= eval(config.double_surf_dist)
seamDSs = eval(config.seamDS)

#Function to mesh between two aero-profiles
def foil_mesh(points1, points2, trianglepoints):
	trianglepoints = trianglepoints
	for i in range(len(points1)-1):
		ip = (i+1)
		trianglepoints.append(points1[i]);  trianglepoints.append(points2[i]);   trianglepoints.append(points2[ip]); 
		trianglepoints.append(points1[i]);  trianglepoints.append(points2[ip]);  trianglepoints.append(points1[ip]); 
	return trianglepoints

def interpolate_ang(ang, axs,d = 100):
	xs, ys = [ 0 ], [ 0 ]
	#axs = [semi_span*i/(len(ang)-1)  for i in range(len(ang))]
	#print(axs)
	for i in range(1, len(ang)):
		x0, x1 = axs[i-1], axs[i]
		a0, a1 = ang[i-1], ang[i]
		n = int((x1-x0)/d) + 1
		for j in range(1, n+1):
			x = x0 + (x1-x0)*j/n
			a = a0 + (a1-a0)*j/n
			slope = math.tan(math.radians(a))
			dy = slope*(x-xs[-1])
			xs.append(x)
			ys.append(ys[-1]+dy)
	return xs,ys

#Function to interpolate items at various points
def interpolate_length(lengths, secs, interp):
	points = []

	for station in range (0, len(lengths)):
		points.append(FreeCAD.Vector(secs[station], lengths[station],0))

	BSpline = Part.BSplineCurve(points)
	wire = DraftGeomUtils.curvetowire(BSpline,interp)
	ys = [lengths[0]]

	for edge in wire:
		ys.append(edge.lastVertex().Y)

	return ys

def angToPlacement(angs,secs):
	ys = [0]
	for i in range(1,len(angs)):
		slope = math.tan(math.radians(angs[i]))
		dy = slope*(secs[i]-secs[i-1])
		ys.append(ys[-1]+dy)
	return ys

def convertDS(pts,ds, seam,chord):
	l=len(pts)
	aerof=[]
	dsp = [ds,0]
	dsfp = [seam,0]
	found = False
	front = False
	pl = pts[0]
	highlight=False
	
	for p in pts:
		if p[0]*chord < ds and not found:
			dsp[1] = p[1]*chord + ((ds-p[0]*chord)*(pl[1]-p[1]))/(pl[0]-p[0])
			found = True
			print(dsp)
		if not highlight and p[0]>pl[0]:
			highlight = True
			print('found highlight',pl)
		if highlight and p[0]*chord>seam:
			dsfp[1]= p[1]*chord + ((seam-p[0]*chord)*(pl[1]-p[1]))/(pl[0]-p[0])
			print('foundseam',dsfp)
			#aerof.append(App.Vector(dsfp[0],0,dsfp[1]))
			BSptsx=np.linspace(dsfp[0],dsp[0],l-len(aerof))
			BSptsy=np.interp(BSptsx,[dsfp[0],dsp[0]],[dsfp[1],dsp[1]])
			#aerof.append(App.Vector(dsp[0],0,dsp[1]))
			for x in BSptsx:
				z=np.interp(x,[dsfp[0],dsp[0]],[dsfp[1],dsp[1]])
				aerof.append(App.Vector(x,0,z))
			break
		aerof.append(App.Vector(p[0]*chord,0,p[1]*chord))
		pl = p
	return aerof,dsp
		

trianglepoints = []


pts = np.loadtxt(aerofoil_file,delimiter = ',')
dsl=[]
df = pd.DataFrame()


for station in range(len(secs)):
	points, dsp = convertDS(pts, doubleSurfs[station], seamDSs[station], chords[station])
	print(len(points))
	section = Draft.makeWire(points, closed = False)

	section.Placement = App.Placement(App.Vector(sweeps[station],secs[station], dihedrals[station]), App.Rotation(App.Vector(0,1,0),twists[station]), App.Vector(0,0,0))
	points = [section.Placement*p  for p in section.Points]
	section.Label = str(station)+nameFile +"_(DWire)"
	dsl.append(section.Placement*App.Vector(dsp[0],0,dsp[1]))

	if station > 0:
		trianglepoints = foil_mesh(last_points,  points, trianglepoints)
		if station == len(secs)-1:
			meshy = Mesh.Mesh(trianglepoints)
			Mesh.show(meshy)
#			print(meshy)
	last_points = points
	x,y,z = [],[],[]
	for p in points:
		x.insert(0,p.x)
		y.insert(0,p.y)
		z.insert(0,p.z)
	df.insert(0,'x'+str(station),x)
	df.insert(0,'y'+str(station),y)
	df.insert(0,'z'+str(station),z)

section = Draft.makeWire(dsl, closed = False)
#print(OPpts)


df = df.iloc[:, ::-1]
#print(df)
df.to_csv(OP_file, index =False)
