# -*- coding: utf-8 -*-
# Macro to make project7wing as list of wires and single bspline surface

import FreeCAD as App
import FreeCADGui as Gui
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv
import numpy
from FreeCAD import Vector, Rotation

doc = App.ActiveDocument
	
def getemptyobject(doc, objtype, objname):
	if doc.findObjects(Name=objname):
		doc.removeObject(objname)
		doc.recompute()
	return doc.addObject(objtype, objname)

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
	uc = paramintconv(u, zvals)
	i = max(0, min(len(zvals)-2, int(uc)))
	m = uc - i
	p0 = sections[i].Shape.valueAt(v)
	p1 = sections[i+1].Shape.valueAt(v)
	return p0*(1-m) + p1*m

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
	

# Fetch the sections from the folder and find the parameter ranges
sections = doc.getObject("SectionGroup").OutList
zvals = [ s.Placement.Base.x  for s in sections ]
urange = [0, zvals[-1]]
vrange = [sections[0].Shape.FirstParameter, sections[0].Shape.LastParameter]
print("Ranges", urange, vrange)

# generate and plot the meshed object
mesh = getemptyobject(doc, "Mesh::Feature", "genwingmesh")
mesh.Mesh = Mesh.Mesh(genfacets(12, 30))
mesh.ViewObject.Lighting = "Two side"
