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
# Do this if running by pasting into Python window
#sys.path.append("/home/julian/repositories/HGnotebooks/wingflattening/freecad_macro_work")
from p7modules.p7wingeval import WingEval
from p7modules.p7wingeval import getemptyobject, createobjectingroup, removeObjectRecurse

doc = App.ActiveDocument

R13type = doc.getObject("Group")
wingeval = WingEval(doc.getObject("Group" if R13type else "SectionGroup").OutList, R13type)


patchuvpolygonsGroup = doc.getObject("UVPolygonsOffsets") or doc.getObject("UVPolygons")
print("** using", patchuvpolygonsGroup.Name)
patchuvpolygons = patchuvpolygonsGroup.OutList 
uvtg = getemptyobject(doc, "App::DocumentObjectGroup", "UVTriangulations")

# Program in the offsets for each of the polygons (allows same polygon to get 2 offsets)
patchuvpolygonMakerList = [ ]
for patchuvpolygon in patchuvpolygons:
	polygonname = patchuvpolygon.Name[1:]
	patchuvpolygonMakerList.append([polygonname, patchuvpolygon, 6.0 ]) 
	if R13type and polygonname == "LE":
		patchuvpolygonMakerList.append(["LEM", patchuvpolygon, 12.5 ]) 


from p7modules.barmesh.tribarmes import TriangleBarMesh, TriangleBar, MakeTriangleBoxing
from p7modules.barmesh import barmesh
from p7modules.p7wingflatten_barmeshfuncs import ImplicitAreaBallOffsetOfClosedContour, WNode


urange, vrange, seval, uvals = wingeval.urange, wingeval.vrange, wingeval.seval, wingeval.uvals


from p7modules.barmesh.basicgeo import P2, P3, Partition1, Along, I1
from p7modules.p7wingflatten_barmeshfuncs import MakeRectBarmeshForWingParametrization, subloopsequence
from p7modules.barmesh.barmeshslicer import BarMeshSlicer
from p7modules.barmesh.mainfunctions import nodewithinpairs, BarMeshContoursN
from p7modules.p7wingflatten_barmeshfuncs import findallnodesandpolys, cpolytriangulate


#
# Calculate the offsets of the polygons based on a common rectangular subdivision spacing xpartA, xpartB
# and product a contour in UV space that would project to the offset 3D surface
#

uspacing, vspacing = 20, 10

urgA, vrgA = I1(*urange).Inflate(90), I1(*vrange).Inflate(110)
xpartA = Partition1(urgA.lo, urgA.hi, int(urgA.Leng()/uspacing + 2))
ypartA = Partition1(vrgA.lo, vrgA.hi, int(vrgA.Leng()/vspacing + 2))

def SubPartition(part, vlo, vhi):
	res = Partition1(0, 1, 2)
	ilo, ihi = part.GetPartRange(vlo, vhi)
	res.vs = part.vs[ilo:ihi+2]
	res.lo, res.hi = res.vs[0], res.vs[-1]
	res.nparts = ihi - ilo + 1
	assert len(res.vs) == res.nparts + 1
	assert res.lo < vlo < vhi < res.hi, (res.lo , vlo , vhi , res.hi)
	return res

def sevalP3(u, v):
	p = seval(u, v)
	return P3(p.x, p.y, p.z)

# Main loop through the polygons
for i in range(0, len(patchuvpolygonMakerList)):
	patchname, s, radoffset = patchuvpolygonMakerList[i]
	rd2 = max(uspacing, vspacing, radoffset*2) + 10

	print("\nStarting", i, patchname, radoffset)
	polyloop = [ P2(v.Point.x, v.Point.y)  for v in s.Shape.OrderedVertexes ]
	polyloopW = [ sevalP3(p[0], p[1])  for p in polyloop ]
	urg = I1.AbsorbList(p[0]  for p in polyloop).Inflate(60)
	vrg = I1.AbsorbList(p[1]  for p in polyloop).Inflate(80)
	xpart = SubPartition(xpartA, urg.lo, urg.hi)
	ypart = SubPartition(ypartA, vrg.lo, vrg.hi)

	iaoffset = ImplicitAreaBallOffsetOfClosedContour(polyloopW, polyloop, boxwidth=10)
	bm = MakeRectBarmeshForWingParametrization(sevalP3, xpart, ypart)
	contourdelta = min(uspacing, vspacing)*0.2
    
	bms = BarMeshSlicer(bm, iaoffset, rd=radoffset, rd2=rd2, contourdotdiff=0.95, contourdelta=contourdelta, lamendgap=0.001, strictlyplanarbarmesh=False)

	#bms.initializecutsanddistances()
	bms.fullmakeslice()

	contsN, topbars = BarMeshContoursN(bm, barmesh.PZ_BEYOND_R)
	tnodes, cpolys = findallnodesandpolys(bm)
	ptsF = [ node.sp  for node in tnodes ]
	tris = [ ]
	for cpoly in cpolys:
		tris.extend(cpolytriangulate(ptsF, cpoly))

	# need to create all the triangles like an STL and hope for the system to find that most of the points are the same
	ptsFV = [ Vector(*p)  for p in ptsF ]
	facets = [ [ ptsFV[i0], ptsFV[i1], ptsFV[i2] ]  for i0, i1, i2 in tris ]

	mesh = createobjectingroup(doc, uvtg, "Mesh::Feature", "m%s"%patchname)
	mesh.Mesh = Mesh.Mesh(facets)
	mesh.ViewObject.Lighting = "Two side"
	mesh.ViewObject.DisplayMode = "Wireframe"
	mesh.ViewObject.ShapeColor = s.ViewObject.PointColor
	mesh.ViewObject.LineColor = s.ViewObject.PointColor

	print(mesh.Name, "tris", len(tris), "ptsF", len(ptsF), mesh.Mesh)
	
