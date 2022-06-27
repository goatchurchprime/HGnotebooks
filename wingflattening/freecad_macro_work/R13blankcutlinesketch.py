# -*- coding: utf-8 -*-
# Macro to make project7wing as list of wires and single bspline surface
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv, sys
from FreeCAD import Vector, Rotation

sys.path.append(os.path.split(__file__)[0])
from p7modules.p7wingeval import WingEval
from p7modules.p7wingeval import getemptyobject, createobjectingroup, uvrectangle

doc = App.ActiveDocument

R13type = True

wingeval = WingEval(doc.getObject("Group").OutList, R13type)
urange, vrange, seval = wingeval.urange, wingeval.vrange, wingeval.seval
uvals, sections = wingeval.uvals, wingeval.sections

# Make the wing outline
import numpy
xvals = [ seval(u, 0.0).x  for u in uvals ]
if R13type:
	leadingedgesY = [ seval(u, v).y  for u, v in zip(uvals, wingeval.leadingedgesV) ]
	xvals = wingeval.xvals
else:
	vsamplesforfindingLE = numpy.arange(-200, 200, 1.0)
	leadingedgesY = [ max(seval(u, v).y  for v in vsamplesforfindingLE)  for u in uvals ]
	
trailingedgesUpperY = [ seval(u, vrange[0]).y  for u in uvals ]
trailingedgesLowerY = [ seval(u, vrange[1]).y  for u in uvals ]

def planwingoutlinesketch(sketchname, xvals, yplusedges, yminusedges, additionaldrawingedges=None):
	Psketch = getemptyobject(doc, "Sketcher::SketchObject", sketchname)

	plusEdges = [ Psketch.addGeometry(Part.LineSegment(Vector(xvals[i], yplusedges[i]), Vector(xvals[i+1], yplusedges[i+1])), True)  for i in range(len(xvals)-1) ]
	minusEdges = [ Psketch.addGeometry(Part.LineSegment(Vector(xvals[i], yminusedges[i]), Vector(xvals[i+1], yminusedges[i+1])), True)  for i in range(len(xvals)-1) ]
	leftedge = Psketch.addGeometry(Part.LineSegment(Vector(xvals[0], yplusedges[0]), Vector(xvals[0], yminusedges[0])), True)
	rightedge = Psketch.addGeometry(Part.LineSegment(Vector(xvals[-1], yplusedges[-1]), Vector(xvals[-1], yminusedges[-1])), True)
	if additionaldrawingedges:
		[ Psketch.addGeometry(Part.LineSegment(Vector(xvals[i], additionaldrawingedges[i]), Vector(xvals[i+1], additionaldrawingedges[i+1])), False)  for i in range(len(xvals)-1) ]

	# nail down the endpoints of all these edges
	for i in range(len(Psketch.Geometry)):
		l = Psketch.Geometry[i]
		Psketch.addConstraint(Sketcher.Constraint('DistanceX', i, 1, l.StartPoint.x)) 
		Psketch.addConstraint(Sketcher.Constraint('DistanceY', i, 1, l.StartPoint.y)) 
		Psketch.addConstraint(Sketcher.Constraint('DistanceX', i, 2, l.EndPoint.x)) 
		Psketch.addConstraint(Sketcher.Constraint('DistanceY', i, 2, l.EndPoint.y)) 

	for i in range(len(Psketch.Constraints)):
		Psketch.setVirtualSpace(i, True)
	
	
	
# create the blank sketches in the order they will be used
planwingoutlinesketch("precutupper", xvals, leadingedgesY, trailingedgesUpperY)
planwingoutlinesketch("precutlower", xvals, leadingedgesY, trailingedgesLowerY)
sketch = uvrectangle(urange, vrange, "cutlinesketch",doc)
planwingoutlinesketch("postpenupper", xvals, leadingedgesY, trailingedgesUpperY, trailingedgesLowerY)
planwingoutlinesketch("postpenlower", xvals, leadingedgesY, trailingedgesLowerY)
