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

doc = App.ActiveDocument

sflattened = doc.SFlattened.OutList
spencil = doc.SPencil.OutList

import ezdxf, os

AAMA_CUT = "1"
AAMA_DRAW = "8"
AAMA_INTCUT = "11"

dxfversion = "R12"

outputfilename = os.path.join(os.path.split(__file__)[0], "../p7test.dxf")
print("Saving", outputfilename)

blockbasename = os.path.splitext(os.path.split(outputfilename)[1])[0]
dxc = ezdxf.new(dxfversion)

aamacutlayer = dxc.layers.new("1", {"color":1})
aamadrawlayer = dxc.layers.new("8", {"color":4})
aamaintcutlayer = dxc.layers.new("11", {"color":3})
patchshapelayer = dxc.layers.new("21", {"color":21})

def MeshBoundary(mesh):
	#fpts, tris = fmesh.Mesh.Topology
	tbarmesh = TriangleBarMesh()
	trpts = [ sum(f.Points, ())  for f in fmesh.Mesh.Facets ]
	tbarmesh.BuildTriangleBarmesh(trpts)
	assert len(tbarmesh.nodes) == fmesh.Mesh.CountPoints
	assert len(tbarmesh.bars) == fmesh.Mesh.CountEdges

	tbarcycles = set()
	for bar in tbarmesh.bars:
		if bar.barforeright is None:
			tbarcycles.add((bar, bar.nodeback))
		elif bar.barbackleft is None:
			tbarcycles.add((bar, bar.nodefore))

	cpolys = [ ]
	while len(tbarcycles):
		cbar, cnode = tbarcycles.pop()
		ccpoly = [ ]
		ccbar, ccnode = cbar, cnode
		while True:
			ccpoly.append(ccnode.p)
			while (lccbar:=ccbar.GetForeRightBL(ccbar.nodefore == ccnode)) is not None:
				ccbar = lccbar
			ccnode = ccbar.GetNodeFore(ccbar.nodeback == ccnode)
			if ccbar == cbar and ccnode == cnode:
				break
			tbarcycles.remove((ccbar, ccnode))
		cpolys.append(ccpoly)
	return cpolys

for fmesh in sflattened:
	meshcentre = fmesh.Mesh.BoundBox.Center
	blockname = fmesh.Name[1:]
	spencild = doc.getObject("p"+blockname)
	block = dxc.blocks.new(name=blockname)
	blockcentre = ezdxf.math.Vec3(meshcentre.x, meshcentre.y, 0)

	cpolys = MeshBoundary(fmesh.Mesh)
	for cpoly in cpolys:
		patchboundary = [ ezdxf.math.Vec3(p[0], p[1], 0)-blockcentre  for p in cpoly ]
		patchboundary.append(patchboundary[0])
		block.add_polyline2d(patchboundary, dxfattribs={ "layer":aamacutlayer.dxf.name })

	for w in spencild.OutList:
		block.add_polyline2d([ ezdxf.math.Vec3(v.Point.x, v.Point.y, 0)-blockcentre  for v in w.Shape.OrderedVertexes ], dxfattribs={ "layer":aamadrawlayer.dxf.name })

	msp = dxc.modelspace()
	dxfattribs = {'rotation': 0, 'linetype':'BYLAYER' }
	k = msp.add_blockref(blockname, blockcentre, dxfattribs=dxfattribs)

dxc.set_modelspace_vport(height=2300, center=(1800, 900))
dxc.saveas(outputfilename)

	
