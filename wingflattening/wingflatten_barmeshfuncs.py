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

