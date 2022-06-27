# -*- coding: utf-8 -*-
# Macro to make project7wing as list of wires and single bspline surface

import FreeCAD as App
import Draft, Part, Mesh
import DraftGeomUtils
import math, os, csv
from FreeCAD import Vector, Rotation

# Run this on testriotwires
# Very much the same as p7wingshape


doc = App.ActiveDocument
from p7modules.p7wingeval import getemptyobject, createobjectingroup, removeObjectRecurse

groupwires = doc.Group.OutList
sections = [ [ (-v.Point.y, v.Point.z)  for v in groupwire.Shape.OrderedVertexes ]  for groupwire in groupwires ]
zvals = [ groupwire.Shape.OrderedVertexes[0].Point.x  for groupwire in groupwires ]
 
if True:
	wingloft = getemptyobject(doc, "Part::Feature", "wingloft")
	wingloft.Shape = Part.makeLoft([l.Shape  for l in doc.Group.OutList], False, True)
	if doc.findObjects(Name="SectionGroup"):
		removeObjectRecurse(doc, "SectionGroup")

else:
	# 
	# This is the old bspline fitting, which generated nasty folds in the curves
	# There's code to demo this at the bottom
	#

	assert False
	
	def deriveparametizationforallsections(chosensection):
		points = [App.Vector(0, -p[0], p[1])  for p in chosensection]
		chordlengths = [ 0 ]
		for p0, p1 in zip(points, points[1:]):
			chordlengths.append(chordlengths[-1] + (p0-p1).Length)

		print("This is the bit where we need to find the front leading edge between 0 and chordlength", chordlengths[-1])

		m = chordlengths[-1]*0.5
		return [ c-m  for c in chordlengths ]

	def makesectionsandsplineedges(doc, sg, sections, zvals, sectionparameters):
		secbsplineedges = [ ]
		for i in range(len(zvals)):
			points = [App.Vector(0, -p[0], p[1])  for p in sections[i]]
			placement = App.Placement(App.Vector(zvals[i], 0, 0), App.Rotation())
			secbspline = Part.BSplineCurve()
			
			# make sure it doesn't close the curve or cause bad spline tangents
			pointsnc = points[:-1]+[points[-1]+Vector(0,0,0.001)]
			secbspline.approximate(pointsnc, Parameters=sectionparameters, DegMin=2, DegMax=2)
			assert not secbspline.isClosed()
			
			ws = createobjectingroup(doc, sg, "Part::Feature", "section_%d"%(i+1))
			ws.Shape = secbspline.toShape()
			ws.Placement = placement
			secbsplineedges.append(ws)
		return secbsplineedges


	# clear present Groups (FC folders)
	sg = getemptyobject(doc, "App::DocumentObjectGroup", "SectionGroup")

	# pick the curve lengths of an average section to apply to the parametrization of all the other sections 
	chosenparametrization = deriveparametizationforallsections(sections[5])

	# create the sections (as consistently parametrized bsplines) and also return 
	sections = makesectionsandsplineedges(doc, sg, sections, zvals, chosenparametrization)

	# Loft this series of section curves
	wingloft = getemptyobject(doc, "Part::Feature", "wingloft")
	wingloft.Shape = Part.makeLoft([l.Shape  for l in sg.OutList], False, True)

	doc.recompute()


	#
	# Demo of bad section splines to show off the folds
	#
	import numpy, json
	from FreeCAD import Vector, Rotation

	doc = App.ActiveDocument

	jstring = '{"points": [[0.0, -2258.6778865723136, 35.490222375937066], [0.0, -2238.780656395911, 35.06666931848484], [0.0, -2197.7259594150637, 33.90532376375612], [0.0, -2169.257127335683, 33.053772509330614], [0.0, -2135.6133703859737, 32.283103781059175], [0.0, -2096.9533015049333, 31.276002895174773], [0.0, -2053.3957368933343, 31.0979601711877], [0.0, -2005.2106972022616, 30.667700169348393], [0.0, -1952.548832818226, 31.325304009683734], [0.0, -1895.7252273627892, 32.71632709556424], [0.0, -1834.9896113519112, 35.62636069760184], [0.0, -1770.67701758248, 40.58829634359693], [0.0, -1703.1259410959844, 47.33936752240299], [0.0, -1632.74995129106, 55.43992144626593], [0.0, -1559.8810555472735, 64.60872789693076], [0.0, -1484.9905058776822, 74.90490235211418], [0.0, -1408.440586941341, 86.27709726456777], [0.0, -1330.7301777174437, 98.60775826363715], [0.0, -1252.2656402716595, 111.77221218305596], [0.0, -1173.51949484184, 125.60502773550834], [0.0, -1094.951060695848, 139.7743944099855], [0.0, -1017.045647235519, 153.8760272483261], [0.0, -940.26015635237, 167.7319980398348], [0.0, -865.06480975477, 181.179376685884], [0.0, -791.9433220812828, 194.05921136880232], [0.0, -721.3956630870842, 206.18451247350885], [0.0, -653.8661286352267, 217.31691623459648], [0.0, -589.914611306707, 227.194149622452], [0.0, -530.0898742987655, 235.3995056628025], [0.0, -475.08604320913963, 241.03573884375146], [0.0, -425.5942591523402, 242.3888761762406], [0.0, -379.8307841575946, 238.52856069151744], [0.0, -335.756398542928, 230.8374449422143], [0.0, -293.65479365849444, 220.81559831963776], [0.0, -253.7047310877132, 208.58889758890547], [0.0, -216.1557993819773, 194.37670819178425], [0.0, -181.15842324543755, 178.5267674983804], [0.0, -148.83379407949158, 161.52192117389447], [0.0, -119.40887593892941, 143.727395015573], [0.0, -92.94797245737675, 125.36430049089658], [0.0, -69.57658180181848, 106.20988147992057], [0.0, -49.43634183520686, 86.73976990566852], [0.0, -32.604422313682, 67.79421888128658], [0.0, -19.153415675629386, 49.641964405641005], [0.0, -9.160518604923757, 32.11483550660447], [0.0, -2.661461130078112, 19.697713266177292], [0.0, 0.0, 0.0], [0.0, -1.6353410810971938, -11.914615319072194], [0.0, -8.839022679148286, -24.21736943790026], [0.0, -21.61592873761947, -36.06863262049397], [0.0, -38.80747074015513, -46.77481504496044], [0.0, -59.972261550690675, -55.99508161155992], [0.0, -84.91804296179781, -63.13997369194085], [0.0, -102.04529916259236, -65.74706977487955], [0.0, -148.60149481142696, -62.09444321516436], [0.0, -195.15769046026153, -58.441816655449166], [0.0, -241.71388610909608, -54.78919009573399], [0.0, -288.2700817579307, -51.136563536018805], [0.0, -334.82627740676526, -47.483936976303625], [0.0, -381.3824730555998, -43.83131041658845], [0.0, -427.93866870443446, -40.17868385687327], [0.0, -474.49486435326907, -36.52605729715808], [0.0, -521.0510600021037, -32.8734307374429], [0.0, -567.6072556509382, -29.22080417772772], [0.0, -614.1634512997728, -25.568177618012534], [0.0, -660.7196469486073, -21.91555105829736], [0.0, -707.275842597442, -18.262924498582166], [0.0, -753.8320382462765, -14.61029793886699], [0.0, -800.3882338951112, -10.957671379151806], [0.0, -846.9444295439457, -7.305044819436624], [0.0, -893.5006251927803, -3.652418259721445], [0.0, -940.0568208416149, 0.000208299993737171], [0.0, -986.6130164904495, 3.6528348597089213], [0.0, -1033.169212139284, 7.305461419424095], [0.0, -1079.7254077881184, 10.958087979139272], [0.0, -1126.2816034369532, 14.610714538854472], [0.0, -1172.8377990857878, 18.263341098569644], [0.0, -1219.3939947346223, 21.915967658284824], [0.0, -1265.9501903834569, 25.56859421800001], [0.0, -1312.5063860322916, 29.221220777715207], [0.0, -1359.0625816811262, 32.87384733743038], [0.0, -1405.6187773299607, 36.52647389714556], [0.0, -1452.1749729787953, 40.17910045686074], [0.0, -1498.73116862763, 43.831727016575925], [0.0, -1545.2873642764644, 47.48435357629111], [0.0, -1591.8435599252991, 51.136980136006294], [0.0, -1638.3997555741328, 54.79060669572143]], "parameters": [-1146.300354360099, -1135.8204070708882, -1114.2353518839386, -1099.2739974211793, -1081.6173692871803, -1061.3405550338482, -1038.517482471261, -1013.280382404845, -985.7161547868707, -955.9832348780449, -924.2163906502603, -890.598819014331, -855.298045565625, -818.5339147286863, -780.4733847332748, -741.3653622910147, -701.3977870352941, -660.8301628206957, -619.8716337398091, -578.7689238601944, -537.7616743364943, -497.09889430117937, -457.02140395162655, -417.7765077631433, -379.61824157300794, -342.8093135537663, -307.58501297606733, -274.23983354080747, -243.0636489977452, -214.43860650683928, -188.75100095505968, -164.9706974814443, -141.9115727017512, -119.67448502365028, -98.24466368038634, -77.59720335209568, -57.76522375267518, -38.72859900292792, -20.5071680170106, -3.32280781604004, 13.024477883082909, 28.31103575404586, 42.579825647286725, 55.44664989584794, 66.79195532759627, 75.69368629630162, 83.99835486102211, 88.98331965484545, 95.78694006884825, 103.64872233858569, 112.86365397637928, 123.97032343082469, 136.94956554071564, 152.44433213202865, 170.94679276452712, 192.25363802992615, 194.43862863172058, 226.16735282266654, 257.8960770136125, 289.6248012045585, 321.35352539550445, 353.0822495864504, 384.8109737773964, 416.53969796834235, 448.2684221592883, 479.9971463502343, 511.72587054118026, 543.4545947321262, 575.1833189230722, 606.9120431140182, 638.6407673049641, 670.3694914959101, 702.0982156868561, 733.826939877802, 765.555664068748, 797.284388259694, 829.0131124506399, 860.7418366415859, 892.4705608325319, 924.1992850234778, 955.9280092144236, 987.6567334053693, 1019.3854575963151, 1051.1141817872608, 1082.8429059782065, 1114.5716301691523, 1146.300354360099]}'
	jdata = json.loads(jstring)
	wsp = doc.addObject("Part::Feature", "poly")
	wsp.Shape = Part.makePolygon(points)

	ws = doc.addObject("Part::Feature", "bspline")

	chordlengths = [ 0 ]
	for p0, p1 in zip(points, points[1:]):  chordlengths.append(chordlengths[-1] + (p0-p1).Length)


	s = Part.BSplineCurve()
	dfac = 0.6
	#s.approximate(jdata["points"], Parameters=jdata["parameters"])
	s.approximate(jdata["points"], Parameters=chordlengths, DegMin=2, DegMax=2)
	#s.approximate(jdata["points"])
	#s.approximate(jdata["points"], Parameters=jdata["parameters"], DegMin=2, DegMax=2)

	pts = [ s.value(v)-Vector(0,0,v*dfac)  for v in numpy.linspace(s.FirstParameter, s.LastParameter, 1000) ]
	ws.Shape = Part.makePolygon(pts)





