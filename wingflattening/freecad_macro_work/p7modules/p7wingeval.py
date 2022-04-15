# -*- coding: utf-8 -*-
# Module to read the sections from SectionGroup and define the seval(u, v) parametric function on this surface

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv
import numpy
from FreeCAD import Vector, Rotation


def removeObjectRecurse(doc, objname):
	for o in doc.findObjects(Name=objname)[0].OutList:
		removeObjectRecurse(o.Name)
	doc.removeObject(objname)
	
def getemptyobject(doc, objtype, objname):
	if doc.findObjects(Name=objname):
		removeObjectRecurse(doc, objname)
		doc.recompute()
	return doc.addObject(objtype, objname)

def createobjectingroup(doc, group, objtype, objname):
	if group == None:
		return getemptyobject(doc, objtype, objname)
	obj = doc.addObject(objtype, objname)
	obj.adjustRelativeLinks(group)
	group.addObject(obj)
	return obj


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
	# wingeval = WingEval(doc.getObject("SectionGroup").OutList)
	def __init__(self, sections):
		self.sections = sections

		self.leadingedgepoints = [ s.Shape.valueAt(0)  for s in self.sections ]
		self.leadingedgelengths = [ 0.0 ]
		for i in range(len(self.leadingedgepoints)-1):
			self.leadingedgelengths.append(self.leadingedgelengths[-1] + (self.leadingedgepoints[i+1] - self.leadingedgepoints[i]).Length)
		self.uvals = self.leadingedgelengths

		self.urange = [0, self.uvals[-1]]
		self.vrange = [self.sections[0].Shape.FirstParameter, self.sections[0].Shape.LastParameter]
		self.vvalsLE = [self.sections[0].Shape.FirstParameter, self.sections[0].Shape.LastParameter]
		
		self.xvals = [ section.Shape.valueAt(0.0).x  for section in self.sections ]  # sections assumed to lie in constant x planes
		vsamplesforfindingLE = numpy.arange(-200, 200, 0.5)
		self.leadingedgesV = [ max(vsamplesforfindingLE, key=lambda v:section.Shape.valueAt(v).y)  for section in self.sections ]

		print("Ranges", self.urange, self.vrange)
	
	def seval(self, u, v):
		uc = paramintconv(u, self.uvals)
		i = max(0, min(len(self.uvals)-2, int(uc)))
		m = uc - i
		p0 = self.sections[i].Shape.valueAt(v)
		p1 = self.sections[i+1].Shape.valueAt(v)
		return p0*(1-m) + p1*m

	def inverse_seval(self, x, y, bupperface, tol=0.001):
		xc = paramintconv(x, self.xvals)
		i = max(0, min(len(self.xvals)-2, int(xc)))
		m = xc - i
		u = self.uvals[i]*(1-m) + self.uvals[i+1]*m
		vlo, vhi = (self.vrange[0] if bupperface else self.vrange[1]), self.leadingedgesV[0]

		plo0 = self.sections[i].Shape.valueAt(vlo)
		plo1 = self.sections[i+1].Shape.valueAt(vlo)
		plo = plo0*(1-m) + plo1*m
		phi0 = self.sections[i].Shape.valueAt(vhi)
		phi1 = self.sections[i+1].Shape.valueAt(vhi)
		phi = phi0*(1-m) + phi1*m
		if not (plo.y - tol*5 <= y <= phi.y + tol*5):
			print("** Warning %f,%f out of range as not %f < %f < %f" % (x, y, plo.y, y, phi.y))
		while abs(phi.y - plo.y) > tol:
			vmid = (vlo + vhi)/2
			pmid0 = self.sections[i].Shape.valueAt(vmid)
			pmid1 = self.sections[i+1].Shape.valueAt(vmid)
			pmid = pmid0*(1-m) + pmid1*m
			if pmid.y < y:
				vlo, plo0, plo1, plo = vmid, pmid0, pmid1, pmid
			else:
				vhi, phi0, phi1, phi = vmid, pmid0, pmid1, pmid
		return u, vlo
