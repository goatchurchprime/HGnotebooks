import re, json, numpy, math
from basicgeo import P2, P3

try:
    import pygmsh
except ImportError:
    print("No pygmsh")


def loadwingtrimlinesDeprecated(fname):
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



class ParamPolyGraph:
    def __init__(self, wingshape, trimfile, deprecatedTrimFile=False):
        self.legsampleleng = 0.05
        self.splineweight = 0.21
        self.wingshape = wingshape
        if deprecatedTrimFile:
            snodes, self.paths = loadwingtrimlinesDeprecated(trimfile)
            self.nodes = dict((n, self.wingshape.sevalconvO(p))  for n, p in snodes.items())  
        else:
            jdata = json.load(open(trimfile))
            self.nodes = dict((nn, P2(*p))  for nn, p in jdata["nodes"].items())
            self.paths = jdata["paths"]
        self.Inodemax = max(int(re.sub("[^\d]", "", nn) or "0")  for nn in self.nodes)
    def saveas(self, trimfile):
        json.dump({"nodes":self.nodes, "paths":self.paths}, open(trimfile, "w"))
        
    def closestnodedist(self, mp):
        return min(((mp - p).Len(), nn)  for nn, p in self.nodes.items())
    def pointsdata(self):
        return zip(*self.nodes.values())
    def legsdata(self):
        return [[self.nodes[self.paths[i]], self.nodes[self.paths[i+1]]]  for i in range(0, len(self.paths), 2)]
    def commitlineedit(self, n1, n2):
        for i in range(0, len(self.paths), 2):
            if (n1 == self.paths[i] and n2 == self.paths[i+1]) or (n1 == self.paths[i+1] and n2 == self.paths[i]):
                del self.paths[i:i+2]
                return
        self.paths.extend([n1, n2])
    def delnode(self, n1):
        for i in range(0, len(self.paths), 2):
            while i < len(self.paths) and (n1 == self.paths[i] or n1 == self.paths[i+1]):
                del self.paths[i:i+2]
        del self.nodes[n1]
    def newnode(self, n1, mp):
        n2 = None
        while n2 is None or n2 in self.nodes:
            self.Inodemax += 1
            n2 = "i%d" % self.Inodemax
        self.nodes[n2] = mp
        self.paths.extend([n1, n2])
        return n2
        
    def tangentvec(self, n1, n2):
        vn = P2.ZNorm(self.nodes[n2] - self.nodes[n1])
        if len(self.neighbournodes[n1]) == 2 and not self.wingshape.uvonboundary(self.nodes[n1]):
            i = self.neighbournodes[n1].index(n2)
            nb = self.neighbournodes[n1][1-i]
            vb = P2.ZNorm(self.nodes[n1] - self.nodes[nb])
            vn = P2.ZNorm(vn + vb)
        return vn

    def splinemidnodesitem(self, n0, n1):
        p0 = self.nodes[n0]
        p1 = self.nodes[n1]
        sleg = [ ]
        m0 = self.tangentvec(n0, n1)*self.splineweight
        m1 = -self.tangentvec(n1, n0)*self.splineweight
        N = max(1, int((p0 - p1).Len()/self.legsampleleng + 0.75))
        for i in range(1, N):
            t = i*1.0/N
            t2 = t*t
            t3 = t2*t
            p = p0*(2*t3 - 3*t2 +1) + m0*(t3 - 2*t2 + t) + p1*(-2*t3 + 3*t2) + m1*(t3 - t2)
            sleg.append(p)
        return ((n0, n1), sleg)

    def makeallsplinemidnodes(self):
        self.neighbournodes = dict((nn, [])  for nn in self.nodes)
        for i in range(0, len(self.paths), 2):
            self.neighbournodes[self.paths[i]].append(self.paths[i+1])
            self.neighbournodes[self.paths[i+1]].append(self.paths[i])
        self.splinemidnodes = dict(self.splinemidnodesitem(self.paths[i], self.paths[i+1])  for i in range(0, len(self.paths), 2))
    def getsplinemidnodes(self, n0, n1):
        return self.splinemidnodes[(n0, n1)] if (n0, n1) in self.splinemidnodes  else reversed(self.splinemidnodes[(n1, n0)])
    def splineinterpseqq(self, n0, n1):
        p0 = self.nodes[n0]
        p1 = self.nodes[n1]
        sleg = [ p0 ]
        sleg.extend(self.getsplinemidnodes(n0, n1))
        sleg.append(p1)
        return sleg
    
    def splineinterplegsdata(self):
        self.makeallsplinemidnodes()
        self.neighbournodes = dict((nn, [])  for nn in self.nodes)
        for i in range(0, len(self.paths), 2):
            self.neighbournodes[self.paths[i]].append(self.paths[i+1])
            self.neighbournodes[self.paths[i+1]].append(self.paths[i])
        return [ self.splineinterpseqq(self.paths[i], self.paths[i+1])  for i in range(0, len(self.paths), 2) ]

    def isinnerpoly(self, poly, nodepoints):
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
    
    def derivepolygons(self):
        nodepoints = self.nodes
        onepathpairs = self.paths
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

            if not self.isinnerpoly(poly, nodepoints):
                if outerpoly != None:
                    print(" *** extra outer poly ", outerpoly, poly)
                    polys.append(outerpoly) 
                outerpoly = poly
            else:
                polys.append(poly)
        return polys

    def splinedpolypoints(self, polynodes):
        polyloop = [ ]
        for i in range(len(polynodes)):
            n0 = polynodes[i]
            n1 = polynodes[(i+1) % len(polynodes)]
            polyloop.append(self.nodes[n0])
            polyloop.extend(self.getsplinemidnodes(n0, n1))
        return polyloop

    
    def surfacemesheslist(self, polysnodes, mesh_size):
        surfacemeshes = [ ]
        for polynodes in polysnodes:
            polyloop = self.splinedpolypoints(polynodes)
            with pygmsh.geo.Geometry() as g:
                g.add_polygon(polyloop, mesh_size=mesh_size)
                mesh = g.generate_mesh()
            pts = numpy.array([ self.wingshape.seval(p)  for p in mesh.points ])
            surfacemesh = { "polynodes":polynodes, 
                            "polyloop":polyloop,
                            "uvpts":mesh.points, 
                            "pts":numpy.array(pts),
                            "tris":mesh.cells_dict["triangle"]
                          }
            surfacemeshes.append(surfacemesh)
        return surfacemeshes
    
    
import subprocess, json, os

def trimeshesflattener(surfacemeshes, freecadappimage):
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
    fnodes = (1.0/scaleupunits)*numpy.array(flattener.ze_nodes)
    print("mesh (pts=%%d, tris=%%d) flattened" %% (len(pts), len(tris)))
    flatmeshespts.append(fnodes.tolist())

json.dump(flatmeshespts, open(flatmeshfile, "w"))
""" % (surfacemeshfile, flatmeshfile)

    a = subprocess.run([freecadappimage, "-c"], input=fccode.encode(), capture_output=True)
    print(a.stderr.decode())
    print(a.stdout.decode())
    flatmeshes = json.load(open(flatmeshfile))
    for i, flatmesh in enumerate(flatmeshes):
        surfacemeshes[i]["fpts"] = numpy.array(flatmesh)


