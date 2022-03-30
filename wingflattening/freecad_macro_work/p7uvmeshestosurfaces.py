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

doc = App.ActiveDocument

def getemptyobject(doc, objtype, objname):
	if doc.findObjects(Name=objname):
		doc.removeObject(objname)
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

for i in range(0, len(uvtriangulations)):
	t = uvtriangulations[i]
	m = t.Mesh
	pts = [ seval(p.Vector.x, p.Vector.y)  for p in m.Points ]
	tris = [ x.PointIndices  for x in m.Facets ]
	facets = [ [ pts[i0], pts[i1], pts[i2] ]  for i0, i1, i2 in tris ]

	mesh = createobjectingroup(doc, stg, "Mesh::Feature", "s%s"%t.Name[1:])
	mesh.Mesh = Mesh.Mesh(facets)
	mesh.ViewObject.Lighting = "Two side"
	mesh.ViewObject.ShapeColor = t.ViewObject.ShapeColor

	print(mesh.Name, "tris", len(tris), "pts", len(pts), mesh.Mesh)
	gpts = numpy.array([[p.x, p.y, p.z]  for p in pts ])

	flattener = flatmesh.FaceUnwrapper(gpts, numpy.array(tris))
	flattener.findFlatNodes(10, 0.95)
	fpts = [ Vector(ze[0], ze[1], 0)  for ze in flattener.ze_nodes ]
	ffacets = [ [ fpts[i0], fpts[i1], fpts[i2] ]  for i0, i1, i2 in tris ]

	fmesh = createobjectingroup(doc, flg, "Mesh::Feature", "f%s"%t.Name[1:])
	fmesh.Mesh = Mesh.Mesh(ffacets)
	fmesh.ViewObject.Lighting = "Two side"
	fmesh.ViewObject.ShapeColor = t.ViewObject.ShapeColor
	fmesh.Placement.Base = Vector(0,-(i+1)*1000,0)
