# -*- coding: utf-8 -*-
# Macro to make project7wing as list of wires and single bspline surface

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv
import numpy
from FreeCAD import Vector, Rotation

from p7modules.p7wingeval import urange, vrange, seval
print("Rangess", urange, vrange)

doc = App.ActiveDocument
	
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
mesh = getemptyobject(doc, "Mesh::Feature", "genwingmesh")
mesh.Mesh = Mesh.Mesh(genfacets(12, 30))
mesh.ViewObject.Lighting = "Two side"
