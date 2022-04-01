import sys
print(sys.path[-1])

from p7modules.barmesh.basicgeo import P2, P3, Partition1, Along
from p7modules.barmesh import barmesh
from p7modules.barmesh.barmesh import Bar
import numpy

class WNode:
    def __init__(self, p, sp, i):
        self.p = p
        self.sp = sp
        self.i = i
        self.pointzone = None
        
    def newnodetowardsothernode(self, nodefore, lam, i):
        return self.__class__(Along(lam, self.p, nodefore.p), Along(lam, self.sp, nodefore.sp), i)
        
    def pairusedfornesting(self):
        return (self.sp[0], self.sp[1])
    
    def strictlyplanarbarmesh(self):
        return False
    
    def cperpbardot(self, bar, v):
        assert False
        
    def cperpbardotN(self, bar, v):
        assert False

def MakeRectBarmeshForWingParametrization(seval, xpart, ypart):
    bm = barmesh.BarMesh()
    nxs = xpart.nparts + 1

    nodes = bm.nodes
    xbars = [ ]  # multiple of nxs
    ybars = [ ]  # multiple of nxs-1
    for y in ypart.vs:
        bfirstrow = (len(nodes) == 0)
        for i in range(nxs):
            sp = P2(xpart.vs[i], y)
            nnode = bm.AddNode(WNode(seval(sp[0], sp[1]), sp, -1))
            assert nnode == nodes[-1]
            if not bfirstrow:
                xbars.append(Bar(nodes[-nxs - 1], nodes[-1]))
                bm.bars.append(xbars[-1])
                if i != 0:
                    xbars[-1].barbackleft = ybars[1-nxs]
                    ybars[1-nxs].barbackleft = xbars[-2]
            if i != 0:
                ybars.append(Bar(nodes[-2], nodes[-1]))
                bm.bars.append(ybars[-1])
                if not bfirstrow:
                    ybars[-1].barforeright = xbars[-1]
                    xbars[-2].barforeright = ybars[-1]
    assert len(bm.bars) == len(xbars)+len(ybars)
    return bm




from p7modules.barmesh.implicitareaballoffset import DistPZ, DistLamPZ
from p7modules.barmesh.tribarmes import TriangleBarMesh, TriangleBar, MakeTriangleBoxing
from p7modules.barmesh.basicgeo import I1, Partition1, P3, P2, Along

class ImplicitAreaBallOffsetOfClosedContour:
    def __init__(self, polyloopW, polyloop, bloopclosed=True, boxwidth=-1):
        assert len(polyloopW) == len(polyloop)
        # polyloop is in UV space, polyloopW is the 3D space projections
        tbm = TriangleBarMesh()
        tbmF = TriangleBarMesh()
        polyloopN = [ tbm.NewNode(p)  for p in polyloopW ]
        polyloopFN = [ tbmF.NewNode(P3.ConvertGZ(p, 0.0))  for p in polyloop ]
        self.bloopclosed = bloopclosed
        for i in range(len(polyloop)-1):
            tbm.bars.append(TriangleBar(polyloopN[i], polyloopN[i+1]))
            tbmF.bars.append(TriangleBar(polyloopFN[i], polyloopFN[i+1]))
        if bloopclosed:
            tbm.bars.append(TriangleBar(polyloopN[0], polyloopN[-1]))
            tbmF.bars.append(TriangleBar(polyloopFN[0], polyloopFN[-1]))
        
        self.tbarmesh = tbm
        self.tbarmeshF = tbmF
        self.tboxing = MakeTriangleBoxing(self.tbarmesh, boxwidth)
        self.tboxingF = MakeTriangleBoxing(self.tbarmeshF, boxwidth)
        self.hitreg = [0]*len(self.tbarmesh.bars)
        self.nhitreg = 0

    def Isb2dcontournormals(self):
        return False

    def IsToRightRay(self, sp, p0, p1):
        if (p0.y < sp.v) != (p1.y < sp.v):
            mu = (p1.y - sp.v)/(p1.y - sp.v)
            ucut = Along(mu, p0.x, p1.x)
            if ucut > sp.u:
                return 1
        return 0
    
    def InsidePF(self, sp):
        uplusraycuts = 0
        self.nhitreg += 1
        for ix, iy in self.tboxingF.CloseBoxeGenerator(sp.u, self.tboxingF.xpart.hi, sp.v, sp.v, 0.01):
            tbox = self.tboxingF.boxes[ix][iy]
            for i in tbox.edgeis:
                if self.hitreg[i] != self.nhitreg:
                    p0, p1 = self.tboxingF.GetBarPoints(i)
                    uplusraycuts += self.IsToRightRay(sp, p0, p1)
                    self.hitreg[i] = self.nhitreg
        #assert (uplusraycuts == 0 or uplusraycuts == 1), uplusraycuts
        return (uplusraycuts%2) == 1
        assert 0
        
    def DistPN(self, pz, n):
        self.DistP(pz, n.p)
        if self.bloopclosed:
            if self.InsidePF(n.sp):
                pz.r = -pz.r
        
    def DistP(self, pz, p):
        dpz = DistPZ(p, pz.r)
        for ix, iy in self.tboxing.CloseBoxeGenerator(p.x, p.x, p.y, p.y, pz.r):
            tbox = self.tboxing.boxes[ix][iy]
            for i in tbox.pointis:
                dpz.DistPpointPZ(self.tboxing.GetNodePoint(i))
                
        self.nhitreg += 1
        for ix, iy in self.tboxing.CloseBoxeGenerator(p.x, p.x, p.y, p.y, pz.r):
            tbox = self.tboxing.boxes[ix][iy]
            for i in tbox.edgeis:
                if self.hitreg[i] != self.nhitreg:
                    dpz.DistPedgePZ(*self.tboxing.GetBarPoints(i))
                    self.hitreg[i] = self.nhitreg
                    
        pz.r = dpz.r
        pz.v = dpz.v
        
        
    def CutposN(self, nodefrom, nodeto, cp, r):  # point, vector, cp=known close point to narrow down the cutoff search
        p = nodefrom.p
        vp = nodeto.p - nodefrom.p
        dlpz = DistLamPZ(p, vp, r)  
        if cp is not None:
            dlpz.DistLamPpointPZ(cp)
            assert dlpz.lam != 2.0
        
        # solve |p0 + vp * lam - p| == r where Dist(p0) >= r >= Dist(p0 + vp)
        rexp = r + 0.01
        for ix, iy in self.tboxing.CloseBoxeGenerator(min(p.x, p.x+vp.x), max(p.x, p.x+vp.x), min(p.y, p.y+vp.y), max(p.y, p.y+vp.y), rexp):
            tbox = self.tboxing.boxes[ix][iy]
            for i in self.tboxing.SlicePointisZ(tbox.pointis, min(p.z,p.z+vp.z)-rexp, max(p.z,p.z+vp.z)+rexp):
            #for i in tbox.pointis:
                dlpz.DistLamPpointPZ(self.tboxing.GetNodePoint(i))
                
        self.nhitreg += 1
        for ix, iy in self.tboxing.CloseBoxeGenerator(min(p.x, p.x+vp.x*dlpz.lam), max(p.x, p.x+vp.x*dlpz.lam), min(p.y, p.y+vp.y*dlpz.lam), max(p.y, p.y+vp.y*dlpz.lam), r + 0.01):
            tbox = self.tboxing.boxes[ix][iy]
            for i in tbox.edgeis:
                if self.hitreg[i] != self.nhitreg:
                    dlpz.DistLamPedgePZ(*self.tboxing.GetBarPoints(i))
                    self.hitreg[i] = self.nhitreg
        
        if __debug__:
            if not (dlpz.lam == 0.0 or dlpz.lam == 2.0):
                pz = barmesh.PointZone(0, abs(r) + 1.1, None)
                self.DistP(pz, dlpz.p + dlpz.vp*dlpz.lam)
                assert abs(pz.r - r) < 0.002, ("cutposbad", pz.r, dlpz.lam, dlpz.p, dlpz.vp)
            
        return dlpz.lam


    
def findandnumberallnodesandbarcycles(bm):
    tnodes, tbarcycles = [ ], set()
    cizone = barmesh.PZ_BEYOND_R
    for node in bm.nodes:
        if not (node.pointzone.izone == cizone):
            node.i = len(tnodes)
            tnodes.append(node)
        else:
            node.i = -1
    for bar in bm.bars:
        if not bar.bbardeleted:
            if not (bar.nodeback.pointzone.izone == cizone):
                tbarcycles.add((bar, bar.nodeback))
            if not (bar.nodefore.pointzone.izone == cizone):
                tbarcycles.add((bar, bar.nodefore))
            if (bar.nodeback.pointzone.izone == cizone) != (bar.nodefore.pointzone.izone == cizone):
                bar.nodemid.i = len(tnodes)
                tnodes.append(bar.nodemid)
    return tnodes, tbarcycles

def findallnodesandpolys(bm):
    cizone = barmesh.PZ_BEYOND_R
    tnodes, tbarcycles = findandnumberallnodesandbarcycles(bm)
    cpolys = [ ]
    while len(tbarcycles):
        cbar, cnode = tbarcycles.pop()
        assert not (cnode.pointzone.izone == cizone)
        ccpoly = [ ]
        ccbar, ccnode = cbar, cnode
        while True:
            izoneP = ccnode.pointzone.izone
            ccnode = ccbar.GetNodeFore(ccbar.nodeback == ccnode)
            if (ccnode.pointzone.izone == cizone) != (izoneP == cizone):
                ccpoly.append(ccbar.nodemid.i)
            if not (ccnode.pointzone.izone == cizone):
                assert ccnode.i != -1
                ccpoly.append(ccnode.i)
            if ccnode == cnode:
                break
            ccbar = ccbar.GetForeRightBL(ccbar.nodefore == ccnode)
            if not (ccnode.pointzone.izone == cizone):
                tbarcycles.remove((ccbar, ccnode))
        cpolys.append(ccpoly)
    return tnodes, cpolys

def cpolytriangulate(ptsF, cpoly):
    if (n:=len(cpoly)) == 3:
        return [ cpoly ]
    assert n == len(cpoly)
    jp = max((min(P2.Dot((ptsF[cpoly[(j+i)%n]]-ptsF[cpoly[j]]), P2.APerp(ptsF[cpoly[(j+i+1)%n]]-ptsF[cpoly[j]]))  \
                 for i in range(1, n-1)), j)  for j in range(n))
    j = jp[1]
    return [ (cpoly[j], cpoly[(j+i)%n], cpoly[(j+i+1)%n])  for i in range(1, n-1) ]



def orientation(ptfs, polyi):
    jbl, ptbl = min(enumerate(ptfs[i]  for i in polyi), key=lambda X:(X[1][1], X[1][0]))
    ptblFore = ptfs[polyi[(jbl+1)%len(polyi)]]
    ptblBack = ptfs[polyi[(jbl+len(polyi)-1)%len(polyi)]]
    angFore = P2(ptblFore[0]-ptbl[0], ptblFore[1]-ptbl[1]).Arg()
    angBack = P2(ptblBack[0]-ptbl[0], ptblBack[1]-ptbl[1]).Arg()
    return (angBack < angFore)

def applyconsistenrotationtoflats(surfacemesh):
    ptsF = surfacemesh["fpts"]*(1,-1)   # reflect in Y using numpy.array multiplication
    offsetloopuv = surfacemesh["offsetloopuv"]
    offsetloopptsF = [ P2(ptsF[i][0], ptsF[i][1])  for i in surfacemesh["offsetloopI"] ]
    offsetloopuvCentre = sum(offsetloopuv, start=P2(0,0))*(1.0/len(offsetloopuv))
    offsetloopptsFCentre = sum(offsetloopptsF, start=P2(0,0))*(1.0/len(offsetloopptsF))
    voff = offsetloopuvCentre - offsetloopptsFCentre
    
    # this proves all the polygons are reflected
    orientOrg = orientation(surfacemesh["uvpts"], surfacemesh["offsetloopI"])
    orientReflFlatttened = orientation(ptsF, surfacemesh["offsetloopI"])
    assert orientOrg == orientReflFlatttened
    
    # try and rotate so we align with the first edge
    i0 = surfacemesh["offsetloopI"][-10]
    i1 = surfacemesh["offsetloopI"][-5]
    if surfacemesh["patchname"] == "US2":
        i0 = surfacemesh["offsetloopI"][10]
        i1 = surfacemesh["offsetloopI"][15]
    if surfacemesh["patchname"] == "TSR":
        i0 = surfacemesh["offsetloopI"][150]
        i1 = surfacemesh["offsetloopI"][155]

    #v = P2(*surfacemesh["uvpts"][i1]) - offsetloopuvCentre
    #vF = P2(*ptsF[i1]) - offsetloopptsFCentre
    v = P2(*surfacemesh["uvpts"][i1]) - P2(*surfacemesh["uvpts"][i0])
    vF = P2(*ptsF[i1]) - P2(*ptsF[i0])
    
    xv = P2.ZNorm(P2(P2.Dot(vF, v), P2.Dot(P2.APerp(vF), v)))
    yv = P2.APerp(xv)
    
    explodev = (offsetloopuvCentre - P2(3, 0))*0.8
    if surfacemesh["patchname"] == "TSM3":
        offsetloopuvCentre -= P2(1.0, -0.3)
    def transF(p):
        p0 = p - offsetloopptsFCentre
        return xv*p0[0] + yv*p0[1] + offsetloopuvCentre + explodev
    surfacemesh["fptsT"] = fptsT = numpy.array([ transF(p)  for p in ptsF ])
    vFT = P2(*surfacemesh["fptsT"][i1]) - P2(*surfacemesh["fptsT"][i0])
    #print(v.Arg(), vF.Arg(), vFT.Arg())
    surfacemesh["textpos"] = offsetloopuvCentre + explodev

def cpolyuvvectorstransF(uvpts, fptsT, cpoly):
    cpt = sum((P2(*uvpts[ci]) for ci in cpoly), P2(0,0))*(1.0/len(cpoly))
    cptT = sum((P2(*fptsT[ci]) for ci in cpoly), P2(0,0))*(1.0/len(cpoly))
    n = len(cpoly)
    jp = max((abs(P2.Dot((P2(*uvpts[cpoly[j]]) - cpt), P2.APerp(P2(*uvpts[cpoly[(j+1)%n]]) - cpt))), j)  for j in range(n))
    vj = P2(*uvpts[cpoly[jp[1]]]) - cpt
    vj1 = P2(*uvpts[cpoly[(jp[1]+1)%n]]) - cpt
    
    urvec = P2(vj1.v, -vj.v)
    urvec = urvec*(1.0/P2.Dot(urvec, P2(vj.u, vj1.u)))
    vrvec = P2(vj1.u, -vj.u)
    vrvec = vrvec*(1.0/P2.Dot(vrvec, P2(vj.v, vj1.v)))
    # this has gotten muddled.  Should be simpler since the following two are negative of each other
    # P2.Dot(urvec, P2(vj.u, vj1.u)) = vj1.v*vj.u - vj.v*vj1.u
    # P2.Dot(vrvec, P2(vj.v, vj1.v)) = vj1.u*vj.v - vj.u*vj1.v
    # set solve: (urvec.u*vj + urvec.v*vj1).v = 0, which is why it uses only v components 
    
    vjT = P2(*fptsT[cpoly[jp[1]]]) - cptT
    vj1T = P2(*fptsT[cpoly[(jp[1]+1)%n]]) - cptT
    
    # vc = p - cc["cpt"]
    #vcp = cc["urvec"]*vc.u + cc["vrvec"]*vc.v
    #vcs = cc["vj"]*vcp.u + cc["vj1"]*vcp.v ->  vc
    
    return { "cpt":cpt, "cptT":cptT, "urvec":urvec, "vrvec":vrvec, 
             "vj":vj, "vj1":vj1, "vjT":vjT, "vj1T":vj1T }


def generatecpolytransformfunction(surfacemesh):
    bm, xpart, ypart = surfacemesh["barmeshoffset"], surfacemesh["xpart"], surfacemesh["ypart"]
    uvpts = surfacemesh["uvpts"]
    fptsT = surfacemesh["fptsT"]
    cpolycolumns = [ [ ]  for ix in range(xpart.nparts) ]
    tnodes, cpolys = findallnodesandpolys(bm)
    for cpoly in cpolys:
        ccpoly = cpolyuvvectorstransF(uvpts, fptsT, cpoly)
        cpolycolumns[xpart.GetPart(ccpoly["cpt"].u)].append(ccpoly)
    surfacemesh["cpolycolumns"] = cpolycolumns

    
def sliceupatnones(seq):
    res = [ [ ] ]
    for s in seq:
        if s is None:
            if res[-1]:
                res.append([])
        else:
            res[-1].append(s)
    if not res[-1]:
        res.pop()
    return res


def projectspbarmeshF(sp, xpart, cpolycolumns, uspacing, vspacing, bFlattenedPatches=True):
    if not (xpart.lo < sp[0] < xpart.hi):
        return None
    ix = xpart.GetPart(sp[0])
    if len(cpolycolumns[ix]) == 0:
        return None
    cc = min((cc  for cc in cpolycolumns[ix]), key=lambda X: (X["cpt"] - sp).Len())
    if abs(cc["cpt"][0] - sp.u) > uspacing or abs(cc["cpt"][1] - sp.v) > vspacing:
        return None
    vc = sp - cc["cpt"]
    vcp = cc["urvec"]*vc.u + cc["vrvec"]*vc.v
    vcs = cc["vj"]*vcp.u + cc["vj1"]*vcp.v # should be same as vc
    vcsT = cc["vjT"]*vcp.u + cc["vj1T"]*vcp.v
    if bFlattenedPatches:
        return vcsT + cc["cptT"]
    return vcs + cc["cpt"]
    nn = nodesixyShift(ix, iy)

    
def subloopsequence(polynodesloop, polynodesset):
    polynodesseqs = [ [ ] ]
    for i in range(len(polynodesloop)):
        if polynodesloop[i] in polynodesset:
            polynodesseqs[-1].append(polynodesloop[i])
        elif polynodesseqs[-1]:
            polynodesseqs.append([])
    if polynodesseqs[-1]:
        if polynodesseqs[0][0] == polynodesloop[0] and polynodesseqs[-1][-1] == polynodesloop[-1]:
            if len(polynodesseqs) == 1:
                polynodesseqs[0].append(polynodesseqs[0][0])
            else:
                polynodesseqs[0] = polynodesseqs.pop() + polynodesseqs[0]
    else:
        polynodesseqs.pop()
    return polynodesseqs
        

def polyloopvedgeseqpolyline(polyloop, vedge):
    vedgeseq = [ [ ] ]
    for i in range(len(polyloop)):
        if abs(polyloop[i].v - vedge) < 1e-5:
            if vedgeseq[-1]:
                vedgeseq[-1][-1] = i
            else:
                vedgeseq[-1] = [i, i]
        elif vedgeseq[-1]:
            vedgeseq.append([])
    if not vedgeseq[-1]:
        vedgeseq.pop()
    assert len(vedgeseq) == 1, vedgeseq
    i0, i1 = vedgeseq[0]
    assert 0 < i0 < i1 < len(polyloop) - 1, (0, i0, i1, len(polyloop))
    return i0, i1

def singlepointwithinsurfaceoffset(seval, iapolyline, rad, sp, spstep):
    rd2 = rad*2
    nodeIn = WNode(seval(sp[0], sp[1]), sp, -1)
    nodeIn.pointzone = barmesh.PointZone(0, rd2, None)
    iapolyline.DistP(nodeIn.pointzone, nodeIn.p)
    assert nodeIn.pointzone.r < rad
    while True:
        sp += spstep
        nodeOut = WNode(seval(sp[0], sp[1]), sp, -1)
        nodeOut.pointzone = barmesh.PointZone(0, rd2, None)
        iapolyline.DistP(nodeOut.pointzone, nodeOut.p)
        if not (nodeOut.pointzone.r < rad):
            break
        nodeIn = nodeOut
    lam = iapolyline.CutposN(nodeOut, nodeIn, None, rad)
    assert 0.0 <= lam <= 1.0, lam
    spmid = Along(lam, nodeOut.sp, nodeIn.sp)
    nodeMid = WNode(seval(spmid[0], spmid[1]), spmid, -1)
    nodeMid.pointzone = barmesh.PointZone(0, rd2, None)
    iapolyline.DistP(nodeMid.pointzone, nodeMid.p)
    return nodeMid.sp
    
def polylinewithinsurfaceoffset(seval, polyline, rad, spstep):
    polylineW = [ seval(q[0], q[1])  for q in polyline ]
    iapolyline = ImplicitAreaBallOffsetOfClosedContour(polylineW, polyline, bloopclosed=False, boxwidth=10)
    polylineoffset = [ ]
    for sp in polyline:
        polylineoffset.append(singlepointwithinsurfaceoffset(seval, iapolyline, rad, sp, spstep))
    return polylineoffset

