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
from p7modules.p7wingeval import getemptyobject, createobjectingroup, removeObjectRecurse

doc = App.ActiveDocument
R13type = doc.getObject("Group")
print("R13 type offsets" if R13type else "P7 wing offsets")

uvpolygons = doc.UVPolygons.OutList
uvpolygonsoffsets = getemptyobject(doc, "App::DocumentObjectGroup", "UVPolygonsOffsets")
uvpolygonsfoldlines = getemptyobject(doc, "App::DocumentObjectGroup", "UVPolygonsFoldlines")

from p7modules.p7wingeval import WingEval
R13type = doc.getObject("Group")
wingeval = WingEval(doc.getObject("Group" if R13type else "SectionGroup").OutList, R13type)
urange, vrange, seval = wingeval.urange, wingeval.vrange, wingeval.seval


from p7modules.barmesh.basicgeo import P2, P3, Partition1, Along, I1
from p7modules.p7wingflatten_barmeshfuncs import polyloopvedgeseqpolyline, polylinewithinsurfaceoffset

surfacemeshdict = dict((uvpoly.Name[1:], [ P2(v.Point.x, v.Point.y)  for v in uvpoly.Shape.OrderedVertexes ])  for uvpoly in uvpolygons)

#####scratch work
#uvpoly = doc.UVPolygons.OutList[0]
#polyloop = [ P2(v.Point.x, v.Point.y)  for v in uvpoly.Shape.OrderedVertexes ]
#[ i  for i in range(len(polyloop))  if polyloop[i].v == 0 ], len(polyloop)
##for patchname, irot, vedge, rad, spstep, spliceloop in offsetstretchcomponents:
#irot = -10
#Dpolyloop = polyloop[irot:] + polyloop[:irot]
#[ i  for i in range(len(Dpolyloop))  if Dpolyloop[i].v == 0 ], len(Dpolyloop)
#####

legsampleleng = 3.0

# Use this to check what the extended bspline contour looks like 20 units off either end
#import numpy
#doc = App.ActiveDocument
#e = doc.SectionGroup.OutList[0]
#params = numpy.linspace(e.Shape.FirstParameter - 20, e.Shape.LastParameter + 20, 300)
#ws = doc.addObject("Part::Feature", "extcurve")
#ws.Shape = Part.makePolygon([e.Shape.valueAt(l)  for l in params ])


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

# This is where we program in the sections of the contour that will be offset, identified from start and end points in UV
# If 2 offsets happen in same contour then you need to do one first and then look up the values of the offset point
# The edgestartpt amd edgeendpt UV positions are anti-clockwise around the polyloop
offsetstretchcomponentsRG = [ ]
if R13type:
	offsetstretchcomponentsRG = [ 
		{ "patchname":"TSR", "rad":18.5, "spstep":P2(0,-2), "edgestartpt":P2(0,0), "edgeendpt":P2(4417.58,0), "spliceloop":True }, 
		{ "patchname":"TSR", "rad":6.5, "spstep":P2(2,0), "edgestartpt":P2(4417.58,-59.044231), "edgeendpt":P2(4417.58,835), "spliceloop":True } 
	]
else:
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
	for patchname, irot, vedge, rad, spstep, spliceloop in offsetstretchcomponents:
		offsetstretchcomponentsRG.append({ "patchname":patchname, "irot":irot, "vedge":vedge, "rad":rad, "spstep":spstep, "spliceloop":spliceloop })
	
	



def sevalP3(u, v):
	p = seval(u, v)
	return P3(p.x, p.y, p.z)

def polyloopvedgeseqpolylineW(polyloop, vedge):
	vedgeseq = [ [ ] ]
	for i in range(len(polyloop)):
		if abs(polyloop[i].v - vedge) < 1e-5:
			if vedgeseq[-1]:
				vedgeseq[-1][-1] = i
			else:
				vedgeseq[-1] = [i, i]
		elif vedgeseq[-1]:
			vedgeseq.append([])
	if not vedgeseq[-1]:
		vedgeseq.pop()
	assert len(vedgeseq) == 1, vedgeseq
	i0, i1 = vedgeseq[0]
	assert 0 < i0 < i1 < len(polyloop) - 1, (0, i0, i1, len(polyloop), "try a different value for irot")
	return i0, i1


def polyloopvedgeseqpolylineBatwing(polyloop, vedge):
	inxs = [ i  for i in range(len(polyloop))  if polyloop[i].v == vedge ]
	i0, i1 = min(inxs), max(inxs)
	assert (max(abs(polyloop[i].v - vedge) for i in range(i0, i1+1)) < 100), ("point edge too far from edge between", i0, i1, len(polyloop), polyloop[i0], polyloop[i1])
	return i0, i1

def selectpolyloopindex(polyloop, p):
	i = min(range(len(polyloop)), key=lambda X: (polyloop[X] - p).Lensq())
	dst = (polyloop[i] - p).Len()
	assert dst < 0.5, ("too far out: edgepoint ", p, "is", dst, "away")
	return i 
	
def polyloopvedgesFromEdgePoints(polyloop, osc):
	i0 = selectpolyloopindex(polyloop, osc["edgestartpt"])
	i1 = selectpolyloopindex(polyloop, osc["edgeendpt"])
	print("selection range", i0, i1)
	irot = 0
	if i0 > i1:
		irot = (i0 + i1)//2
	elif i0 < 3:
		irot = -10
	elif i1 > len(polyloop) - 4:
		irot = 10
	if irot != 0:
		polyloop = polyloop[irot:] + polyloop[:irot]
		i0 = selectpolyloopindex(polyloop, osc["edgestartpt"])
		i1 = selectpolyloopindex(polyloop, osc["edgeendpt"])
		print("irot by", irot, "selection range now", i0, i1)
		assert (i0 >= 3) and (i1 <= len(polyloop) - 4) and (i0 < i1)
	return polyloop, i0, i1


polylinefoldlinepenmarks = { }
for osc in offsetstretchcomponentsRG:
	patchname = osc["patchname"]
	polyloop = surfacemeshdict[patchname]
	rad = osc["rad"]
	spstep = osc["spstep"]
	spliceloop = osc["spliceloop"]

	if R13type:
		print("working on ", patchname, rad, spstep)
		polyloop, i0, i1 = polyloopvedgesFromEdgePoints(polyloop, osc)
		
	else:
		irot = osc["irot"]
		vedge = osc["vedge"]
		polyloop = polyloop[irot:] + polyloop[:irot]
		i0, i1 = polyloopvedgeseqpolylineW(polyloop, vedge)
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
	
	
	
