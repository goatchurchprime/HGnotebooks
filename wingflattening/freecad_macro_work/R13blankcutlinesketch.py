# -*- coding: utf-8 -*-
# Macro to make project7wing as list of wires and single bspline surface

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv
from FreeCAD import Vector, Rotation

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


from p7modules.p7wingeval import WingEval
wingeval = WingEval(doc.getObject("SectionGroup").OutList)
urange, vrange, seval, leadingedgepoints = wingeval.urange, wingeval.vrange, wingeval.seval, wingeval.leadingedgepoints
uvals, sections = wingeval.uvals, wingeval.sections

# now generate the blank sketch object
sketch = getemptyobject(doc, "Sketcher::SketchObject", "cutlinesketch")

p00 = Vector(urange[0], vrange[0])
p01 = Vector(urange[0], vrange[1])
p10 = Vector(urange[1], vrange[0])
p11 = Vector(urange[1], vrange[1])

e0x = sketch.addGeometry(Part.LineSegment(p00, p01), True)
e1x = sketch.addGeometry(Part.LineSegment(p10, p11), True)
ex0 = sketch.addGeometry(Part.LineSegment(p00, p10), True)
ex1 = sketch.addGeometry(Part.LineSegment(p01, p11), True)

sketch.addConstraint(Sketcher.Constraint("Vertical", e0x))
sketch.addConstraint(Sketcher.Constraint("Vertical", e1x))
sketch.addConstraint(Sketcher.Constraint("Horizontal", ex0))
sketch.addConstraint(Sketcher.Constraint("Horizontal", ex1))

sketch.addConstraint(Sketcher.Constraint("Coincident", e0x, 1, ex0, 1))
sketch.addConstraint(Sketcher.Constraint("Coincident", e0x, 2, ex1, 1))
sketch.addConstraint(Sketcher.Constraint("Coincident", ex0, 2, e1x, 1))
sketch.addConstraint(Sketcher.Constraint("Coincident", e1x, 2, ex1, 2))

sketch.addConstraint(Sketcher.Constraint('DistanceX', e0x, 1, urange[0])) 
sketch.addConstraint(Sketcher.Constraint('DistanceY', e0x, 1, vrange[0])) 
sketch.addConstraint(Sketcher.Constraint('DistanceX', e1x, 2, urange[1])) 
sketch.addConstraint(Sketcher.Constraint('DistanceY', e1x, 2, vrange[1])) 

