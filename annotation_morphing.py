
import shapely
import alphashape
import numpy as np
import scipy
from PIL import Image, ImageDraw
from allen_functions import make_polyshape

import triangle 
import trimesh

from typing import Dict

import logging

logger = logging.getLogger(__name__)

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
    # print(contour.shape, contour.dtype)
    # contour_list = contour.tolist()
    contour_list = [(int(point[0]), int(point[1])) for point in contour]
    draw.polygon(contour_list, fill=None, outline=1, width=1)
    
    msk = np.array(img)
    
    return msk


def morph_contour(fromcontour, tocontour, fromnum, tonum, internum, mpp, check_dist=False):
    
    # frommsk = boundarymask(fromcontour)
    
    # plt.subplot(1,3,1)
    # plt.imshow(frommsk)
    # plt.subplot(1,3,2)
    # plt.imshow(tomsk)
    
    assert tonum > fromnum
    assert internum > fromnum and internum < tonum
    
    nsteps = tonum-fromnum+1
    stepnum = internum-fromnum
    
    
    if tonum - internum < stepnum or len(tocontour)>len(fromcontour):
        logger.debug(f'swap: fromnum {fromnum}, internum {internum} tonum {tonum}')
        stepnum = tonum - internum
        dstmsk = boundarymask(fromcontour, mpp)
        srcpts = tocontour
    else:
        dstmsk = boundarymask(tocontour, mpp)
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
        poly_arr = []
        if poly.geom_type=='Polygon':
            poly_arr.append(poly)
        elif poly.geom_type=='MultiPolygon':
            poly_arr = poly.geoms
        for poly_i in poly_arr:
            pts, faces = _constrained_triangulate(poly_i)
            pts_3d = np.hstack([pts, np.full((pts.shape[0], 1), z)])  # Convert to 3D
            mesh_vertices.append(pts_3d)
            mesh_faces.append(faces + offset)  # Adjust indices
            offset += len(pts_3d)

    mesh_vertices = np.vstack(mesh_vertices)
    mesh_faces = np.vstack(mesh_faces)

    mesh = trimesh.Trimesh(vertices=mesh_vertices, faces=mesh_faces)

    return mesh


def morph_shape(fromshape_in, toshape_in, fromnum, tonum, internum, mpp):
    fromshape = get_valid_shape(fromshape_in)
    
    toshape = get_valid_shape(toshape_in)

    # local utility
    def get_int_ext(shp):

        if is_convex_dist(shp):
            extc = np.array(shp.exterior.xy).T.astype(int)
            intc = None
            if len(shp.interiors)>0:
                intc = np.vstack([np.array(elt.xy).T.astype(int) for elt in shp.interiors])
        else:
            extc, intc = make_interior_exterior(shp)

        return extc, intc
    
    ext_from, int_from = get_int_ext(fromshape)
    ext_to, int_to  = get_int_ext(toshape)

    # local helper to avoid repeated multi-argument calls to morph_contour
    morph_helper = lambda fromcontour, tocontour: morph_contour(fromcontour, tocontour,fromnum, tonum, internum, mpp)

    newext, _, _ = morph_helper(ext_from, ext_to)

    if int_from is not None:
        if int_to is not None:
            newint, _, _ = morph_helper(int_from, int_to)
            return make_polyshape([newext, newint])
        
        else:
            # int_to is not available, so ...
            if internum - fromnum <  tonum - internum:
                # march int_from towards ext_to
                newint, _, _ = morph_helper(int_from, ext_to)
                return make_polyshape([newext, newint])
            else:
                # march int_from towards ext_to here also,
                # as morph_contour will swap since internum is closer to tonum
                newint, _, _ = morph_helper(ext_to, int_from)
                return make_polyshape([newext, newint])
    else:
        if int_to is not None:
            if internum - fromnum  > tonum - internum:
                # march int_to towards ext_from
                newint, _, _ = morph_helper(int_to, ext_from)
                return make_polyshape([newext, newint])
            else:
                # march int_to towards ext_from here also,
                # as morph_contour will swap since internum is closer to fromnum
                newint, _, _ = morph_helper(ext_from, int_to)
                return make_polyshape([newext, newint])
        else:
            # no interiors in either shape
            return make_polyshape([newext])
            
