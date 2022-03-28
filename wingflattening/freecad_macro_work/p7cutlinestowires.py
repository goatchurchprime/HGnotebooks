# -*- coding: utf-8 -*-
# Macro to make project7wing as list of wires and single bspline surface

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv
import numpy
from FreeCAD import Vector, Rotation

from p7modules.p7wingeval import urange, vrange, seval
print("Rangesss", urange, vrange)

doc = App.ActiveDocument
cutlinesketch = doc.cutlinesketch

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

# makes sets of one non-construction edge end point which are then merged according to each coincident constraint 
def extractcoincidentnodes(cutlinesketch):
	gsegs = dict((i, x.Geometry)  for i, x in enumerate(cutlinesketch.GeometryFacadeList)  if not x.Construction)
	gcpts = [ ((d.First, d.FirstPos), (d.Second, d.SecondPos))  for d in cutlinesketch.Constraints  if d.IsActive and d.Type == "Coincident" and d.First in gsegs and d.Second in gsegs ]
	gcptmap = dict((x, set([x]))  for x in [ (i, 1)  for i in gsegs.keys() ] + [ (i, 2)  for i in gsegs.keys() ] )
	for a, b in gcpts:
		u = gcptmap[a].union(gcptmap[b])
		for c in u:
			gcptmap[c] = u
		assert gcptmap[b] is gcptmap[a]
	gcptsets = [ ]
	gcptnmap = { }
	for x in gcptmap.keys():
		if gcptmap[x]:
			for y in gcptmap[x]:
				assert y not in gcptnmap
				gcptnmap[y] = len(gcptsets)
			gcptsets.append(gcptmap[x].copy())
			gcptmap[x].clear()
	return gcptsets, gcptnmap

# make a sorted array of edges according to angle from each connection list
def coincidentnodetanges(cutlinesketch, gcptset):
	g = cutlinesketch.Geometry
	Dpts = [ (g[i].StartPoint if d == 1 else g[i].EndPoint)  for i, d in gcptset ]
	Dptsavg = sum(Dpts, Vector())*(1.0/len(Dpts))
	assert max([(Dptsavg - x).Length  for x in Dpts]) < 0.001, ("Coincident point not coincident", Dpts)
	Dpts = [ (g[i].StartPoint if d == 1 else g[i].EndPoint)  for i, d in gcptset ]
	gcptorder = [ ]
	for i, d in gcptset:
		v = (g[i].tangent(g[i].FirstParameter)[0] if d == 1 else -g[i].tangent(g[i].LastParameter)[0])
		gcptorder.append((math.atan2(v.y, v.x), (i, d)))
	gcptorder.sort()
	return gcptorder
	
def extractsequences(gcptorders, gcptnmap):
	visited2 = { }
	seqs = [ ]
	for i, d in gcptnmap.keys():
		if (i, d) not in visited2:
			seq = [ ]
			while (i, d) not in visited2:
				seq.append((i, d))
				visited2[(i, d)] = len(seqs)
				dE = (2 if d == 1 else 1)
				gcptn = gcptorders[gcptnmap[(i, dE)]]
				for j in range(len(gcptn)):
					if gcptn[j][1] == (i, dE):
						i2, d2 = gcptn[(j+len(gcptn)-1)%len(gcptn)][1]
						break
				else:
					assert False, "Failed to find our edge in node"
				i, d = i2, d2
			seqs.append(seq)
	return seqs

# clear present Groups (FC folders).  (Doesn't work reliably)
clw = getemptyobject(doc, "App::DocumentObjectGroup", "CutlineWires")

gcptsets, gcptnmap = extractcoincidentnodes(cutlinesketch)
gcptorders = [ coincidentnodetanges(cutlinesketch, gcptset)  for gcptset in gcptsets ]
seqs = extractsequences(gcptorders, gcptnmap)

for n, seq in enumerate(seqs):
	print(n, seq)
	points = [ ]
	for i, d in seq:
		l = cutlinesketch.Geometry[i]
		params = numpy.linspace(l.FirstParameter, l.LastParameter, 20)
		if d == 2:
			params = list(reversed(params))
		for a in params:
			points.append(l.value(a))
	ws = createobjectingroup(doc, clw, "Part::Feature", "wireP_%d"%(n+1))
	ws.Shape = Part.makePolygon(points)
