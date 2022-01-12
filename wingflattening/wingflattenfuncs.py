#
# 2D and 3D point classes for easier lerp functions
#

from collections import namedtuple
import math, numpy

class P2(namedtuple('P2', ['u', 'v'])):
    __slots__ = ()
    def __new__(self, u, v):
        return super(P2, self).__new__(self, float(u), float(v))
    def __repr__(self):
        return "P2(%s, %s)" % (self.u, self.v)
    def __add__(self, a):
        return P2(self.u + a.u, self.v + a.v)
    def __sub__(self, a):
        return P2(self.u - a.u, self.v - a.v)
    def __mul__(self, a):
        return P2(self.u*a, self.v*a)
    def __neg__(self):
        return P2(-self.u, -self.v)
    def __rmul__(self, a):
        raise TypeError("Please use left multiplication")
    def Lensq(self):
        return self.u*self.u + self.v*self.v
    def Len(self):
        if self.u == 0.0:  return abs(self.v)
        if self.v == 0.0:  return abs(self.u)
        return math.sqrt(self.u*self.u + self.v*self.v)
    def LenLZ(self):
        return math.sqrt(self.x*self.x + self.y*self.y)
    def Arg(self):
        return math.degrees(math.atan2(self.v, self.u))
        
        
    def assertlen1(self):
        assert abs(self.Len() - 1.0) < 0.0001
        return True
        
    @staticmethod
    def Dot(a, b):
        return a.u*b.u + a.v*b.v
    @staticmethod
    def DotLZ(a, b):
        return a.u*b.x + a.v*b.y

    @staticmethod
    def ZNorm(v):
        ln = v.Len()
        if ln == 0.0:  
            ln = 1.0
        return P2(v.u/ln, v.v/ln)
            
    @staticmethod
    def APerp(v):
        return P2(-v.v, v.u)
    @staticmethod
    def CPerp(v):
        return P2(v.v, -v.u)

    @staticmethod
    def ConvertLZ(p):  
        return P2(p.x, p.y)

    

class P3(namedtuple('P3', ['x', 'y', 'z'])):
    __slots__ = ()
    def __new__(self, x, y, z):
        return super(P3, self).__new__(self, float(x), float(y), float(z))
    def __repr__(self):
        return "P3(%s, %s, %s)" % (self.x, self.y, self.z)
    def __add__(self, a):
        return P3(self.x + a.x, self.y + a.y, self.z + a.z)
    def __sub__(self, a):
        return P3(self.x - a.x, self.y - a.y, self.z - a.z)
    def __mul__(self, a):
        return P3(self.x*a, self.y*a, self.z*a)
    def __neg__(self):
        return P3(-self.x, -self.y, -self.z)
    def __rmul__(self, a):
        raise TypeError
    def Lensq(self):
        return self.x*self.x + self.y*self.y + self.z*self.z
    def Len(self):
        return math.sqrt(self.Lensq())
    def LenLZ(self):
        return math.sqrt(self.x*self.x + self.y*self.y)
        
        
    def assertlen1(self):
        assert abs(self.Len() - 1.0) < 0.0001
        return True
        
    @staticmethod
    def Dot(a, b):
        return a.x*b.x + a.y*b.y + a.z*b.z

    @staticmethod
    def Cross(a, b):
        return P3(a.y*b.z - b.y*a.z, -a.x*b.z + b.x*a.z, a.x*b.y - b.x*a.y)

    @staticmethod
    def Diff(a, b, bfore):
        if bfore:  return b - a
        return a - b
        
    @staticmethod
    def ZNorm(v):
        ln = v.Len()
        if ln == 0.0:  
            ln = 1.0
        return P3(v.x/ln, v.y/ln, v.z/ln)
            
    @staticmethod
    def ConvertGZ(p, z):  
        return P3(p.u, p.v, z)
    @staticmethod
    def ConvertCZ(p, z):  
        return P3(p.x, p.y, z)

    
#
# Load the parametric trim lines
#
import json
def loadwingtrimlines(fname):
    lnodes, paths = json.load(open(fname))
    nodes = { }
    for k, v in lnodes.items():
        v = eval(v)
        p = P2(max(0, min(1, v[0]/4)), max(0, min(1, v[1]/4)))
        nodes[k] = p
    cr0 = max((k  for k in nodes  if nodes[k][1] <= 0), key=lambda x:nodes[x][0])
    cr1 = min((k  for k in nodes  if nodes[k][0] >= 1), key=lambda x:nodes[x][1])
    nodes["c4"] = P2(1,0)
    paths.extend([cr0, "c4", "c4", cr1])  
    return nodes, paths




#
# Convert parametric trim lines into polygons
#
def isinnerpoly(poly, nodepoints):
    jbl = 0
    ptbl = nodepoints[poly[jbl]]
    for j in range(1, len(poly)):
        pt = nodepoints[poly[j]]
        if pt.v < ptbl.v or (pt.v == ptbl.v and pt.u < ptbl.u):
            jbl = j
            ptbl = pt
    ptblFore = nodepoints[poly[(jbl+1)%len(poly)]]
    ptblBack = nodepoints[poly[(jbl+len(poly)-1)%len(poly)]]
    angFore = P2(ptblFore.u-ptbl.u, ptblFore.v-ptbl.v).Arg()
    angBack = P2(ptblBack.u-ptbl.u, ptblBack.v-ptbl.v).Arg()
    return (angBack < angFore)


def trimlinestopolygons(nodes, paths):
    nodepoints = nodes
    onepathpairs = paths
    Lpathvectorseq = { } 
    for i in nodepoints.keys():
        Lpathvectorseq[i] = [ ]  # [ (arg, pathindex) ]
    Npaths = int(len(onepathpairs)/2)
    opvisits2 = [ ]
    for i in range(Npaths):
        i0 = onepathpairs[i*2]
        i1 = onepathpairs[i*2+1]
        if i0 != i1:
            vec = nodepoints[i1] - nodepoints[i0]
            Lpathvectorseq[i0].append([vec.Arg(), i])
            Lpathvectorseq[i1].append([(-vec).Arg(), i])
            opvisits2.append(0)
            opvisits2.append(0)
        else:
            print("Suppressing loop edge in onepathpairs (how did it get here?) polynet function would fail as it relies on orientation")
            opvisits2.append(-1)
            opvisits2.append(-1)

    for pathvectorseq in Lpathvectorseq.values():
        pathvectorseq.sort()

    polys = [ ]
    linearpaths = [ ]
    outerpoly = None
    assert (len(opvisits2) == len(onepathpairs))
    for i in range(len(opvisits2)):
        if opvisits2[i] != 0:
            continue
        ne = int(i/2)
        np = onepathpairs[ne*2 + (0 if ((i%2)==0) else 1)]
        poly = [ ]
        singlenodeindexes = [ ]
        hasnondoublenodes = False
        while (opvisits2[ne*2 + (0 if onepathpairs[ne*2] == np else 1)]) == 0:
            opvisits2[ne*2 + (0 if onepathpairs[ne*2] == np else 1)] = len(polys)+1
            poly.append(np)
            np = onepathpairs[ne*2 + (1  if onepathpairs[ne*2] == np  else 0)]
            if len(Lpathvectorseq[np]) == 1:
                singlenodeindexes.append(len(poly))
            elif len(Lpathvectorseq[np]) != 2:
                hasnondoublenodes = True
            for j in range(len(Lpathvectorseq[np])):
                if Lpathvectorseq[np][j][1] == ne:
                    ne = Lpathvectorseq[np][(j+1)%len(Lpathvectorseq[np])][1]
                    break

        # find and record the orientation of the polygon by looking at the bottom left
        if len(poly) == 0:
            print("bad poly size 0")
            continue

        if not isinnerpoly(poly, nodepoints):
            if outerpoly != None:
                print(" *** extra outer poly ", outerpoly, poly)
                polys.append(outerpoly) 
            outerpoly = poly
        else:
            polys.append(poly)
    return polys



#
# Wing geometry: maps uv in [0,1],[0,1] -> XYZ points on wing surface
#
import csv

def loadwinggeometry(fname, fac=1.0):
    r = csv.reader(open(fname))
    k = list(r)
    wingmeshuvudivisions = eval(k[0][-3])
    assert (wingmeshuvudivisions ==len(k[0])/3-1), 'Section numbering incorrect'

    sections = []
    zvals = []
    for i in range(0, (wingmeshuvudivisions*3)+2, 3):
        pts = [ ]
        z = float(k[2][i+1])
        for j in range(2, 70):
            assert (z == float(k[j][i+1]))
            pts.append(P2(float(k[j][i]), float(k[j][i+2]))*fac)
        zvals.append(z*fac)
        sections.append(pts)
    assert(len(sections) == wingmeshuvudivisions+1)
    return sections, zvals

def wingwireframe(sections, zvals):
    wingmeshuvvdivisions = len(sections[0])
    X = numpy.array([[p[0]  for p in pts]  for pts in sections])
    Y = numpy.array([[p[1]  for p in pts]  for pts in sections])
    Z = numpy.array([[z  for i in range(wingmeshuvvdivisions)]  for z in zvals])
    return X, Y, Z

def winguv2xyz(uvx, uvy, sections, zvals):
    wingmeshuvudivisions = len(sections)-1
    #print(wingmeshuvudivisions)
    wingmeshuvvdivisions = len(sections[0])
    #print(wingmeshuvvdivisions)
    usecl = uvx*wingmeshuvudivisions
    usec = int(max(0, min(wingmeshuvudivisions-1, math.floor(usecl))))
    ropepointlamda = usecl - usec
    aroundsegmentl = uvy*wingmeshuvvdivisions-1
    aroundsegment = int(max(0, min(wingmeshuvvdivisions-2, math.floor(aroundsegmentl))))
    lambdaCalong = aroundsegmentl - aroundsegment
    p00 = sections[usec][aroundsegment]
    p01 = sections[usec][aroundsegment+1]
    p10 = sections[usec+1][aroundsegment]
    p11 = sections[usec+1][aroundsegment+1]
    z = zvals[usec]*(1-ropepointlamda) + zvals[usec+1]*ropepointlamda
    p0 = p00*(1-ropepointlamda) + p10*ropepointlamda
    p1 = p01*(1-ropepointlamda) + p11*ropepointlamda
    p = p0*(1-lambdaCalong) + p1*lambdaCalong
    return P3(p[0], p[1], z)



#
# The batch surface flattener from FreeCAD
#
import sys, numpy, json, os, shutil, subprocess

freecadappimage = "/home/timbo/software/FreeCAD_0.19-24054-Linux-Conda_glibc2.12-x86_64.AppImage"
# fetch from: wget https://github.com/FreeCAD/FreeCAD/releases/download/0.19_pre/FreeCAD_0.19-24267-Linux-Conda_glibc2.12-x86_64.AppImage

def trimeshesflattener(surfacemeshes):
    surfacemeshfile = "surfacemeshfile.json"
    flatmeshfile = "flattenedmesh.json"

    if os.path.exists(flatmeshfile):
        os.remove(flatmeshfile)

    jsurfacemeshes = [ { "pts":surfacemesh["pts"].tolist(), "tris":surfacemesh["tris"].tolist() }\
                          for surfacemesh in surfacemeshes ]
    json.dump(jsurfacemeshes, open(surfacemeshfile, "w"))


    fccode = """import flatmesh
import sys, numpy, json, os

surfacemeshfile = "%s"
flatmeshfile = "%s"
scaleupunits = 1024.0

surfacemeshes = json.load(open(surfacemeshfile))
flatmeshespts = [ ]
for surfacemesh in surfacemeshes:
    pts = scaleupunits*numpy.array(surfacemesh["pts"])
    tris = numpy.array(surfacemesh["tris"])
    flattener = flatmesh.FaceUnwrapper(pts, tris)
    flattener.findFlatNodes(10, 0.95)
    fnodes = (1/scaleupunits)*flattener.ze_nodes
    print("mesh (pts=%%d, tris=%%d) flattened" %% (len(pts), len(tris)))
    flatmeshespts.append(fnodes.tolist())

json.dump(flatmeshespts, open(flatmeshfile, "w"))

""" % (surfacemeshfile, flatmeshfile)

    a = subprocess.run([freecadappimage, "-c"], input=fccode.encode(), capture_output=True)
    #print(a.stderr.decode())
    print(a.stdout.decode())

    flatmeshes = json.load(open(flatmeshfile))
    return flatmeshes


#
# All in one batch poly triangulation, projection and flattener
#
try:
    import pygmsh
except ImportError as e:
    print("No pygmsh here")

def triprojpolyflattener(nodes, polys, sections, zvals, mesh_size):
    surfacemeshes = [ ]
    for poly in polys:
        npoly = [ [nodes[p][0], nodes[p][1]]  for p in poly ]
        with pygmsh.geo.Geometry() as g:
            g.add_polygon(npoly, mesh_size=mesh_size)
            mesh = g.generate_mesh()

        pts = [ winguv2xyz(p[0], p[1], sections, zvals)  for p in mesh.points ]
        tris = mesh.cells_dict["triangle"]
        surfacemeshes.append({"pts":numpy.array(pts), "tris":tris })
    flatmeshes = trimeshesflattener(surfacemeshes)
    for i, flatmesh in enumerate(flatmeshes):
        surfacemeshes[i]["fpts"] = numpy.array(flatmesh)
    return surfacemeshes


def fullflattriareas(surfacemesh):
    ptsP = [ P3(*p)  for p in surfacemesh["pts"] ]
    fptsP = [ P2(*p)  for p in surfacemesh["fpts"] ]
    tris = surfacemesh["tris"]

    def P2Cross(a, b):
        return a.u*b.v - b.u*a.v

    triareas = [ ]
    for tri in tris:
        p0, p1, p2 = ptsP[tri[0]], ptsP[tri[1]], ptsP[tri[2]]
        parea = 0.5*P3.Cross(p1 - p0, p2 - p0).Len()
        f0, f1, f2 = fptsP[tri[0]], fptsP[tri[1]], fptsP[tri[2]]
        farea = 0.5*abs(P2Cross(f1 - f0, f2 - f0))
        #areachange = farea/parea
        triareas.append([parea, farea])
    return numpy.array(triareas)



class WingShape:
    def __init__(self, fname):
        self.Isect = 7  # Fix the section all rectangle unwrapping is relative to
        self.sections, self.zvals = loadwinggeometry(fname, 0.001)
        self.nsections = len(self.zvals)
        assert self.nsections == len(self.sections)
        self.nchorddivs = len(self.sections[0])
        assert self.nchorddivs == len(self.sections[-1])
        self.sectionchordlengths = [ ]
        self.sectionchordranges = [ ]
        for section in self.sections:
            chordlengths = [ 0 ]
            for p0, p1 in zip(section, section[1:]):
                chordlengths.append(chordlengths[-1] + (p0-p1).Len())
            self.sectionchordlengths.append(chordlengths)
            self.sectionchordranges.append((-chordlengths[-1]*0.5, chordlengths[-1]*0.5))
        self.leadingedgelengths = [ 0 ]
        for i in range(1, self.nsections):
            p0 = P3.ConvertGZ(self.sectionchordeval(i-1, 0), self.zvals[i-1])
            p1 = P3.ConvertGZ(self.sectionchordeval(i, 0), self.zvals[i])
            self.leadingedgelengths.append(self.leadingedgelengths[-1] + (p0-p1).Len())
        self.urange = (self.leadingedgelengths[0], self.leadingedgelengths[-1])
        self.vrange = self.sectionchordranges[self.Isect]
        
    def sectionchordlengthconv(self, i, s):
        chordlengths = self.sectionchordlengths[i]
        ls = s - self.sectionchordranges[i][0]
        j0, j1 = 0, len(chordlengths)-1
        while j1 - j0 >= 2:
            j = (j1 + j0)//2
            if ls <= chordlengths[j]:
                j1 = j
            else:
                j0 = j
        return j0 + (ls-chordlengths[j0])/(chordlengths[j1]-chordlengths[j0])
        
    def sectionchordevalI(self, i, u):
        j = max(0, min(self.nchorddivs-2, int(u)))
        l = u - j
        p0 = self.sections[i][j]
        p1 = self.sections[i][j+1]
        return p0*(1-l) + p1*l

    def sectionchordeval(self, i, s):
        return self.sectionchordevalI(i, self.sectionchordlengthconv(self.Isect, s))

    def leadingedgelengthconv(self, t):
        j0, j1 = 0, len(self.leadingedgelengths)-1
        while j1 - j0 >= 2:
            j = (j1 + j0)//2
            if t <= self.leadingedgelengths[j]:
                j1 = j
            else:
                j0 = j
        return j0 + (t-self.leadingedgelengths[j0])/(self.leadingedgelengths[j1]-self.leadingedgelengths[j0])

    def sevalconv(self, p):
        return P2(self.sectionchordlengthconv(self.Isect, p[0]), self.leadingedgelengthconv(p[1]))

    def sevalI(self, p):
        i = max(0, min(self.nsections-2, int(p[1])))
        m = p[1] - i
        p0 = P3.ConvertGZ(self.sectionchordevalI(i, p[0]), self.zvals[i])
        p1 = P3.ConvertGZ(self.sectionchordevalI(i+1, p[0]), self.zvals[i+1])
        return p0*(1-m) + p1*m
        
    def seval(self, p):
        return self.sevalI(self.sevalconv(p))

    def sevalconvO(self, p):
        uniformchordlength = self.sectionchordlengths[self.Isect]
        vsecl = p.v*(self.nchorddivs-1)
        vsec = max(0, min(self.nchorddivs-2, int(math.floor(vsecl))))
        vr = vsecl - vsec
        v = uniformchordlength[vsec]*(1-vr) + uniformchordlength[vsec+1]*vr
        
        usecl = p.u*(self.nsections-1)
        usec = max(0, min(self.nsections-2, int(math.floor(usecl))))
        ur = usecl - usec
        u = self.leadingedgelengths[usec]*(1-ur) + self.leadingedgelengths[usec+1]*ur
        return P2(u, v+self.sectionchordranges[self.Isect][0])

    def clampuv(self, p):
        return P2(max(self.urange[0], min(self.urange[1], p.u)), 
                  max(self.vrange[0], min(self.vrange[1], p.v)))
    def uvonboundary(self, p):
        return p.u == self.urange[0] or p.u == self.urange[1] or p.v == self.vrange[0] or p.v == self.vrange[1]


def exportpolygonsobj(filepath, nodes, paths, wingshape, mesh_size):    
    polys = trimlinestopolygons(nodes, paths)
    f = open(filepath, 'w')
    f.write("# OBJ file\n")
    joff = 1
    for i, poly in enumerate(polys):
        npoly = [ [nodes[p][0], nodes[p][1]]  for p in poly ]
        with pygmsh.geo.Geometry() as g:
            g.add_polygon(npoly, mesh_size=mesh_size)
            mesh = g.generate_mesh()
            pts = numpy.array([wingshape.seval(p)  for p in mesh.points])
            f.write("o patch%d\n" % (10+i))
            for v in pts:
                f.write("v %.4f %.4f %.4f\n" % tuple(v))
            for t in mesh.cells_dict["triangle"]:
                f.write("f %d %d %d\n" % (t[0]+joff,t[1]+joff,t[2]+joff))
            joff += len(pts)
    f.close()

