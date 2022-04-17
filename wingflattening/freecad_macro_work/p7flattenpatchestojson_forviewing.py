# -*- coding: utf-8 -*-

# Macro to generate the pencil lines onto each of the patches 
# based on the other outlines and on the batton patch design

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv, sys, json
import numpy

doc = App.ActiveDocument

sflattened = doc.SFlattened.OutList
striangulations = doc.STriangulations.OutList

outputfilename = os.path.join(os.path.split(__file__)[0], "../p7test.json")
#outputfilename = "/home/julian/repositories/HGnotebooks/wingflattening/freecad_macro_work/p7test.json"
print("Saving", outputfilename)


jdata = [ ]
for fmesh, smesh in zip(sflattened, striangulations):
	blockname = fmesh.Name[1:]
	assert blockname == smesh.Name[1:]

	ffpts = [ tuple(p.Vector)  for p in fmesh.Mesh.Points ]
	ftris = [ x.PointIndices  for x in fmesh.Mesh.Facets ]

	sfpts = [ tuple(p.Vector)  for p in smesh.Mesh.Points ]
	stris = [ x.PointIndices  for x in smesh.Mesh.Facets ]

	jdata.append([blockname, ffpts, ftris, sfpts, stris])

json.dump(jdata, open(outputfilename, "w"))
	
