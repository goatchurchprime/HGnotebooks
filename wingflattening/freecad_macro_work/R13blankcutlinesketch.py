# -*- coding: utf-8 -*-
# Macro to make project7wing as list of wires and single bspline surface
sys.path.append(os.path.split(__file__)[0])
import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv, sys
from FreeCAD import Vector, Rotation

sys.path.append(os.path.split(__file__)[0])
from p7modules.p7wingeval import WingEval

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


# Make the wing outline
import numpy
vsamplesforfindingLE = numpy.arange(-200, 200, 1.0)
xvals = [ seval(u, 0.0).x  for u in uvals ]
leadingedgesY = [ max(seval(u, v).y  for v in vsamplesforfindingLE)  for u in uvals ]
trailingedgesUpperY = [ seval(u, vrange[0]).y  for u in uvals ]
trailingedgesLowerY = [ seval(u, vrange[1]).y  for u in uvals ]

def planwingoutlinesketch(sketchname, xvals, yplusedges, yminusedges):
	Psketch = getemptyobject(doc, "Sketcher::SketchObject", sketchname)
	plusEdges = [ Psketch.addGeometry(Part.LineSegment(Vector(xvals[i], yplusedges[i]), Vector(xvals[i+1], yplusedges[i+1])), True)  for i in range(len(xvals)-1) ]
	minusEdges = [ Psketch.addGeometry(Part.LineSegment(Vector(xvals[i], yminusedges[i]), Vector(xvals[i+1], yminusedges[i+1])), True)  for i in range(len(xvals)-1) ]
	leftedge = Psketch.addGeometry(Part.LineSegment(Vector(xvals[0], yplusedges[0]), Vector(xvals[0], yminusedges[0])), True)
	rightedge = Psketch.addGeometry(Part.LineSegment(Vector(xvals[-1], yplusedges[-1]), Vector(xvals[-1], yminusedges[-1])), True)
	# we could easily connect everything up, but this might make it easy to miss if you've moved one by accident
	# locating all by points with position constraints adds too much clutter
	
planwingoutlinesketch("precutupper", xvals, leadingedgesY, trailingedgesUpperY)
planwingoutlinesketch("precutlower", xvals, leadingedgesY, trailingedgesLowerY)
planwingoutlinesketch("postpenupper", xvals, leadingedgesY, trailingedgesUpperY)
planwingoutlinesketch("postpenlower", xvals, leadingedgesY, trailingedgesLowerY)
