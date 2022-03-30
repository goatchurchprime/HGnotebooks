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

def seval(u, v):
	uc = paramintconv(u, uvals)
	i = max(0, min(len(uvals)-2, int(uc)))
	m = uc - i
	p0 = sections[i].Shape.valueAt(v)
	p1 = sections[i+1].Shape.valueAt(v)
	return p0*(1-m) + p1*m

# Fetch the sections from the folder and find the parameter ranges
sections = doc.getObject("SectionGroup").OutList

leadingedgepoints = [ s.Shape.valueAt(0)  for s in sections ]
leadingedgelengths = [ 0.0 ]
for i in range(len(leadingedgepoints)-1):
	leadingedgelengths.append(leadingedgelengths[-1] + (leadingedgepoints[i+1] - leadingedgepoints[i]).Length)
uvals = leadingedgelengths

urange = [0, uvals[-1]]
vrange = [sections[0].Shape.FirstParameter, sections[0].Shape.LastParameter]

print("Ranges", urange, vrange)

