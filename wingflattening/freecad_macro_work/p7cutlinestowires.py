# -*- coding: utf-8 -*-
# Macro to make project7wing as list of wires and single bspline surface

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv
import numpy
from FreeCAD import Vector, Rotation

from p7modules.p7wingeval import urange, vrange, seval
print("Rangesss", urange, vrange)

doc = App.ActiveDocument

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

cutlinesketch = doc.cutlinesketch

# clear present Groups (FC folders).  (Doesn't work reliably)
clw = getemptyobject(doc, "App::DocumentObjectGroup", "CutlineWires")

pointindexes = [ ]
for i, e in enumerate(cutlinesketch.Geometry):
	p0, p1 = e.StartPoint, e.EndPoint
	ws = createobjectingroup(doc, clw, "Part::Feature", "wire_%d"%(i+1))
	ll = numpy.linspace(0, 1, 10)
	luvs = [ p0*(1-l) + p1*l  for l in ll ]
	points = [ seval(p.x, p.y)  for p in luvs ]
	ws.Shape = Part.makePolygon(points)
	
