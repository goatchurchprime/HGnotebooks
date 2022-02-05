from basicgeo import P2, P3
import csv, numpy, math

#
# Wing geometry: maps uv in [0,1],[0,1] -> XYZ points on wing surface
#

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
        return P2(self.leadingedgelengthconv(p[0]), self.sectionchordlengthconv(self.Isect, p[1]))

    def sevalI(self, p):
        i = max(0, min(self.nsections-2, int(p[0])))
        m = p[0] - i
        p0 = P3.ConvertGZ(self.sectionchordevalI(i, p[1]), self.zvals[i])
        p1 = P3.ConvertGZ(self.sectionchordevalI(i+1, p[1]), self.zvals[i+1])
        return p0*(1-m) + p1*m
        
    def seval(self, p):
        if p[0] < 0.0:
            s = self.sevalI(self.sevalconv((-p[0], p[1])))
            return P3(s.x, s.y, -s.z)                       
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

    def linesegmentnetflipyz(self, flipyz):
        seglines = [ [flipyz(self.seval(P2(u,v)))  for v in numpy.linspace(self.vrange[0], self.vrange[1], 51)]  for u in self.leadingedgelengths ]
        spanlines = [ [flipyz(self.seval(P2(u,v)))  for u in numpy.linspace(self.urange[0], self.urange[1], 51)]  for v in numpy.linspace(self.vrange[0], self.vrange[1], 21) ]
        return seglines+spanlines
    
    

