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

patchuvpolygonsGroup = doc.getObject("UVPolygonsOffsets") or doc.getObject("UVPolygons")
print("** using", patchuvpolygonsGroup.Name)
patchuvpolygons = patchuvpolygonsGroup.OutList 
uvtg = getemptyobject(doc, "App::DocumentObjectGroup", "UVTriangulations")


# Do this if running by pasting into Python window
#sys.path.append("/home/julian/repositories/HGnotebooks/wingflattening/freecad_macro_work")

from p7modules.barmesh.tribarmes import TriangleBarMesh, TriangleBar, MakeTriangleBoxing
from p7modules.barmesh import barmesh
from p7modules.p7wingflatten_barmeshfuncs import ImplicitAreaBallOffsetOfClosedContour, WNode

from p7modules.p7wingeval import WingEval
wingeval = WingEval(doc.getObject("SectionGroup").OutList)
urange, vrange, seval, leadingedgelengths = wingeval.urange, wingeval.vrange, wingeval.seval, wingeval.leadingedgelengths


from p7modules.barmesh.basicgeo import P2, P3, Partition1, Along, I1
from p7modules.p7wingflatten_barmeshfuncs import MakeRectBarmeshForWingParametrization, subloopsequence
from p7modules.barmesh.barmeshslicer import BarMeshSlicer
from p7modules.barmesh.mainfunctions import nodewithinpairs, BarMeshContoursN
from p7modules.p7wingflatten_barmeshfuncs import findallnodesandpolys, cpolytriangulate


#
# Calculate the offsets of the polygons based on a common rectangular subdivision spacing xpartA, xpartB
# and product a contour in UV space that would project to the offset 3D surface
#

radoffset = 6
uspacing, vspacing = 20, 20
rd2 = max(uspacing, vspacing, radoffset*2) + 10

battonuvlines = [ ]
for u in leadingedgelengths[1:-1]:
	battonuvlines.append([P2(u, v)  for v in numpy.arange(vrange[0]-vspacing, vrange[1]+vspacing, vspacing)])

urgA, vrgA = I1(*urange).Inflate(60), I1(*vrange).Inflate(110)
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

for i in range(0, len(patchuvpolygons)):
	s = patchuvpolygons[i]
	print("\nStarting", i, s.Name)
	polyloop = [ P2(v.Point.x, v.Point.y)  for v in s.Shape.OrderedVertexes ]
	polyloopW = [ sevalP3(p[0], p[1])  for p in polyloop ]
	urg = I1.AbsorbList(p[0]  for p in polyloop).Inflate(50)
	vrg = I1.AbsorbList(p[1]  for p in polyloop).Inflate(50)
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

	mesh = createobjectingroup(doc, uvtg, "Mesh::Feature", "m%s"%s.Name[1:])
	mesh.Mesh = Mesh.Mesh(facets)
	mesh.ViewObject.Lighting = "Two side"
	mesh.ViewObject.DisplayMode = "Wireframe"
	mesh.ViewObject.ShapeColor = s.ViewObject.PointColor
	mesh.ViewObject.LineColor = s.ViewObject.PointColor

	print(mesh.Name, "tris", len(tris), "ptsF", len(ptsF), mesh.Mesh)
	
