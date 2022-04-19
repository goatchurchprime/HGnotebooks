# -*- coding: utf-8 -*-

# Macro to generate the pencil lines onto each of the patches 
# based on the other outlines and on the batton patch design

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv, sys
import numpy
from FreeCAD import Vector, Rotation

sys.path.append(os.path.split(__file__)[0])

from p7modules.barmesh.basicgeo import P2, P3, Partition1, Along, I1

doc = App.ActiveDocument

from p7modules.p7wingeval import WingEval
R13type = doc.getObject("Group")
wingeval = WingEval(doc.getObject("Group" if R13type else "SectionGroup").OutList, R13type)
urange, vrange, seval = wingeval.urange, wingeval.vrange, wingeval.seval

uspacing, vspacing = 20, 10
xpart = Partition1(urange[0], urange[1], int((urange[1]-urange[0])/uspacing + 2))
ypart = Partition1(vrange[0], (vrange[0]+vrange[1])/2, int((vrange[1]-vrange[0])/vspacing/2 + 2))

def sevalP3(u, v):
	p = seval(u, v)
	return P3(p.x, p.y, p.z)

from p7modules.p7wingflatten_barmeshfuncs import sliceupatnones

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

def sevalP3(u, v):
	p = seval(u, v)
	return P3(p.x, p.y, p.z)

lowersurfacesewline = getemptyobject(doc, "Part::Feature", "UVLSsewline")

# we use the fact that the parametrization runs with constant u giving constant x, 
# so can be calculated in-line

UVLSsewlinepoints = [ ]
for u in xpart.vs:
	pS = seval(u, vrange[1])
	vlo, vhi = vrange[0], (vrange[0]+vrange[1])/2
	plo, phi = seval(u, vlo), seval(u, vhi)
	assert plo.y < pS.y < phi.y
	while phi.y - plo.y > 0.001:
		vmid = (vlo + vhi)/2
		pmid = seval(u, vmid)
		if pmid.y < pS.y:
			vlo, plo = vmid, pmid
		else:
			vhi, phi = vmid, pmid
	UVLSsewlinepoints.append(Vector(u, vlo, 0))

lowersurfacesewline.Shape = Part.makePolygon(UVLSsewlinepoints)
lowersurfacesewline.ViewObject.PointColor = (1.0,0.0,1.0)
lowersurfacesewline.ViewObject.LineColor = (1.0,0.0,1.0)
