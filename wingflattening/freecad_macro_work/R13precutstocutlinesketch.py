# -*- coding: utf-8 -*-

# Macro to generate the pencil lines onto each of the patches 
# based on the other outlines and on the batton patch design

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv, sys, math
import numpy
from FreeCAD import Vector, Rotation

sys.path.append(os.path.split(__file__)[0])

from p7modules.barmesh.basicgeo import P2, P3, Partition1, Along, I1
from p7modules.p7wingeval import WingEval
from p7modules.p7wingeval import getemptyobject, createobjectingroup

doc = App.ActiveDocument

cutlinesketch = doc.cutlinesketch
nnonconstructionlines = sum(int(not g.Construction)  for g in doc.cutlinesketch.GeometryFacadeList)
if nnonconstructionlines != 0:
	print("cutlinesketch contains %d non-construction lines" % nnonconstructionlines)
	print("Creating junk sketch for testing instead")
	cutlinesketch = getemptyobject(doc, "Sketcher::SketchObject", "cutlinesketch_Junk")

wingeval = WingEval(doc.getObject("SectionGroup").OutList)

legsampleleng = 3.0
def projectprecut(cutlinesketch, precutsketch, bupperface):
	for g in precutsketch.GeometryFacadeList:
		if not g.Construction:
			gg = g.Geometry
			num = int(math.ceil(gg.length()/legsampleleng) + 1)
			params = numpy.linspace(gg.FirstParameter, gg.LastParameter, num)
			qs = [ ]
			for a in params:
				p = gg.value(a)
				q = wingeval.inverse_seval(p.x, p.y, bupperface, tol=0.001)
				qs.append(Vector(q[0], q[1]))
			cbspline = Part.BSplineCurve()
			cbspline.approximate(qs, Parameters=params, DegMin=2, DegMax=2)
			print(cbspline)
			cutlinesketch.addGeometry(cbspline, False)

projectprecut(cutlinesketch, doc.precutupper, True)
projectprecut(cutlinesketch, doc.precutlower, False)
