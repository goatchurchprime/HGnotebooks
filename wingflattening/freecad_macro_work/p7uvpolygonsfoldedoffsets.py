# -*- coding: utf-8 -*-

# This macro takes the areas out of PatchUVPolygons (polygons in UV space)
# and trims sections of the wingsurface to them to generate triangulated surfaces

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv, sys
import numpy
from FreeCAD import Vector, Rotation

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

uvpolygons = doc.UVPolygons.OutList
uvpolygonsoffsets = getemptyobject(doc, "App::DocumentObjectGroup", "UVPolygonsOffsets")
uvpolygonsfoldlines = getemptyobject(doc, "App::DocumentObjectGroup", "UVPolygonsFoldlines")

from p7modules.p7wingeval import WingEval
wingeval = WingEval(doc.getObject("SectionGroup").OutList)
urange, vrange, seval, leadingedgelengths = wingeval.urange, wingeval.vrange, wingeval.seval, wingeval.leadingedgelengths


from p7modules.barmesh.basicgeo import P2, P3, Partition1, Along, I1
from p7modules.p7wingflatten_barmeshfuncs import polyloopvedgeseqpolyline, polylinewithinsurfaceoffset

surfacemeshdict = dict((uvpoly.Name[1:], [ P2(v.Point.x, v.Point.y)  for v in uvpoly.Shape.OrderedVertexes ])  for uvpoly in uvpolygons)

legsampleleng = 3.0

def splicereplacedpolylineintoloop(polyloop, i0, i1, polyline, legsampleleng):
	assert 0 < i0 < i1 < len(polyloop) - 1, (0, i0, i1, len(polyloop))
	def intermediatesamplelegsteps(p0, p1, legsampleleng):
		Nsteps = int((p1 - p0).Len()/legsampleleng + 0.9)
		return [ Along(i/Nsteps, p0, p1)  for i in range(1, Nsteps) ]
	return polyloop[:i0] + \
			intermediatesamplelegsteps(polyloop[i0-1], polyline[0], legsampleleng) + \
			polyline + \
			intermediatesamplelegsteps(polyline[-1], polyloop[i1+1], legsampleleng) + \
			polyloop[i1+1:]

# double folds are at 12-6 and 24-6 before the offset by 6 (all in mm!)
offsetstretchcomponents = [ ("US1", -10, vrange[1], 6, P2(0, 2), True), 
							("US2", 0, vrange[1], 6, P2(0, 2), True), 
							("TSM1", 10, vrange[0], 12, P2(0, -2), False), 
							("TSM1", 10, vrange[0], 18, P2(0, -2), True), 
							("TSM2", 0, vrange[0], 12, P2(0, -2), False), 
							("TSM2", 0, vrange[0], 18, P2(0, -2), True), 
							("TSR", 0, vrange[0], 12, P2(0, -2), False), 
							("TSR", 0, vrange[0], 18, P2(0, -2), True) 
						  ]

def sevalP3(u, v):
	p = seval(u, v)
	return P3(p.x, p.y, p.z)

polylinefoldlinepenmarks = { }
for patchname, irot, vedge, rad, spstep, spliceloop in offsetstretchcomponents:
	polyloop = surfacemeshdict[patchname]
	polyloop = polyloop[irot:] + polyloop[:irot]
	i0, i1 = polyloopvedgeseqpolyline(polyloop, vedge)
	print(patchname, i0, i1, rad)

	polyline = polyloop[i0:i1+1]
	if patchname not in polylinefoldlinepenmarks:
		polylinefoldlinepenmarks[patchname] = [ polyline ]
	polylineOffset = polylinewithinsurfaceoffset(sevalP3, polyline, rad, spstep)
	
	if spliceloop: 
		polyloop = splicereplacedpolylineintoloop(polyloop, i0, i1, polylineOffset, legsampleleng)
		surfacemeshdict[patchname] = polyloop
	else:
		polylinefoldlinepenmarks[patchname].append(polylineOffset)

	polyloop = surfacemeshdict[patchname]

for uvpoly in uvpolygons:
	name = uvpoly.Name[1:]
	polylineOffset = surfacemeshdict[name]
	assert uvpoly.Shape.isClosed()
	ws = createobjectingroup(doc, uvpolygonsoffsets, "Part::Feature", "x%s"%name)
	polylineOffsetV = [ Vector(p[0], p[1], 0)  for p in polylineOffset]
	ws.Shape = Part.makePolygon(polylineOffsetV+[polylineOffsetV[0]])
	ws.ViewObject.PointColor = uvpoly.ViewObject.PointColor
	
	for polylinefoldlinepenmark in polylinefoldlinepenmarks.get(name, [ ]):
		ws = createobjectingroup(doc, uvpolygonsfoldlines, "Part::Feature", "d%s_%d"%(name, len(uvpolygonsfoldlines.OutList)))
		ws.Shape = Part.makePolygon([Vector(p[0], p[1], 0)  for p in polylinefoldlinepenmark])
		ws.ViewObject.PointColor = uvpoly.ViewObject.PointColor
	
	
	
