from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from matplotlib.widgets import Button
from basicgeo import P2, P3

cursor1, cursor2 = None, None
def cursordata():
    return zip(*[cursor1 or P2(0,0), cursor2 or P2(0,0.1)])

events = [ ]
nodenamedown = None
nodeclickdistance = 0.04
Dlineedits = [ ]
parapolygraph = None
wingshape = None
fig, axpara = None, None
cursorupdater, mupdater, lupdater = None, None, None

def button_press_callback(event):
    global nodenamedown, cursor1, cursor2
    if event.inaxes == axpara:
        mp = wingshape.clampuv(P2(event.xdata, event.ydata))
        l, nn = parapolygraph.closestnodedist(mp)
        if cursor2 is not None:
            if l < nodeclickdistance:
                if nodenamedown == nn:
                    parapolygraph.delnode(nodenamedown)
                nodenamedown = None
                cursor2 = None
            elif nodenamedown is not None:
                nodenamedown = parapolygraph.newnode(nodenamedown, mp)
                Dlineedits.append(("newnode", nodenamedown))
                cursor2 = mp
            mupdater.set_data(parapolygraph.pointsdata())
            lupdater.set_segments(parapolygraph.legsdata())
        elif l < nodeclickdistance:
            if event.button == 1:
                nodenamedown = nn
                cursor1 = None
            elif event.button == 3:
                nodenamedown = nn
                cursor2 = parapolygraph.nodes[nodenamedown]
        cursorupdater.set_data(cursordata())
        fig.canvas.draw_idle()

def button_release_callback(event):
    global nodenamedown, cursor2
    events.append(event)
    if nodenamedown is not None:
        if cursor2 is not None and event.button == 3 and nodenamedown is not None and cursor1 is not None:
            l, nn = parapolygraph.closestnodedist(cursor1)
            if l < nodeclickdistance and nodenamedown != nn:
                parapolygraph.commitlineedit(nodenamedown, nn)
                #lupdater.set_segments(parapolygraph.legsdata())
            nodenamedown = None
            cursor2 = None
        elif event.button == 1 and cursor2 is None:
            nodenamedown = None
        cursorupdater.set_data(cursordata())
        lupdater.set_segments(parapolygraph.splineinterplegsdata())
        fig.canvas.draw_idle()

        
def motion_notify_callback(event):
    global cursor1
    if event.inaxes == axpara:
        mp = wingshape.clampuv(P2(event.xdata, event.ydata))
        if nodenamedown is not None and cursor2 is None:
            parapolygraph.nodes[nodenamedown] = mp
            mupdater.set_data(parapolygraph.pointsdata())
            lupdater.set_segments(parapolygraph.legsdata())
            fig.canvas.draw_idle()
        else:
            cursor1 = mp
            cursorupdater.set_data(cursordata())
            fig.canvas.draw_idle()

        
def buttonSpline(event):
    events.append(event)
    lupdater.set_segments(parapolygraph.splineinterplegsdata())
    fig.canvas.draw_idle()

def key_press_callback(event):
    events.append(event)

def makeinteractivefigure(lfig, lparapolygraph):
    global fig, parapolygraph, wingshape, axpara, cursorupdater, mupdater, lupdater
    fig = lfig
    parapolygraph = lparapolygraph
    wingshape = lparapolygraph.wingshape
    axpara = fig.add_subplot(1,1,1)
    axpara.add_collection(LineCollection([[(u, wingshape.vrange[0]), (u, wingshape.vrange[1])]  for u in wingshape.leadingedgelengths ], color="grey", linewidth=0.3))

    lupdater = axpara.add_collection(LineCollection(parapolygraph.legsdata()))
    mupdater, = axpara.plot(*parapolygraph.pointsdata(), color='black', linestyle='none', marker='o', markersize=5)
    cursorupdater, = axpara.plot(*cursordata(), color='red', linestyle='none', marker='o', markersize=3)
    lupdater.set_segments(parapolygraph.splineinterplegsdata())

    axpara.autoscale()

    #axres = plt.axes([0.15, 0.8, 0.12, 0.03])
    #bres = Button(axres, 'Spline')
    #bres.on_clicked(buttonSpline)
    
    fig.canvas.mpl_connect('button_press_event', button_press_callback)
    fig.canvas.mpl_connect('button_release_event', button_release_callback)
    fig.canvas.mpl_connect('motion_notify_event', motion_notify_callback)
    fig.canvas.mpl_connect('key_press_event', key_press_callback)


