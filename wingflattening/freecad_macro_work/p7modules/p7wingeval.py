# -*- coding: utf-8 -*-
# Module to read the sections from SectionGroup and define the seval(u, v) parametric function on this surface

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv
import numpy
from FreeCAD import Vector, Rotation

doc = App.ActiveDocument
	
# If you are getting the following error:
#  <class 'ReferenceError'>: Cannot access attribute 'Shape' of deleted object
# You might need to restart FreeCAD since it seems capable of leaving submodule of 
# a macro holding on to pointers of some previous objects from a closed file

# parametric definition functions for the wingshape
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
	def __init__(self, sections):
		self.sections = sections

		self.leadingedgepoints = [ s.Shape.valueAt(0)  for s in self.sections ]
		self.leadingedgelengths = [ 0.0 ]
		for i in range(len(self.leadingedgepoints)-1):
			self.leadingedgelengths.append(self.leadingedgelengths[-1] + (self.leadingedgepoints[i+1] - self.leadingedgepoints[i]).Length)
		self.uvals = self.leadingedgelengths

		self.urange = [0, self.uvals[-1]]
		self.vrange = [self.sections[0].Shape.FirstParameter, self.sections[0].Shape.LastParameter]

		print("Ranges", self.urange, self.vrange)
	
	def seval(self, u, v):
		uc = paramintconv(u, self.uvals)
		i = max(0, min(len(self.uvals)-2, int(uc)))
		m = uc - i
		p0 = self.sections[i].Shape.valueAt(v)
		p1 = self.sections[i+1].Shape.valueAt(v)
		return p0*(1-m) + p1*m

# wingeval = WingEval(doc.getObject("SectionGroup").OutList)


