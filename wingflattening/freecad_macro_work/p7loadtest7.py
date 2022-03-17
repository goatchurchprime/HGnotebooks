# -*- coding: utf-8 -*-
# Macro to load the test7.json wing trimming design into a cutline sketch once

import FreeCAD as App
import Draft, Part, Mesh, Sketcher
import DraftGeomUtils
import math, os, csv, json
from FreeCAD import Vector, Rotation

doc = App.ActiveDocument
	
def getemptyobject(doc, objtype, objname):
	if doc.findObjects(Name=objname):
		doc.removeObject(objname)
		doc.recompute()
	return doc.addObject(objtype, objname)


jdata = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test7.json")))

cutlinesketch = getemptyobject(doc, "Sketcher::SketchObject", "cutlinesketch")
for i in range(0, len(jdata["paths"]), 2):
	n0, n1 = jdata["paths"][i], jdata["paths"][i+1]
	p0 = Vector(jdata["nodes"][n0][0]*1000, jdata["nodes"][n0][1]*1000)
	p1 = Vector(jdata["nodes"][n1][0]*1000, jdata["nodes"][n1][1]*1000)
	if p0 != p1:
		cutlinesketch.addGeometry(Part.LineSegment(p0, p1))
doc.recompute()

# Generate constraints from matching nodes
pointindexes = [ ]
for i, e in enumerate(cutlinesketch.Geometry):
	pointindexes.append((e.StartPoint.x, e.StartPoint.y, e.StartPoint.z, i, 1))
	pointindexes.append((e.EndPoint.x, e.EndPoint.y, e.EndPoint.z, i, 2))
pointindexes.sort()

for i in range(len(pointindexes)-1):
	if pointindexes[i][:3] == pointindexes[i+1][:3]:
		cutlinesketch.addConstraint(Sketcher.Constraint("Coincident", pointindexes[i][3], pointindexes[i][4], pointindexes[i+1][3], pointindexes[i+1][4]))

doc.recompute()

# use FreeCADGui.Selection.getSelection() to get a selected object
