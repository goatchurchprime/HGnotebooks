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
		removeObjectRecurse(doc, o.Name)
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

	def inverse_seval(self, x, y, bupperface, tol=0.001):
		xc = paramintconv(x, self.xvals)
		i = max(0, min(len(self.xvals)-2, int(xc)))
		m = xc - i
		u = self.uvals[i]*(1-m) + self.uvals[i+1]*m
		vlo, vhi = (self.vrange[0] if bupperface else self.vrange[1]), self.leadingedgesV[0]

		if self.R13type:
			plo0 = self.sueval(i, vlo)
			plo1 = self.sueval(i+1, vlo)
		else:
			plo0 = self.sections[i].Shape.valueAt(vlo)
			plo1 = self.sections[i+1].Shape.valueAt(vlo)
		plo = plo0*(1-m) + plo1*m

		if self.R13type:
			phi0 = self.sueval(i, vhi)
			phi1 = self.sueval(i+1, vhi)
		else:
			phi0 = self.sections[i].Shape.valueAt(vhi)
			phi1 = self.sections[i+1].Shape.valueAt(vhi)

		phi = phi0*(1-m) + phi1*m
		if not (plo.y - tol*5 <= y <= phi.y + tol*5):
			print("** Warning %f,%f out of range as not %f < %f < %f" % (x, y, plo.y, y, phi.y))
		while abs(phi.y - plo.y) > tol:
			vmid = (vlo + vhi)/2
			if self.R13type:
				pmid0 = self.sueval(i, vmid)
				pmid1 = self.sueval(i+1, vmid)
			else:
				pmid0 = self.sections[i].Shape.valueAt(vmid)
				pmid1 = self.sections[i+1].Shape.valueAt(vmid)
				
			pmid = pmid0*(1-m) + pmid1*m
			if pmid.y < y:
				vlo, plo0, plo1, plo = vmid, pmid0, pmid1, pmid
			else:
				vhi, phi0, phi1, phi = vmid, pmid0, pmid1, pmid
		return u, vlo
