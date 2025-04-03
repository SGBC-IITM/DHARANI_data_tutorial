
import shapely
import alphashape
import numpy as np
import scipy
from PIL import Image, ImageDraw
from allen_functions import make_polyshape

import triangle 
import trimesh

from typing import Dict

def is_convex_dist(shape):
    minx,miny,maxx,maxy=shape.bounds
    width = max((maxx-minx),(maxy-miny))
    if shapely.hausdorff_distance(shape.exterior,shape.convex_hull) > 0.1 * width:
        return False
    return True

def get_valid_shape(inshape):
    tmpshape = inshape.buffer(0)
    if tmpshape.geom_type=="MultiPolygon":
        new_shp = max(tmpshape.geoms, key=lambda item: item.area)
        return new_shp
    return tmpshape
    
def make_interior_exterior(shape):
    shapePoints=np.array(shape.exterior.xy).T.astype(int)
    new_shape = alphashape.alphashape(shapePoints,0.03)

    if new_shape.geom_type == "MultiPolygon":
        new_shape = shape.convex_hull
        
    new_outer = np.array(new_shape.exterior.xy).T.astype(int)
    new_interiors = new_shape - shape
    
    new_interior_poly = max(new_interiors.geoms, key=lambda item: item.area)

    new_interior = np.array(new_interior_poly.exterior.xy).T.astype(int)

    return new_outer, new_interior

def boundarymask(contour, mpp):
    msk = np.zeros([int(3000*32/mpp),int(3000*32/mpp)],bool)
    # r = contour[:,1]
    # c = contour[:,0]
    # rr,cc = skdraw.polygon_perimeter(r,c,msk.shape,clip=True)
    # msk[rr,cc]=1

    img = Image.fromarray(msk)
    draw = ImageDraw.Draw(img)
    draw.polygon(contour, fill=None, outline=1, width=1)
    
    msk = np.array(img)
    
    return msk


def morph_contour(fromcontour, tocontour, fromnum, tonum, internum, check_dist=False):
    
    # frommsk = boundarymask(fromcontour)
    
    # plt.subplot(1,3,1)
    # plt.imshow(frommsk)
    # plt.subplot(1,3,2)
    # plt.imshow(tomsk)
    
    assert tonum > fromnum
    assert internum > fromnum and internum < tonum
    
    nsteps = tonum-fromnum+1
    stepnum = internum-fromnum
    
    
    if tonum - internum < stepnum:
        stepnum = tonum - internum
        dstmsk = boundarymask(fromcontour)
        srcpts = tocontour
    else:
        dstmsk = boundarymask(tocontour)
        srcpts = fromcontour
        
    distmap,distidx = scipy.ndimage.distance_transform_edt(~dstmsk,return_indices=True)
    # plt.subplot(1,3,3)
    # plt.imshow(distmap)
    
    pairs = []
    widthlist = []
    newpts = []
    
    for pt in srcpts:
        pairpt = distidx[:,pt[1],pt[0]].T.squeeze()[::-1].tolist() # maintain x,y notation
        if check_dist and len(pairs) > 0:
            last = pairs[-1][1]
            dpair=np.array(pairpt)-np.array(last)
        #     dpt = np.array(pt)-np.array(pairs[-1][0])
        #     # print(pairs[-1], "x",pt, "x",pairpt, "x", dpair,end="")
        #     # relative to 4000x4000
            if np.sqrt(dpair[0]**2+dpair[1]**2) > 200: # max(200,2*np.sqrt(dpt[0]**2+dpt[1]**2)):
        #         # print(pairs[-1], "x",pt, "x",pairpt, "x", dpt)
        #         # print('###')
                pairpt = last
        #     # else:
        #     #     print()
        pairs.append((pt,pairpt))
        u = np.array(pairpt-pt)
        m = scipy.linalg.norm(u)
        widthlist.append(m)
        if m==0:
            newpts.append(pt)
        else:
            u = u/m
            newpt = np.array(pt) + u*m/nsteps*stepnum
            newpts.append(newpt)

    return np.array(newpts), pairs, widthlist


def _constrained_triangulate(polygon:shapely.Geometry):
    """Triangulate a polygon with holes using 'triangle' library."""
    ext = np.array(polygon.exterior.coords[:-1])  # Outer boundary
    holes = [np.array(hole.coords[:-1]) for hole in polygon.interiors]  # Inner boundaries
    
    # Define segment markers for constrained triangulation
    segments = np.vstack([np.column_stack([np.arange(len(ext)), np.roll(np.arange(len(ext)), -1)])])
    for hole in holes:
        hole_segments = np.column_stack([np.arange(len(hole)), np.roll(np.arange(len(hole)), -1)]) + len(ext)
        segments = np.vstack([segments, hole_segments])
        ext = np.vstack([ext, hole])  # Combine outer + hole points

    # Use triangle to perform constrained triangulation
    tri = triangle.triangulate({'vertices': ext, 'segments': segments}, 'p')
    return np.array(tri['vertices']), np.array(tri['triangles'])


def make_mesh(polydict:Dict[int,shapely.Geometry], downsample):

    mesh_vertices = []
    mesh_faces = []
    offset = 0
    scale = 1/(2**downsample)
    for secnum, poly in polydict.items():
        z = secnum*60*scale
        pts, faces = _constrained_triangulate(poly)
        pts_3d = np.hstack([pts, np.full((pts.shape[0], 1), z)])  # Convert to 3D
        mesh_vertices.append(pts_3d)
        mesh_faces.append(faces + offset)  # Adjust indices
        offset += len(pts_3d)

    mesh_vertices = np.vstack(mesh_vertices)
    mesh_faces = np.vstack(mesh_faces)

    mesh = trimesh.Trimesh(vertices=mesh_vertices, faces=mesh_faces)

    return mesh


def morph_shape(fromshape_in, toshape_in, fromnum, tonum, internum):
    fromshape = get_valid_shape(fromshape_in)
    
    toshape = get_valid_shape(toshape_in)

    # fromshape = fromshape_in
    # toshape = toshape_in
    
    # if len(fromshape.interiors)==0 and len(toshape.interiors)==0:
    #     extfrom=np.array(fromshape.exterior.xy).T.astype(int)
    #     extto=np.array(toshape.exterior.xy).T.astype(int)
        
    #     newext, pairs, widthlist = morph_contour(extfrom, extto, fromnum, tonum, internum)
    #     return make_polyshape([newext])
        
    # else:
    
    if len(fromshape.interiors) == 0:
        if is_convex_dist(toshape):
            print(internum,"case 1, no from interiors, to convex")
            extfrom, extto = make_interior_exterior(fromshape)
        else:
            print(internum,"case 2, no from interiors, to not convex")
            extfrom=np.array(fromshape.exterior.xy).T.astype(int) 
            extto=np.array(toshape.exterior.xy).T.astype(int)
        newext,pairs,widthlist = morph_contour(extfrom, extto, fromnum, tonum, internum)
        return make_polyshape([newext])
    else:
        extfrom=np.array(fromshape.exterior.xy).T.astype(int)
        intfrom = np.vstack([np.array(elt.xy).T.astype(int) for elt in fromshape.interiors])

        if len(toshape.interiors) == 0:
            if is_convex_dist(fromshape):
                print(internum,"case 3, from interiors, from convex, to no interiors")
                extto, intto = make_interior_exterior(toshape)
                newext,pairs,widthlist = morph_contour(extfrom, extto, fromnum, tonum, internum)
                newint, pairs2, widthlist2 = morph_contour(intfrom, intto, fromnum, tonum, internum,True)
                return make_polyshape([newext, newint])
            else:
                print(internum,"case 4, from interiors, from not convex, to no interiors")
                extfrom=np.array(fromshape.exterior.xy).T.astype(int) 
                extto=np.array(toshape.exterior.xy).T.astype(int)
                newext,pairs,widthlist = morph_contour(extfrom, extto, fromnum, tonum, internum)
                return make_polyshape([newext])
        else:
            print(internum,"case 5, from interiors, to interiors")
            extto=np.array(toshape.exterior.xy).T.astype(int)
            intto = np.vstack([np.array(elt.xy).T.astype(int) for elt in toshape.interiors])
    
    
            newext,pairs,widthlist = morph_contour(extfrom, extto, fromnum, tonum, internum)
            newint, pairs2, widthlist2 = morph_contour(intfrom, intto, fromnum, tonum, internum,True)
            return make_polyshape([newext, newint])
