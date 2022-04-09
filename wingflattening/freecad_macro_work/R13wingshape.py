# -*- coding: utf-8 -*-
# Macro to make project7wing as list of wires and single bspline surface

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv
from FreeCAD import Vector, Rotation

# Run this on testriotwires
# Very much the same as p7wingshape

doc = App.ActiveDocument

	
def removeObjectRecurse(objname):
	for o in doc.findObjects(Name=objname)[0].OutList:
		removeObjectRecurse(o.Name)
	doc.removeObject(objname)
	
def getemptyobject(doc, objtype, objname):
	if doc.findObjects(Name=objname):
		removeObjectRecurse(objname)
		doc.recompute()
	return doc.addObject(objtype, objname)

def createobjectingroup(doc, group, objtype, objname):
	if group == None:
		return getemptyobject(doc, objtype, objname)
	obj = doc.addObject(objtype, objname)
	obj.adjustRelativeLinks(group)
	group.addObject(obj)
	return obj


groupwires = doc.Group.OutList
sections = [ [ (v.Point.x, v.Point.z)  for v in groupwire.Shape.OrderedVertexes ]  for groupwire in groupwires ]
zvals = [ groupwire.Shape.OrderedVertexes[0].Point.y  for groupwire in groupwires ]
 

def deriveparametizationforallsections(chosensection):
	points = [App.Vector(0, -p[0], p[1])  for p in chosensection]
	chordlengths = [ 0 ]
	for p0, p1 in zip(points, points[1:]):
		chordlengths.append(chordlengths[-1] + (p0-p1).Length)

	print("This is the bit where we need to find the front leading edge between 0 and chordlength", chordlengths[-1])

	m = chordlengths[-1]*0.5
	return [ c-m  for c in chordlengths ]

def makesectionsandsplineedges(doc, sg, sections, zvals, sectionparameters):
	secbsplineedges = [ ]
	for i in range(len(zvals)):
		points = [App.Vector(0, -p[0], p[1])  for p in sections[i]]
		placement = App.Placement(App.Vector(zvals[i], 0, 0), App.Rotation())
		secbspline = Part.BSplineCurve()
		
		# make sure it doesn't close the curve or cause bad spline tangents
		pointsnc = points[:-1]+[points[-1]+Vector(0,0,0.001)]
		secbspline.approximate(pointsnc, Parameters=sectionparameters, DegMin=2, DegMax=2)
		assert not secbspline.isClosed()
		
		ws = createobjectingroup(doc, sg, "Part::Feature", "section_%d"%(i+1))
		ws.Shape = secbspline.toShape()
		ws.Placement = placement
	


# clear present Groups (FC folders)
sg = getemptyobject(doc, "App::DocumentObjectGroup", "SectionGroup")

# pick the curve lengths of an average section to apply to the parametrization of all the other sections 
chosenparametrization = deriveparametizationforallsections(sections[5])

# create the sections (as consistently parametrized bsplines) and also return 
makesectionsandsplineedges(doc, sg, sections, zvals, chosenparametrization)

# Loft this series of section curves
wingloft = getemptyobject(doc, "Part::Feature", "wingloft")
wingloft.Shape = Part.makeLoft([l.Shape  for l in sg.OutList], False, True)

doc.recompute()

# f = body.Faces[0]; e = f.Edges[0]; e.curveOnSurface(i)
