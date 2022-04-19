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
from p7modules.p7wingeval import getemptyobject, createobjectingroup

doc = App.ActiveDocument

R13type = True


def paramintconv(u, uvals):
	j0, j1 = 0, len(uvals)-1
	while j1 - j0 >= 2:
		j = (j1 + j0)//2
		if u <= uvals[j]:
			j1 = j
		else:
			j0 = j
	return j0 + (u-uvals[j0])/(uvals[j1]-uvals[j0])


class WingEval:
	# R13type = doc.getObject("Group")
	# wingeval = WingEval(doc.getObject("Group" if R13type else "SectionGroup").OutList, R13type)
	def __init__(self, sections, R13type):
		self.sections = sections
		self.R13type = R13type
		
		# main difference is that we treat the source curves as linearized sections by length
		# rather than bsplines with a parametrization, since the latter is buggy and introduces self-folding
		if self.R13type:
			self.Isection = 5
			self.sectionpoints = [ ]
			for section in self.sections:
				self.sectionpoints.append([ v.Point  for v in section.Shape.OrderedVertexes ])

			self.Ichordlengths = [ 0 ]
			for p0, p1 in zip(self.sectionpoints[self.Isection], self.sectionpoints[self.Isection][1:]):
				self.Ichordlengths.append(self.Ichordlengths[-1] + (p0-p1).Length)
			self.vrange = [ self.Ichordlengths[0], self.Ichordlengths[-1] ]

			self.xvals = [ spoints[0].x  for spoints in self.sectionpoints ]  # sections assumed to lie in constant x planes
			self.uvals = self.xvals
			self.urange = [0, self.uvals[-1]]
			
			self.leadingedgesV = [ ]
			for spoints in self.sectionpoints:
				j = max(range(len(spoints)), key=lambda jj:spoints[jj].y)
				self.leadingedgesV.append(self.Ichordlengths[j])
				print(j)
				
		else:
			leadingedgepoints = [ s.Shape.valueAt(0)  for s in self.sections ]
			leadingedgelengths = [ 0.0 ]
			for i in range(len(leadingedgepoints)-1):
				leadingedgelengths.append(leadingedgelengths[-1] + (leadingedgepoints[i+1] - leadingedgepoints[i]).Length)
			self.uvals = leadingedgelengths

			self.urange = [0, self.uvals[-1]]
			self.vrange = [self.sections[0].Shape.FirstParameter, self.sections[0].Shape.LastParameter]
			
			vsamplesforfindingLE = numpy.arange(-200, 200, 0.5)
			self.leadingedgesV = [ max(vsamplesforfindingLE, key=lambda v:section.Shape.valueAt(v).y)  for section in self.sections ]
			self.xvals = [ section.Shape.valueAt(0.0).x  for section in self.sections ]  # sections assumed to lie in constant x planes

		print("Ranges", self.urange, self.vrange)
	
	def sueval(self, i, v):
		vc = paramintconv(v, self.Ichordlengths)
		j = max(0, min(len(self.Ichordlengths)-2, int(vc)))
		m = vc - j
		return self.sectionpoints[i][j]*(1-m) + self.sectionpoints[i][j+1]*m

	def seval(self, u, v):
		uc = paramintconv(u, self.uvals)
		i = max(0, min(len(self.uvals)-2, int(uc)))
		m = uc - i
		if self.R13type:
			p0 = self.sueval(i, v)
			p1 = self.sueval(i+1, v)
		else:
			p0 = self.sections[i].Shape.valueAt(v)
			p1 = self.sections[i+1].Shape.valueAt(v)
		return p0*(1-m) + p1*m



wingeval = WingEval(doc.getObject("Group").OutList, R13type)
urange, vrange, seval = wingeval.urange, wingeval.vrange, wingeval.seval
uvals, sections = wingeval.uvals, wingeval.sections



# now generate the blank sketch object
def uvrectangle(urange, vrange, sketchname):
	sketch = getemptyobject(doc, "Sketcher::SketchObject", sketchname)

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
xvals = [ seval(u, 0.0).x  for u in uvals ]
if R13type:
	leadingedgesY = [ seval(u, v).y  for u, v in zip(uvals, wingeval.leadingedgesV) ]
	xvals = wingeval.xvals
else:
	vsamplesforfindingLE = numpy.arange(-200, 200, 1.0)
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
	
# create the blank sketches in the order they will be used
planwingoutlinesketch("precutupper", xvals, leadingedgesY, trailingedgesUpperY)
planwingoutlinesketch("precutlower", xvals, leadingedgesY, trailingedgesLowerY)
sketch = uvrectangle(urange, vrange, "cutlinesketch")
planwingoutlinesketch("postpenupper", xvals, leadingedgesY, trailingedgesUpperY)
planwingoutlinesketch("postpenlower", xvals, leadingedgesY, trailingedgesLowerY)
