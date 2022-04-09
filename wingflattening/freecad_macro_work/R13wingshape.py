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
		secbsplineedges.append(ws)
	return secbsplineedges


# clear present Groups (FC folders)
sg = getemptyobject(doc, "App::DocumentObjectGroup", "SectionGroup")

# pick the curve lengths of an average section to apply to the parametrization of all the other sections 
chosenparametrization = deriveparametizationforallsections(sections[5])

# create the sections (as consistently parametrized bsplines) and also return 
sections = makesectionsandsplineedges(doc, sg, sections, zvals, chosenparametrization)

# Loft this series of section curves
wingloft = getemptyobject(doc, "Part::Feature", "wingloft")
wingloft.Shape = Part.makeLoft([l.Shape  for l in sg.OutList], False, True)

doc.recompute()


sections = doc.getObject("SectionGroup").OutList

# now generate the blank sketch object
cutlinesketch = getemptyobject(doc, "Sketcher::SketchObject", "cutlinesketch")

leadingedgepoints = [ s.Shape.valueAt(0)  for s in sections ]
leadingedgelengths = [ 0.0 ]
for i in range(len(leadingedgepoints)-1):
	leadingedgelengths.append(leadingedgelengths[-1] + (leadingedgepoints[i+1] - leadingedgepoints[i]).Length)
uvals = leadingedgelengths

urange = [0, uvals[-1]]
vrange = [sections[0].Shape.FirstParameter, sections[0].Shape.LastParameter]

p00 = Vector(urange[0], vrange[0])
p01 = Vector(urange[0], vrange[1])
p10 = Vector(urange[1], vrange[0])
p11 = Vector(urange[1], vrange[1])

e0x = sketch.addGeometry(Part.LineSegment(p00, p01))
e1x = sketch.addGeometry(Part.LineSegment(p10, p11))
ex0 = sketch.addGeometry(Part.LineSegment(p00, p10))
ex1 = sketch.addGeometry(Part.LineSegment(p01, p11))

# These needs to be converted into Construction types.  refer to other code	gsegs = dict((i, x.Geometry)  for i, x in enumerate(cutlinesketch.GeometryFacadeList)  if not x.Construction)

