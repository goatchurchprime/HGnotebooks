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

#from p7modules.p7wingflatten_barmeshfuncs import findallnodesandpolys, cpolyuvvectorstransF
from p7modules.barmesh.basicgeo import P2, P3, Partition1, Along, I1

doc = App.ActiveDocument

from p7modules.p7wingeval import WingEval
from p7modules.p7wingeval import getemptyobject, createobjectingroup

R13type = doc.getObject("Group")
wingeval = WingEval(doc.getObject("Group" if R13type else "SectionGroup").OutList, R13type)
urange, vrange, seval, uvals = wingeval.urange, wingeval.vrange, wingeval.seval, wingeval.uvals

from p7modules.p7wingflatten_barmeshfuncs import sliceupatnones

uvpolygonsGroup = doc.getObject("UVPolygonsOffsets") or doc.getObject("UVPolygons")
print("** using", uvpolygonsGroup.Name)
uvpolygons = uvpolygonsGroup.OutList

uvtriangulations = doc.UVTriangulations.OutList
striangulations = doc.STriangulations.OutList
sflattened = doc.SFlattened.OutList
uvfoldlines = doc.UVPolygonsFoldlines.OutList if doc.getObject("UVPolygonsFoldlines") else [ ]
postpenupper = doc.getObject("postpenupper") 
postpenlower = doc.getObject("postpenlower") 


assert len(uvpolygons) == len(uvtriangulations) == len(striangulations), len(sflattened)
pencilg = getemptyobject(doc, "App::DocumentObjectGroup", "SPencil")
pencilT = getemptyobject(doc, "App::DocumentObjectGroup", "TPencil")

# get the batten detail file and set the duplicated positions for the pen cuts
battendetailfile = None if R13type else os.path.join(os.path.split(__file__)[0], "batten detail TSR.dxf")
#battendetailfile = "/home/julian/repositories/HGnotebooks/wingflattening/freecad_macro_work/batten detail TSR.dxf"

if battendetailfile:
	import ezdxf
	docbattendetail = ezdxf.readfile(battendetailfile)
	dxflines = [ k  for k in docbattendetail.entities  if "-CUT" in k.dxf.layer or "PLOT" in k.dxf.layer ]
	battendetaillines = [ ]
	for line in dxflines:
		p0, p1 = P2(line.dxf.start.x, line.dxf.start.y), P2(line.dxf.end.x, line.dxf.end.y)
		battendetaillines.extend([p0, p1])
	dxflinelayers = [ k.dxf.layer  for k in dxflines ]
	uvoffsettobettertriangle = P2(0, 100)
	battonuvdetailpositions = [ (P2(u, vrange[0]), P2(u, vrange[0])+uvoffsettobettertriangle)  for u in uvals[1:-1] ]


def cp2t(t):
	return [ P2(t[0][0], t[0][1]), P2(t[1][0], t[1][1]), P2(t[2][0], t[2][1]) ]

def cpolyuvvectorstransC(uvpts, fptsT):
	assert len(uvpts) == len(fptsT)
	n = len(uvpts)
	cpt = sum(uvpts, P2(0,0))*(1.0/n)
	cptT = sum(fptsT, P2(0,0))*(1.0/n)
	jp = max((abs(P2.Dot(uvpts[j] - cpt, P2.APerp(uvpts[(j+1)%n] - cpt))), j)  for j in range(n))
	vj = uvpts[jp[1]] - cpt
	vj1 = uvpts[(jp[1]+1)%n] - cpt

	urvec = P2(vj1.v, -vj.v)
	urvec = urvec*(1.0/P2.Dot(urvec, P2(vj.u, vj1.u)))
	vrvec = P2(vj1.u, -vj.u)
	vrvec = vrvec*(1.0/P2.Dot(vrvec, P2(vj.v, vj1.v)))
	# this has gotten muddled.  Should be simpler since the following two are negative of each other
	# P2.Dot(urvec, P2(vj.u, vj1.u)) = vj1.v*vj.u - vj.v*vj1.u
	# P2.Dot(vrvec, P2(vj.v, vj1.v)) = vj1.u*vj.v - vj.u*vj1.v
	# set solve: (urvec.u*vj + urvec.v*vj1).v = 0, which is why it uses only v components 

	vjT = fptsT[jp[1]] - cptT
	vj1T = fptsT[(jp[1]+1)%n] - cptT

	# vc = p - cc["cpt"]
	#vcp = cc["urvec"]*vc.u + cc["vrvec"]*vc.v
	#vcs = cc["vj"]*vcp.u + cc["vj1"]*vcp.v ->  vc
	area = abs(P2.Dot(fptsT[1] - fptsT[0], P2.APerp(fptsT[2] - fptsT[0]))*0.5)
	uvarea = abs(P2.Dot(uvpts[1] - uvpts[0], P2.APerp(uvpts[2] - uvpts[0]))*0.5)

	return { "cpt":cpt, "cptT":cptT, "urvec":urvec, "vrvec":vrvec, 
			 "vj":vj, "vj1":vj1, "vjT":vjT, "vj1T":vj1T, "area":area, "uvarea":uvarea }

uspacing, vspacing = 20, 20
battonuvlines = [ ]
for u in uvals[1:-1]:
	battonuvlines.append([P2(u, v)  for v in numpy.arange(vrange[0]-vspacing, vrange[1]+vspacing, vspacing)])

#uvmesh = doc.UVTriangulations.OutList[2]
#flattenedmesh = doc.SFlattened.OutList[2]
#uvtranslist = [ cpolyuvvectorstransC(cp2t(a.Points), cp2t(b.Points))  for a, b in zip(uvmesh.Mesh.Facets, flattenedmesh.Mesh.Facets) ]

def generateTransColumns(uvmesh, flattenedmesh):
	uvtranslist = [ cpolyuvvectorstransC(cp2t(a.Points), cp2t(b.Points))  for a, b in zip(uvmesh.Mesh.Facets, flattenedmesh.Mesh.Facets) ]
	uvareacutoff = max(t["uvarea"]  for t in uvtranslist)*0.2
	uvtranslistC = [t  for t in uvtranslist  if t["uvarea"]  > uvareacutoff]
	print("discarding", len(uvtranslist)-len(uvtranslistC), "small triangles out of", len(uvtranslist))

	# recreate the original partition of the urange which matches the zoning of the areas already there
	# (we could derive it from the inputs, but I'm porting this code across from functions which 
	# depended on carrying across the same barmesh as between the operations, instead of saving 
	# them out to unstructured meshes as we have here now) 
	radoffset = 6
	rd2 = max(uspacing, vspacing, radoffset*2) + 10
	urgA, vrgA = I1(*urange).Inflate(60), I1(*vrange).Inflate(110)
	xpartA = Partition1(urgA.lo, urgA.hi, int(urgA.Leng()/uspacing + 2))
	ypartA = Partition1(vrgA.lo, vrgA.hi, int(vrgA.Leng()/vspacing + 2))
	uvtranslistCcolumns = [ [ ]  for ix in range(xpartA.nparts) ] 
	for uvtrans in uvtranslistC:
		uvtranslistCcolumns[xpartA.GetPart(uvtrans["cpt"].u)].append(uvtrans)
	return xpartA, uvtranslistCcolumns

def findcctriangleinmesh(sp, xpart, uvtranslistCcolumns):
	if not (xpart.lo < sp[0] < xpart.hi):
		return None
	ix = xpart.GetPart(sp[0])
	if len(uvtranslistCcolumns[ix]) == 0:
		return None
	return min((cc  for cc in uvtranslistCcolumns[ix]), key=lambda X: (X["cpt"] - sp).Len())

def projectspbarmeshF(sp, xpart, uvtranslistCcolumns, bFlattenedPatches=True):
	cc = findcctriangleinmesh(sp, xpart, uvtranslistCcolumns)
	if cc is None:
		return None
	if abs(cc["cpt"][0] - sp.u) > uspacing or abs(cc["cpt"][1] - sp.v) > vspacing:
		return None
	vc = sp - cc["cpt"]
	vcp = cc["urvec"]*vc.u + cc["vrvec"]*vc.v
	vcs = cc["vj"]*vcp.u + cc["vj1"]*vcp.v # should be same as vc
	vcsT = cc["vjT"]*vcp.u + cc["vj1T"]*vcp.v
	if bFlattenedPatches:
		return vcsT + cc["cptT"]
	return vcs + cc["cpt"]


def projectdetaillinesF(sporigin, sptriangle, xpart, uvtranslistCcolumns, uspacing, vspacing, battendetaillines):
    cc = findcctriangleinmesh(sptriangle, xpart, uvtranslistCcolumns)
    if cc is None:
        return [ ]
    if abs(cc["cpt"][0] - sptriangle.u) > uspacing or abs(cc["cpt"][1] - sptriangle.v) > vspacing:
        return [ ]
    vc = sporigin - cc["cpt"]
    vcp = cc["urvec"]*vc.u + cc["vrvec"]*vc.v
    vcs = cc["vj"]*vcp.u + cc["vj1"]*vcp.v # should be same as vc
    vcsT = cc["vjT"]*vcp.u + cc["vj1T"]*vcp.v

    # use the 6mm expansion on either side of this line to our advantage
    ccLeft = findcctriangleinmesh(sptriangle-P2(5, 0), xpart, uvtranslistCcolumns)
    ccRight = findcctriangleinmesh(sptriangle+P2(5, 0), xpart, uvtranslistCcolumns)
    assert ccLeft != None and ccRight != None, (ccLeft, ccRight)
    
    trailingedgevecL = P2.ZNorm(ccLeft["vjT"]*ccLeft["urvec"].u + ccLeft["vj1T"]*ccLeft["urvec"].v)
    trailingedgevecR = P2.ZNorm(ccRight["vjT"]*ccRight["urvec"].u + ccRight["vj1T"]*ccRight["urvec"].v)
    #trailingedgevec = P2.ZNorm(cc["vjT"]*cc["urvec"].u + cc["vj1T"]*cc["urvec"].v)
    trailingedgevec = P2.ZNorm(trailingedgevecL + trailingedgevecR)
    #print("trailingedge angles ", trailingedgevecL.Arg(), trailingedgevecR.Arg())
    trailingedgevecPerp = P2.ZNorm(cc["vjT"]*cc["vrvec"].u + cc["vj1T"]*cc["vrvec"].v)
    #trailingedgevec = P2.CPerp(trailingedgevecPerp)
    
    battendetails = [ ]
    for lsp in battendetaillines:
        battendetails.append(vcsT + cc["cptT"] + trailingedgevec*lsp.u + trailingedgevecPerp*lsp.v)
    return battendetails

legsampleleng = 3.0
def projectpostpen(postpensketch, bupperface):
	resuv = [ ]
	for g in postpensketch.GeometryFacadeList:
		if not g.Construction:
			gg = g.Geometry
			num = int(math.ceil(gg.length()/legsampleleng) + 1)
			params = numpy.linspace(gg.FirstParameter, gg.LastParameter, num)
			qs = [ ]
			for a in params:
				p = gg.value(a)
				q = wingeval.inverse_seval(p.x, p.y, bupperface, tol=0.001)
				qs.append(P2(q[0], q[1]))
			if len(qs) > 2:
				resuv.append(qs)
	return resuv

postpenuvs = projectpostpen(postpenupper, True) + projectpostpen(postpenlower, False)
for ip, ppuvs in enumerate(postpenuvs):
	ws = createobjectingroup(doc, pencilT, "Part::Feature", "t%d"%ip)
	ws.Shape = Part.makePolygon([seval(p.u, p.v)  for p in ppuvs])
	# ws.Shape = Part.makePolygon([Vector(p.u, p.v, 1.5)  for p in ppuvs])  # to draw instead into UV space
	print("postpenuvs", ip, len(ppuvs))


#
# main loop across the different patches here
#
for I in range(len(uvtriangulations)):
	uvmesh = uvtriangulations[I]
	surfacemesh = striangulations[I]
	flattenedmesh = sflattened[I]
	assert uvmesh.Mesh.CountFacets == flattenedmesh.Mesh.CountFacets == surfacemesh.Mesh.CountFacets
	name = uvmesh.Name[1:]
	uvfoldlineL = [ [ P2(v.Point.x, v.Point.y)  for v in uvfoldline.Shape.OrderedVertexes ]  for uvfoldline in uvfoldlines  if uvfoldline.Name[1:len(name)+1] == name ]
	print("Name", name, "with fold lines", len(uvfoldlineL))

	pencilgS = createobjectingroup(doc, pencilg, "App::DocumentObjectGroup", "p%s"%name)

	xpart, uvtranslistCcolumns = generateTransColumns(uvmesh, flattenedmesh)

	# These are the offset polygons of the other patches that are 
	# to be drawn onto this patch
	spsFS = [ ]
	for J in range(len(uvtriangulations)):
		if J == I:
			continue
		spsJ = [ P2(v.Point.x, v.Point.y)  for v in uvpolygons[J].Shape.OrderedVertexes ]
		spsJF = [ projectspbarmeshF(sp, xpart, uvtranslistCcolumns)  for sp in spsJ ]
		spsFS.extend(sliceupatnones(spsJF))

	for spsS in spsFS:
		ws = createobjectingroup(doc, pencilgS, "Part::Feature", "w%s_%d"%(name, len(pencilgS.OutList)))
		ws.Shape = Part.makePolygon([Vector(p[0], p[1], 1.0)  for p in spsS])
		ws.ViewObject.PointColor = (1.0,0.0,0.0)
		ws.ViewObject.LineColor = (1.0,0.0,0.0)

	# These are the batten details on the P7 wing only
	if battendetailfile:
		battendetailsegments = [ ]
		for sporigin, sptriangle in battonuvdetailpositions:
			battendetailsegments.extend(projectdetaillinesF(sporigin, sptriangle, xpart, uvtranslistCcolumns, uspacing, vspacing, battendetaillines))
		for i in range(0, len(battendetailsegments), 2):
			bdsegs = [ Vector(battendetailsegments[i][0], battendetailsegments[i][1], 1), Vector(battendetailsegments[i+1][0], battendetailsegments[i+1][1], 1) ]
			ws = createobjectingroup(doc, pencilgS, "Part::Feature", "b%s_%d"%(name, len(pencilgS.OutList)))
			ws.Shape = Part.makePolygon(bdsegs)
			ws.ViewObject.PointColor = (0.0,0.0,1.0)
			ws.ViewObject.LineColor = (0.0,0.0,1.0)

	# These are the pencuts, upper and lower merged into one
	for ip, ppuvs in enumerate(postpenuvs):
		ppuvsF = [ projectspbarmeshF(sp, xpart, uvtranslistCcolumns)  for sp in ppuvs ]
		for iip, spsS in enumerate(sliceupatnones(ppuvsF)):
			ws = createobjectingroup(doc, pencilgS, "Part::Feature", "e%s_%d_%d"%(name, ip, iip))
			ws.Shape = Part.makePolygon([Vector(p[0], p[1], 1.0)  for p in spsS])
			ws.ViewObject.PointColor = (1.0,0.0,1.0)
			ws.ViewObject.LineColor = (1.0,0.0,1.0)

	# these are the fold lines
	uvfoldlineLFS= [ ]
	for uvfoldline in uvfoldlineL:
		battonlineF = [ projectspbarmeshF(sp, xpart, uvtranslistCcolumns)  for sp in uvfoldline ]
		uvfoldlineLFS.extend(sliceupatnones(battonlineF))
	for spsS in uvfoldlineLFS:
		ws = createobjectingroup(doc, pencilgS, "Part::Feature", "l%s_%d"%(name, len(pencilgS.OutList)))
		ws.Shape = Part.makePolygon([Vector(p[0], p[1], 1.0)  for p in spsS])
		ws.ViewObject.PointColor = (0.0,0.8,0.0)
		ws.ViewObject.LineColor = (0.0,0.8,0.0)

