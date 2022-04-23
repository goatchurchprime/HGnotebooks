# -*- coding: utf-8 -*-

# Macro to generate the pencil lines onto each of the patches 
# based on the other outlines and on the batton patch design

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv, sys
import numpy
from FreeCAD import Vector, Rotation
import ezdxf

sys.path.append(os.path.split(__file__)[0])
from p7modules.barmesh.basicgeo import P2

from p7modules.p7wingflatten_barmeshfuncs import MeshBoundary
from p7modules.p7wingeval import getemptyobject, createobjectingroup, removeObjectRecurse

doc = App.ActiveDocument

sflattened = doc.SFlattened.OutList
spencil = doc.SPencil.OutList
thinnedlines = getemptyobject(doc, "App::DocumentObjectGroup", "ThinnedLines")

import ezdxf, os

AAMA_CUT = "1"
AAMA_DRAW = "8"
AAMA_INTCUT = "11"

dxfversion = "R2013"

outputfilename = os.path.join(os.path.split(__file__)[0], "../p7test.dxf")
print("Saving", outputfilename)

blockbasename = os.path.splitext(os.path.split(outputfilename)[1])[0]
dxc = ezdxf.new(dxfversion)

aamacutlayer = dxc.layers.new("1", {"color":1})
aamadrawlayer = dxc.layers.new("8", {"color":4})
aamaintcutlayer = dxc.layers.new("11", {"color":3})
patchshapelayer = dxc.layers.new("21", {"color":21})

thinningtolerance = 0.25
def pointlinedistance(p0, p1, q):
	v = p1 - p0
	vsq = v.dot(v)
	if vsq == 0:
		return (p0 - q).magnitude
	lam = max(0.0, min(1.0, v.dot(q - p0)/vsq))
	return (p0 + v*lam - q).magnitude

def ThinDXFpoly(plp):
	istack = [ (0, len(plp)-1) ] 
	iseq = [ 0 ]
	while len(istack) != 0:
		i0, i1 = istack.pop()
		if i1 - i0 >	 1:
			p0, p1 = plp[i0], plp[i1]
			d, im = max((pointlinedistance(p0, p1, plp[i]), i)  for i in range(i0+1, i1))
			if d > thinningtolerance:
				istack.append((im, i1))
				istack.append((i0, im))
				continue
		assert iseq[-1] == i0
		iseq.append(i1)
	#print(len(plp), len(iseq))
	#return plp
	return [ plp[i]  for i in iseq ]
	
def ShowInThinnedLines(plp, coff, name):
	ws = createobjectingroup(doc, thinnedlines, "Part::Feature", name)
	ws.Shape = Part.makePolygon([Vector(p.x+coff.x, p.y+coff.y, 2)  for p in plp])
	ws.ViewObject.LineColor = (0.0,0.0,0.9)

for fmesh in sflattened:
	meshcentre = fmesh.Mesh.BoundBox.Center
	blockname = fmesh.Name[1:]
	print("Working on", blockname)
	spencild = doc.getObject("p"+blockname)
	block = dxc.blocks.new(name=blockname)
	blockcentre = ezdxf.math.Vector(meshcentre.x, meshcentre.y, 0)

	cpolys = MeshBoundary(fmesh)
	for cpoly in cpolys:
		patchboundary = [ ezdxf.math.Vector(p[0], p[1], 0)-blockcentre  for p in cpoly ]
		patchboundary.append(patchboundary[0])   # Make the closed shape closed
		thinnedpatchboundary = ThinDXFpoly(patchboundary)
		ShowInThinnedLines(thinnedpatchboundary, blockcentre, "%s_thin"%fmesh.Name)
		block.add_polyline2d(thinnedpatchboundary, dxfattribs={ "layer":aamacutlayer.dxf.name })

	print("Now doing pencilcuts", len(spencild.OutList))
	for w in spencild.OutList:
		pencilline = [ ezdxf.math.Vector(v.Point.x, v.Point.y, 0)-blockcentre  for v in w.Shape.OrderedVertexes ]
		thinnedpencilline = ThinDXFpoly(pencilline)
		ShowInThinnedLines(thinnedpencilline, blockcentre, "%s_thin"%w.Name)
		block.add_polyline2d(thinnedpencilline, dxfattribs={ "layer":aamadrawlayer.dxf.name })
		
	msp = dxc.modelspace()
	dxfattribs = {'rotation': 0, 'linetype':'BYLAYER' }
	k = msp.add_blockref(blockname, blockcentre, dxfattribs=dxfattribs)

dxc.set_modelspace_vport(height=2300, center=(1800, 900))
dxc.saveas(outputfilename)

	
