# -*- coding: utf-8 -*-
# Macro to make project7wing as list of wires and single bspline surface

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv
from FreeCAD import Vector, Rotation

doc = App.ActiveDocument

def loadwinggeometry(fname):
	k = list(csv.reader(open(fname)))
	wingmeshuvudivisions = eval(k[0][-3])
	assert (wingmeshuvudivisions == len(k[0])/3-1), 'Section numbering incorrect'
	sections, zvals = [], []
	for i in range(0, (wingmeshuvudivisions*3)+2, 3):
		pts = [ ]
		z = float(k[2][i+1])
		for j in range(2, len(k)):
			assert (z == float(k[j][i+1]))
			pts.append((float(k[j][i]), float(k[j][i+2])))
		zvals.append(z)
		sections.append(pts)
	assert(len(sections) == wingmeshuvudivisions+1)
	return sections, zvals
	
def getemptyobject(doc, objtype, objname):
	if doc.findObjects(Name=objname):
		doc.removeObject(objname)
		doc.recompute()
	return doc.addObject(objtype, objname)

def createobjectingroup(doc, group, objtype, objname):
	obj = doc.addObject(objtype, objname)
	obj.adjustRelativeLinks(group)
	group.addObject(obj)
	return obj

def deriveparametizationforallsections(chosensection):
	points = [App.Vector(0, -p[0], p[1])  for p in chosensection]
	chordlengths = [ 0 ]
	for p0, p1 in zip(points, points[1:]):
		chordlengths.append(chordlengths[-1] + (p0-p1).Length)
	m = chordlengths[-1]*0.5
	return [ c-m  for c in chordlengths ]

def makesectionsandsplineedges(doc, sg, sections, zvals, sectionparameters):
	secbsplineedges = [ ]
	for i in range(len(zvals)):
		points = [App.Vector(0, -p[0], p[1])  for p in sections[i]]
		placement = App.Placement(App.Vector(zvals[i], 0, 0), App.Rotation())
		secbspline = Part.BSplineCurve()
		secbspline.approximate(points, Parameters=sectionparameters)
		ws = createobjectingroup(doc, sg, "Part::Feature", "section_%d"%(i+1))
		ws.Shape = secbspline.toShape()
		ws.Placement = placement
	

# Spreadsheet containing all the wingsections
sections, zvals = loadwinggeometry(os.path.join(os.path.dirname(os.path.abspath(__file__)), "P7-211221-XYZ geometry.csv"))

# clear present Groups (FC folders).  (Doesn't work reliably)
sg = getemptyobject(doc, "App::DocumentObjectGroup", "SectionGroup")

# pick the curve lengths of an average section to apply to the parametrization of all the other sections 
chosenparametrization = deriveparametizationforallsections(sections[7])

# create the sections (as consistently parametrized bsplines) and also return 
makesectionsandsplineedges(doc, sg, sections, zvals, chosenparametrization)

# Loft this series of section curves
wingloft = getemptyobject(doc, "Part::Feature", "wingloft")
wingloft.Shape = Part.makeLoft([l.Shape  for l in sg.OutList])

doc.recompute()

# f = body.Faces[0]; e = f.Edges[0]; e.curveOnSurface(i)
