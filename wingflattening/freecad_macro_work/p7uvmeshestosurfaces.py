# -*- coding: utf-8 -*-

# This macro takes the areas out of PatchUVPolygons (polygons in UV space)
# and trims sections of the wingsurface to them to generate triangulated surfaces

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv, sys
import numpy
from FreeCAD import Vector, Rotation
import flatmesh

sys.path.append(os.path.split(__file__)[0])

doc = App.ActiveDocument

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
	obj = doc.addObject(objtype, objname)
	obj.adjustRelativeLinks(group)
	group.addObject(obj)
	return obj

uvtriangulations = doc.UVTriangulations.OutList
stg = getemptyobject(doc, "App::DocumentObjectGroup", "STriangulations")
flg = getemptyobject(doc, "App::DocumentObjectGroup", "SFlattened")

# Do this if running by pasting into Python window
#sys.path.append("/home/julian/repositories/HGnotebooks/wingflattening/freecad_macro_work")

from p7modules.p7wingeval import urange, vrange, seval, leadingedgelengths

def transformalignfpts(uvpts, fpts, patchname):
	uvpts = [ p.Vector for p in t.Mesh.Points ]
	uvcentre = sum(uvpts, Vector())*(1/len(uvpts))
	flatcentre = sum(fpts, Vector())*(1/len(fpts))
	
	itopright = max(range(len(uvpts)), key=lambda X: uvpts[X].x + uvpts[X].y)
	ibottomright = max(range(len(uvpts)), key=lambda X: uvpts[X].x - uvpts[X].y)
	
	# or do the opposite corners to align the left hand side with it.
	if patchname == "TSF2":
		itopright = min(range(len(uvpts)), key=lambda X: uvpts[X].x + uvpts[X].y)
		ibottomright = min(range(len(uvpts)), key=lambda X: uvpts[X].x - uvpts[X].y)

	vuvtr = uvpts[itopright] - uvcentre
	vuvbr = uvpts[ibottomright] - uvcentre
	vftr = fpts[itopright] - flatcentre
	vfbr = fpts[ibottomright] - flatcentre
	vuvdotperp = -vuvtr.x*vuvbr.y + vuvtr.y*vuvbr.x
	assert vuvdotperp > 0.0
	vfdotperp = -vftr.x*vfbr.y + vftr.y*vfbr.x
	if vfdotperp < 0.0: # reflect
		fpts = [ Vector(-p.x, p.y, 0)  for p in fpts ]
		flatcentre = sum(fpts, Vector())*(1/len(fpts))
		vftr = fpts[itopright] - flatcentre
		vfbr = fpts[ibottomright] - flatcentre
	cs = vuvtr.dot(vftr)/(vuvtr.Length*vftr.Length)
	sn = vuvtr.dot(Vector(-vftr.y, vftr.x, 0))/(vuvtr.Length*vftr.Length)
	vdisp = uvcentre - flatcentre
	
	explodev = (uvcentre - Vector(3000, 0, 0))*0.8
	if patchname == "TSM3":
		uvcentre -= Vector(1000, -300, 0)
	def transF(p):
		p0 = p - flatcentre
		return p0*cs + Vector(-p0.y, p0.x, 0)*sn + uvcentre + explodev
	rfpts = [ transF(p)   for p in fpts ]
	return rfpts


for i in range(0, len(uvtriangulations)):
	t = uvtriangulations[i]
	m = t.Mesh
	uvpts = [ p.Vector  for p in m.Points ]
	pts = [ seval(p.Vector.x, p.Vector.y)  for p in m.Points ]
	tris = [ x.PointIndices  for x in m.Facets ]
	facets = [ [ pts[i0], pts[i1], pts[i2] ]  for i0, i1, i2 in tris ]
	uvcentre = sum((p.Vector for p in m.Points), Vector())*(1/m.CountPoints)

	mesh = createobjectingroup(doc, stg, "Mesh::Feature", "s%s"%t.Name[1:])
	mesh.Mesh = Mesh.Mesh(facets)
	mesh.ViewObject.Lighting = "Two side"
	mesh.ViewObject.ShapeColor = t.ViewObject.ShapeColor

	print(mesh.Name, "tris", len(tris), "pts", len(pts), mesh.Mesh)
	gpts = numpy.array([[p.x, p.y, p.z]  for p in pts ])

	flattener = flatmesh.FaceUnwrapper(gpts, numpy.array(tris))
	flattener.findFlatNodes(10, 0.95)
	fpts = [ Vector(ze[0], ze[1], 0)  for ze in flattener.ze_nodes ]

	rfpts = transformalignfpts(uvpts, fpts, t.Name[1:])
	rffacets = [ [ rfpts[i0], rfpts[i1], rfpts[i2] ]  for i0, i1, i2 in tris ]

	fmesh = createobjectingroup(doc, flg, "Mesh::Feature", "f%s"%t.Name[1:])
	fmesh.Mesh = Mesh.Mesh(rffacets)
	fmesh.ViewObject.Lighting = "Two side"
	fmesh.ViewObject.ShapeColor = t.ViewObject.ShapeColor
	
	
for i in range(0, len(uvtriangulations)):
	t, fmesh = doc.UVTriangulations.OutList[i], doc.SFlattened.OutList[i]
	fpts = [ p.Vector  for p in fmesh.Mesh.Points ]
	tris = [ x.PointIndices  for x in t.Mesh.Facets ]
	
	uvpts = [ p.Vector for p in t.Mesh.Points ]
	uvcentre = sum(uvpts, Vector())*(1/len(uvpts))
	flatcentre = sum(fpts, Vector())*(1/len(fpts))
	itopright = max(range(len(uvpts)), key=lambda X: uvpts[X].x + uvpts[X].y)
	ibottomright = max(range(len(uvpts)), key=lambda X: uvpts[X].x - uvpts[X].y)
	vuvtr = uvpts[itopright] - uvcentre
	vuvbr = uvpts[ibottomright] - uvcentre
	vftr = fpts[itopright] - flatcentre
	vfbr = fpts[ibottomright] - flatcentre
	vuvdotperp = -vuvtr.x*vuvbr.y + vuvtr.y*vuvbr.x
	assert vuvdotperp > 0.0
	vfdotperp = -vftr.x*vfbr.y + vftr.y*vfbr.x
	if vfdotperp < 0.0: # reflect
		fpts = [ Vector(-p.x, p.y, 0)  for p in fpts ]
		flatcentre = sum(fpts, Vector())*(1/len(fpts))
		vftr = fpts[itopright] - flatcentre
		vfbr = fpts[ibottomright] - flatcentre
	cs = vuvtr.dot(vftr)/(vuvtr.Length*vftr.Length)
	sn = vuvtr.dot(Vector(-vftr.y, vftr.x, 0))/(vuvtr.Length*vftr.Length)
	vdisp = uvcentre - flatcentre
	
	explodev = (uvcentre - Vector(3000, 0, 0))*0.8
	if fmesh.Name[1:] == "TSM3":
		uvcentre -= Vector(1000, -300, 0)
	def transF(p):
		p0 = p - flatcentre
		return p0*cs + Vector(-p0.y, p0.x, 0)*sn + uvcentre + explodev
	rfpts = [ transF(p)   for p in fpts ]
	
	rffacets = [ [ rfpts[i0], rfpts[i1], rfpts[i2] ]  for i0, i1, i2 in tris ]
	fmesh.Mesh = Mesh.Mesh(rffacets)


