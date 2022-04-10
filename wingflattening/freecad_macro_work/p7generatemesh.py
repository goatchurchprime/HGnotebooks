# -*- coding: utf-8 -*-

# Basic macro that just generates untrimmedwingmesh with a given set of steps 
# in u and v from the list of wire sections in SectionGroup 
# This should be exactly the same shape as the wingloft shape

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv, sys
import numpy
from FreeCAD import Vector, Rotation

sys.path.append(os.path.split(__file__)[0])

doc = App.ActiveDocument

from p7modules.p7wingeval import WingEval
wingeval = WingEval(doc.getObject("SectionGroup").OutList)
urange, vrange, seval, leadingedgepoints = wingeval.urange, wingeval.vrange, wingeval.seval, wingeval.leadingedgepoints
uvals, sections = wingeval.uvals, wingeval.sections

print("Rangess", urange, vrange)
from p7modules.p7wingeval import sections, leadingedgepoints, uvals

def paramintconv(u, uvals):
	j0, j1 = 0, len(uvals)-1
	while j1 - j0 >= 2:
		j = (j1 + j0)//2
		if u <= uvals[j]:
			j1 = j
		else:
			j0 = j
	return j0 + (u-uvals[j0])/(uvals[j1]-uvals[j0])

def sevalG(u, v):
	uc = paramintconv(u, uvals)
	i = max(0, min(len(uvals)-2, int(uc)))
	m = uc - i
	p0 = sections[i].Shape.valueAt(v)
	p1 = sections[i+1].Shape.valueAt(v)
	return p0*(1-m) + p1*m



print(sevalG(1,1))

	
def getemptyobject(doc, objtype, objname):
	if doc.findObjects(Name=objname):
		doc.removeObject(objname)
		doc.recompute()
	return doc.addObject(objtype, objname)

def genfacets(usteps, vsteps):
	prevrow = [ ]
	facets = [ ]
	for u in numpy.linspace(urange[0], urange[1], usteps):
		row = [ ]
		for v in numpy.linspace(vrange[0], vrange[1], vsteps):
			row.append(seval(u, v))
		if prevrow:
			for i in range(len(prevrow)-1):
				facets.extend([prevrow[i], prevrow[i+1], row[i+1]])
				facets.extend([prevrow[i], row[i+1], row[i]])
		prevrow = row
	return facets
	
# generate and plot the meshed object
mesh = getemptyobject(doc, "Mesh::Feature", "untrimmedwingmesh")
mesh.Mesh = Mesh.Mesh(genfacets(60, 120))
mesh.ViewObject.Lighting = "Two side"
