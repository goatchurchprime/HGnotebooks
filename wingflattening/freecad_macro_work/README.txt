
Series of macros for processing wing sections of the p7 and R13 wings 
into dxf of flat pieces of fabric with pen marks.

p7wingshape.py - Creates SectionGroup of bsplines from shapes defined in P7-211221-XYZ geometry.csv

R13wingshape.py - Creates SectionGroup of bsplines from linearized shapes in Group.  Presence of 
Group node is used to identify that scripts are running against the R13 wingeval

R13blankcutlinesketch.py - Constructs cutlinesketch with a dimensioned construction line rectangle 
for use in defining the cuts in the fabric in UV space

p7cutlinestouvpolygons.py - Creates UVPolygons containing polygons of each of the areas that the 
cutlinessketch divides into.  Points need to be joined with the Coincident constraint to be 
considered a continuation of the polygon.  Polygons are given names according to a lookup table.

p7uvpolygonsfoldedoffsets.py - Extends polygons that are on the trailing edges by 6 or 18mm so that 
when the whole shape is offset by 6mm they are at 12mm and 24mm to allow the fabric to be folded over 
and sewn.  The outputs are UVPolygonOffsets and UVPolygonsFoldlines (though if they don't exist, UVPolygons 
will be used by in a subsequent stage)

p7uvpolygonstouvmeshes.py - offsets by 6mm and triangulates each polygon in UV space into UVTriangulations

p7uvmeshestosurfaces.py - projects each triangulated mesh in UV space into the wing surface 
by evaluating the function WingEval.SEval().  These go into STriangulations.  Then flatmesh.FaceUnwrapper()
is called on each surface and the flattened areas are put into SFlattened

p7drawlinesonpatches.py - projects the outlines of all the adjacent patches into SPencil groups of each patch, 
as well as projecting the "batten detail TSR.dxf" onto the trailing edge of each section

p7drawpatchestodxf.py - Outputs the file "../p7test.dxf" from the SFlattened outlines and SPencil lines




