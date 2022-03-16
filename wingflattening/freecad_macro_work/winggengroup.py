# -*- coding: utf-8 -*-
# Macro to create a mesh for a hang glider wing suitable for flattening to produce sailmaking patterns
#V0.0
	#-Basic functionality creates single mesh for single aerofoil data file and set of wing sweeps, twists and dihedrals
	#-just uses base sections, no interpolation
version = 0

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os
import pandas as pd
import numpy as np
from FreeCAD import Vector, Rotation

doc = App.ActiveDocument
config = doc.Spreadsheet

dirname = os.path.dirname(os.path.abspath(__file__))
aerofoil_file = os.path.join(dirname, config.aerofoilcsv)
pts = np.loadtxt(aerofoil_file,delimiter = ',')

secs = eval(config.secs)
semi_span = secs[-1]

def angToPlacement(angs,secs):
	ys = [0]
	for i in range(1,len(angs)):
		slope = math.tan(math.radians(angs[i]))
		dy = slope*(secs[i]-secs[i-1])
		ys.append(ys[-1]+dy)
	return ys


sweeps = angToPlacement(eval(config.sweeps), secs)
dihedrals = angToPlacement(eval(config.dihedrals), secs)
chords = eval(config.chords)
twists = eval(config.twists)
doubleSurfs= eval(config.double_surf_dist)
seamDSs = eval(config.seamDS)

def convertDS(pts, ds, seam, chord):
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

for i in range(len(secs)+100):
	wi = doc.findObjects(Name="sec%d"%i)
	if wi:
		doc.removeObject(wi[0])
	else:
		break

secbsplineedges = [ ]
for i in range(len(secs)):
	points, dsp = convertDS(pts, doubleSurfs[i], seamDSs[i], chords[i])
	secplacement = App.Placement(App.Vector(sweeps[i], secs[i], dihedrals[i]), 
									App.Rotation(App.Vector(0,1,0), twists[i]), App.Vector(0,0,0))
	wi = doc.addObject("Part::Feature", "sec%d"%i)
	wi.Shape = Part.makePolygon(points)
	wi.Placement = secplacement
	secbspline = Part.BSplineCurve()
	secbspline.approximate(points, Parameters=range(len(points)))
	secbsplineE = Part.Edge(secbspline)
	secbsplineE.Placement = secplacement
	secbsplineedges.append(secbsplineE)
	
wingloft = doc.findObjects(Name="wingloft")
wingloft = wingloft[0] if wingloft else doc.addObject("Part::Feature", "wingloft")
wingloft.Shape = Part.makeLoft(secbsplineedges)

doc.recompute()

# wlf = doc.wingloft.Shape.Faces[0]
# this is interpolated 0->1 in both parameters

# We can do Part.Vertex(x,y,z).distToShape(doc.wingloft) and get a triple of 
# (distance, [(vertex, closestpointinwingloft)], [uvparameterspaceinfo])

# the lofted surface is a shell shape with Faces for each of the pairs of 90 nodes. 
# each face is u in [i,i+1] and v in [0,1]
# face.valueAt(u, v)
# face.getUVNodes()
# face.isPartOfDomain(u, v)

# obj is a Wire
# b = [ v.Point  for v in obj.Shape.Vertexes]
# splx = [ p.x  for p in b ]
# splz = [ p.x  for p in b ]

#V=App.Vector
#poles=[V(-10,-10),V(10,-10),V(10,10),V(-10,10)]
#n=Part.BSplineCurve()
#Part.show(n.toShape())


