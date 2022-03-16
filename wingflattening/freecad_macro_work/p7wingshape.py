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
	return doc.addObject(objtype, objname)

def createobjectingroup(doc, group, objtype, objname):
	obj = doc.addObject(objtype, objname)
	obj.adjustRelativeLinks(group)
	group.addObject(obj)
	return obj

def makesectionsandsplineedges(doc, sg, sections, zvals):
	secbsplineedges = [ ]
	for i in range(len(zvals)):
		points = [App.Vector(0, -p[0], p[1])  for p in sections[i]]
		placement = App.Placement(App.Vector(zvals[i], 0, 0), App.Rotation())
		ws = createobjectingroup(doc, sg, "Part::Feature", "section%d"%i)
		ws.Shape = Part.makePolygon(points)
		ws.Placement = placement
		secbspline = Part.BSplineCurve()
		secbspline.approximate(points, Parameters=range(len(points)))
		secbsplineE = Part.Edge(secbspline)
		secbsplineE.Placement = placement
		secbsplineedges.append(secbsplineE)
	return secbsplineedges
	
sections, zvals = loadwinggeometry(os.path.join(os.path.dirname(os.path.abspath(__file__)), "P7-211221-XYZ geometry.csv"))
sg = getemptyobject(doc, "App::DocumentObjectGroup", "SectionGroup")
secbsplineedges = makesectionsandsplineedges(doc, sg, sections, zvals)
wingloft = getemptyobject(doc, "Part::Feature", "wingloft")
wingloft.Shape = Part.makeLoft(secbsplineedges)

doc.recompute()

