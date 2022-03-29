# -*- coding: utf-8 -*-

# This macro is for generating a set of PatchUVPolygons (polygons in UV space)
# derived from the cutlinesketch diagram, which are to be used as the basis of 
# the flattening, offsetting and trimming 

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

def sequencetopoints(cutlinesketch, seq, legsampleleng):
	points = [ ]
	for i, d in seq:
		l = cutlinesketch.Geometry[i]
		num = int(math.ceil(l.length()/legsampleleng) + 1)
		params = numpy.linspace(l.FirstParameter, l.LastParameter, num)
		if d == 2:
			params = list(reversed(params))
		for a in params[:-1]:
			points.append(l.value(a))
	return points
	
def orientationclockwise(points):
	jbl, ptbl = min(enumerate(points), key=lambda X:(X[1].y, X[1].x))
	jblp1 = (jbl+1)%len(points)
	jblp2 = (jbl+2)%len(points)
	jblm1 = (jbl+len(points)-1)%len(points)
	jblm2 = (jbl+len(points)-2)%len(points)
	ptblFore = points[jblp1]
	ptblBack = points[jblm1]
	vFore = ptblFore - ptbl
	vBack = ptblBack - ptbl
	#print (ptblBack, ptbl, ptblFore, jbl, jblp1, jblm1, points[jblp2], points[jblm2])
	return (math.atan2(vFore.x, vFore.y) < math.atan2(vBack.x, vBack.y))


patchnamelookups = {   
	'US1':(0.851, 0.865),
	'US2':(3.907, 0.864),
	'LEI1':(0.207, 0.106),
	'LEI2':(0.622, 0.106),
	'LEI3':(1.045, 0.106),
	'LEI4':(1.481, 0.106),
	'LEI5':(2.158, 0.106),
	'LEI6':(3.484, 0.106),
	'LEI7':(4.734, 0.106),
	'LEI8':(5.612, 0.106),
	'TSF1':(0.851, -0.294),
	'TSF2':(3.907, -0.294),
	'TSM1':(0.415, -0.913),
	'TSM2':(1.266, -0.913),
	'TSM3':(3.394, -0.827),
	'TSR':(4.082, -1.073) }
def getnameofpolygon(points):
	avgpt = sum(points, Vector())*(1.0/len(points))
	closestname = min(((avgpt - Vector(p[0]*1000, p[1]*1000)).Length, name)  for name, p in patchnamelookups.items())[1]
	return closestname

# clear present Groups (FC folders).  (Doesn't work reliably)
clw = getemptyobject(doc, "App::DocumentObjectGroup", "PatchUVPolygons")

# find the sets of nodes from the coincident constraints
gcptsets, gcptnmap = extractcoincidentnodes(cutlinesketch)
gcptorders = [ coincidentnodetanges(cutlinesketch, gcptset)  for gcptset in gcptsets ]

# derive the sequences of (edge, startend) for each contour
seqs = extractsequences(gcptorders, gcptnmap)

for n, seq in enumerate(seqs):
	points = sequencetopoints(cutlinesketch, seq, legsampleleng=3.0)
	if not orientationclockwise(points):
		closestname = getnameofpolygon(points)
		ws = createobjectingroup(doc, clw, "Part::Feature", "%s_%d"%(closestname, n))
		ws.Shape = Part.makePolygon(points+[points[0]])
