from barmesh.basicgeo import P2, P3, Partition1, Along
import barmesh.barmesh as barmesh
from barmesh.barmesh import Bar

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

def MakeRectBarmeshForWingParametrization(wingshape, xpart, ypart):
    bm = barmesh.BarMesh()
    nxs = xpart.nparts + 1

    nodes = bm.nodes
    xbars = [ ]  # multiple of nxs
    ybars = [ ]  # multiple of nxs-1
    for y in ypart.vs:
        bfirstrow = (len(nodes) == 0)
        for i in range(nxs):
            sp = P2(xpart.vs[i], y)
            nnode = bm.AddNode(WNode(wingshape.seval(sp), sp, -1))
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




from barmesh.implicitareaballoffset import DistPZ, DistLamPZ
from barmesh.tribarmes import TriangleBarMesh, TriangleBar, MakeTriangleBoxing
from barmesh.basicgeo import I1, Partition1, P3, P2, Along
from barmesh import barmesh

class ImplicitAreaBallOffsetOfClosedContour:
    def __init__(self, polyloopW, polyloop):
        assert len(polyloopW) == len(polyloop)
        tbm = TriangleBarMesh()
        tbmF = TriangleBarMesh()
        polyloopN = [ tbm.NewNode(p)  for p in polyloopW ]
        polyloopFN = [ tbmF.NewNode(P3.ConvertGZ(p, 0.0))  for p in polyloop ]
        for i in range(len(polyloop)-1):
            tbm.bars.append(TriangleBar(polyloopN[i], polyloopN[i+1]))
            tbmF.bars.append(TriangleBar(polyloopFN[i], polyloopFN[i+1]))
        tbm.bars.append(TriangleBar(polyloopN[0], polyloopN[-1]))
        tbmF.bars.append(TriangleBar(polyloopFN[0], polyloopFN[-1]))
        
        self.tbarmesh = tbm
        self.tbarmeshF = tbmF
        self.tboxing = MakeTriangleBoxing(self.tbarmesh)
        self.tboxingF = MakeTriangleBoxing(self.tbarmeshF)
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


