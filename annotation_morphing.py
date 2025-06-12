
import shapely
import alphashape
import numpy as np
import scipy
from PIL import Image, ImageDraw
from allen_functions import make_polyshape

import triangle 
import trimesh

from typing import Dict
from annotation_handling import AnnotationSet

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

def make_interior_exterior2(shape):
    shapePoints=np.array(shape.exterior.xy).T
    new_shape = alphashape.alphashape(shapePoints,0.03)

    if new_shape.geom_type == "MultiPolygon":
        new_shape = shape.convex_hull
        
    new_outer = np.array(new_shape.exterior.xy).T
    new_interiors = new_shape - shape
    
    new_interior_poly = max(new_interiors.geoms, key=lambda item: item.area)

    new_interior = np.array(new_interior_poly.exterior.xy).T

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

def boundarymask1(contour: np.ndarray, padding: int = 50):
    """
    Creates a boolean mask for a given contour. The mask is adaptively sized
    to fit the contour with specified padding.

    Args:
        contour: Numpy array of points for the contour (N, 2), in pixel units (x,y) or (c,r).
        padding: Padding (in micron units) around the contour's bounding box.

    Returns:
        A tuple (msk, offset):
        - msk: The boolean mask array.
        - offset: A numpy array [offset_x, offset_y] used to translate global
                  contour coordinates to local mask coordinates.
    """
    if contour is None or contour.shape[0] < 2:
        logger.warning("Boundarymask: Input contour is None or has too few points. Returning minimal mask.")
        min_dim = padding * 2 + 1
        return np.zeros((min_dim, min_dim), dtype=bool), np.array([0.0, 0.0], dtype=float)

    min_coords = np.min(contour, axis=0)
    max_coords = np.max(contour, axis=0)

    offset = min_coords - padding
    
    height = int(np.ceil(max_coords[1] - min_coords[1])) + 1 + 2 * padding
    width = int(np.ceil(max_coords[0] - min_coords[0])) + 1 + 2 * padding
    
    height = max(height, padding * 2 + 1) # Ensure minimum size
    width = max(width, padding * 2 + 1)

    msk = np.zeros((height, width), dtype=bool)
    
    contour_local_to_mask = contour - offset
    contour_list_for_draw = [(int(round(p[0])), int(round(p[1]))) for p in contour_local_to_mask]

    if len(contour_list_for_draw) >= 2: # ImageDraw.polygon needs at least 2 points for a line
        img = Image.fromarray(msk)
        draw = ImageDraw.Draw(img)
        draw.polygon(contour_list_for_draw, fill=None, outline=True, width=1) # Use outline=True
        msk = np.array(img)
    
    return msk, offset

def morph_contour(fromcontour:np.ndarray, tocontour:np.ndarray, fromnum:int, tonum:int, internum:int, mpp:float, check_dist=False):
    """
    Morphs a contour from 'fromcontour' towards 'tocontour' at an intermediate z-level.
    Returns the intermediate contour, pointwise correspondences, and width list.

    Args:
        fromcontour: Numpy array of points for the starting contour (N, 2).
        tocontour: Numpy array of points for the target contour (M, 2).
        fromnum: Z-level of fromcontour.
        tonum: Z-level of tocontour.
        internum: Z-level of the desired intermediate contour (must be between fromnum and tonum).
        
        check_dist: If True, applies a heuristic to prevent large jumps in corresponding points.

    Returns:
        newpts: Numpy array of points for the morphed contour at internum.
        pairs: List of tuples (point_from_fromcontour, corresponding_point_from_tocontour_mask).
               This order is guaranteed regardless of internal swap logic.
        widthlist: List of distances between corresponding points in 'pairs'.
    """
    # frommsk = boundarymask(fromcontour)
    
    # plt.subplot(1,3,1)
    # plt.imshow(frommsk)
    # plt.subplot(1,3,2)
    # plt.imshow(tomsk)
    
    assert tonum > fromnum
    assert internum > fromnum and internum < tonum, f"invalid inputs: fromnum {fromnum}, tonum {tonum}, internum {internum}"
    
    nsteps = tonum-fromnum+1
    stepnum = internum-fromnum
    
    swapped = False
    
    if tonum - internum < stepnum or len(tocontour)>len(fromcontour):
        logger.debug(f'swap: fromnum {fromnum}, internum {internum} tonum {tonum}')
        swapped = True
        stepnum = tonum - internum
        dstmsk = boundarymask(fromcontour, mpp)
        srcpts = tocontour
    else:
        dstmsk = boundarymask(tocontour, mpp)
        srcpts = fromcontour
        
    
    distmap,distidx = scipy.ndimage.distance_transform_edt(~dstmsk,return_indices=True)
    
    # plt.subplot(1,3,3)
    # plt.imshow(distmap)

    _srcpts_max_extent = 0 # Or some small value
    if srcpts.shape[0] > 1:
        min_src = np.min(srcpts, axis=0)
        max_src = np.max(srcpts, axis=0)
        _srcpts_max_extent = np.max(max_src - min_src)
    
    pairs = []
    widthlist = []
    newpts = []
    
    for pt in srcpts:
        
        pairpt = distidx[:,int(round(pt[1])),int(round(pt[0]))].T.squeeze()[::-1] # maintain x,y notation. distidx is (2, H, W), indices are (y, x)
        
        
        # Calculate distance between the current source point and its corresponding point in the destination mask
        dist_to_pair = distmap[int(round(pt[1])), int(round(pt[0]))]
        if dist_to_pair == 0:
            print(pt,pairpt)
            
        # Heuristic check: If the distance to the corresponding point is large
        # relative to the size of the source contour, it might be an invalid pairing.
        if check_dist:
            
            # Check distance relative to the overall size of the source contour
            if _srcpts_max_extent > 0 and dist_to_pair > 0.5 * _srcpts_max_extent:
                 logger.debug(f"Skipping potentially bad pair for point {pt}: distance {dist_to_pair:.2f} > 0.5 * src_extent {_srcpts_max_extent:.2f}")
                 continue # Skip this potentially bad pairing

            # Check distance relative to the distance between consecutive points in srcpts
            # This requires keeping track of the previous point in srcpts and its pair.
            # This check is already partially implemented below using 'last' and 'dpair'.
            if len(pairs) > 0:
                lastpair = pairs[-1]
                dlast = distmap[int(round(lastpair[0][1])), int(round(lastpair[0][0]))]
                
                # dpt = np.array(pt)-np.array(pairs[-1][0])
                # relative to 4000x4000
                # max(200,2*np.sqrt(dpt[0]**2+dpt[1]**2)):
                dratio = abs(1-dlast/dist_to_pair)
                if dratio > 0.3:
                    pairpt = lastpair[1]
                    # continue
                
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

    if swapped:
        pairs_fixed = [(pairpt,pt) for pt, pairpt in pairs]
    else:
        pairs_fixed = pairs
    
    del dstmsk
    return np.array(newpts), pairs_fixed, widthlist


def _constrained_triangulate(polygon:shapely.Geometry):
    """Triangulate a polygon with holes using 'triangle' library."""
    ext = np.array(polygon.exterior.coords[:-1])  # Outer boundary
    holes = [np.array(hole.coords[:-1]) for hole in polygon.interiors]  # Inner boundaries
    
    # Define segment markers for constrained triangulation
    segments = np.vstack([np.column_stack([np.arange(len(ext)), np.roll(np.arange(len(ext)), -1)])])
    # Adjust hole indices to be relative to the combined point list
    current_point_idx = len(ext)
    for hole in holes:
        hole_segments = np.column_stack([np.arange(len(hole)), np.roll(np.arange(len(hole)), -1)]) + current_point_idx
        segments = np.vstack([segments, hole_segments])
        ext = np.vstack([ext, hole])  # Combine outer + hole points
        current_point_idx += len(hole)

    # Use triangle to perform constrained triangulation
    tri = triangle.triangulate({'vertices': ext, 'segments': segments}, 'p')
    return np.array(tri['vertices']), np.array(tri['triangles'])

#%% method 1 - naive meshing - demonstrated in dharani_3d_sample1.ipynb

def make_mesh(polydict:Dict[int,shapely.Geometry], mpp, section_thickness=60):

    mesh_vertices = []
    mesh_faces = []
    offset = 0
    scale = 1/mpp
    for secnum, poly in polydict.items():
        z = secnum*section_thickness*scale
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

#%% Method 2 - demonstrated in dharani_3d_sample2.ipynb

from typing import List, Tuple, Union

def create_surface_between_contours(
    point_pairs_pixel: List[Tuple[Union[np.ndarray, List[float]], Union[np.ndarray, List[float]]]],
    z_for_first_points_microns: float,
    z_for_second_points_microns: float,
    mpp: float
) -> trimesh.Trimesh:
    """
    Creates a 3D surface (Trimesh) between two contours that have point-wise correspondences.
    This function effectively "skins" the two contours to form a tube-like structure.

    Args:
        point_pairs_pixel: A list of tuples, where each tuple (p1, p2) contains
                     corresponding 2D points from the first and second contours,
                     respectively. p1 and p2 are expected to be [x, y] coordinates.
                     Example: [([x1a, y1a], [x2a, y2a]), ([x1b, y1b], [x2b, y2b]), ...]
        z_for_first_points: The z-coordinate for all first points (p1) in the pairs.
        z_for_second_points: The z-coordinate for all second points (p2) in the pairs.

    Returns:
        A trimesh.Trimesh object representing the surface connecting the two contours.
        Returns an empty Trimesh if not enough pairs are provided (less than 2)
        to form a surface.
    """
    if not point_pairs_pixel or len(point_pairs_pixel) < 2:
        # Not enough points/pairs to form a surface
        return trimesh.Trimesh()

    vertices = []
    for p1, p2 in point_pairs_pixel:
        vertices.append([p1[0]*mpp, p1[1]*mpp, z_for_first_points_microns])
        vertices.append([p2[0]*mpp, p2[1]*mpp, z_for_second_points_microns])
    
    vertices_np = np.array(vertices, dtype=float)

    faces = []
    num_correspondences = len(point_pairs_pixel)

    for i in range(num_correspondences):
        # Index of the i-th point on the first contour (at z_for_first_points)
        idx_p1_i = 2 * i
        # Index of the i-th point on the second contour (at z_for_second_points)
        idx_p2_i = 2 * i + 1
        
        # Index of the (i+1)-th point on the first contour (wrapping around)
        idx_p1_next_i = 2 * ((i + 1) % num_correspondences)
        # Index of the (i+1)-th point on the second contour (wrapping around)
        idx_p2_next_i = 2 * ((i + 1) % num_correspondences) + 1

        # Create two triangles for the quad formed by (p1_i, p2_i, p2_next_i, p1_next_i)
        # Triangle 1: (p1_i, p2_i, p2_next_i)
        faces.append([idx_p1_i, idx_p2_i, idx_p2_next_i])
        # Triangle 2: (p1_i, p2_next_i, p1_next_i)
        faces.append([idx_p1_i, idx_p2_next_i, idx_p1_next_i])
    
    faces_np = np.array(faces, dtype=int)

    if vertices_np.shape[0] == 0 or faces_np.shape[0] == 0:
        return trimesh.Trimesh() # Should not happen if len(point_pairs) >= 2
        
    return trimesh.Trimesh(vertices=vertices_np, faces=faces_np)

def _resample_contour(contour: np.ndarray, num_points: int) -> np.ndarray:
    """Resamples a 2D contour to a specific number of points using linear interpolation."""
    if len(contour) == num_points:
        return contour
    if len(contour) < 2: # Cannot interpolate if less than 2 points
        if num_points > 0 and len(contour) == 1: # Repeat the single point if num_points > 0
            return np.repeat(contour, num_points, axis=0)
        return contour # Or return empty if num_points is 0 or contour is empty

    # Create a closed path for interpolation by appending the start point
    closed_contour = np.vstack([contour, contour[0]])
    
    # Calculate cumulative distances along the path
    distances = np.cumsum(np.sqrt(np.sum(np.diff(closed_contour, axis=0)**2, axis=1)))
    distances = np.insert(distances, 0, 0) # Start distance at 0

    if distances[-1] == 0: # All points are coincident
        return np.repeat(contour[[0]], num_points, axis=0)

    # Create interpolation functions for x and y
    interp_x = scipy.interpolate.interp1d(distances, closed_contour[:, 0], kind='linear')
    interp_y = scipy.interpolate.interp1d(distances, closed_contour[:, 1], kind='linear')

    # Generate new points by interpolating at evenly spaced distances
    new_distances = np.linspace(0, distances[-1], num_points, endpoint=False) # endpoint=False as we handle open contours
    return np.vstack([interp_x(new_distances), interp_y(new_distances)]).T

def morph_contour2(fromcontour_orig:np.ndarray, tocontour_orig:np.ndarray, fromnum:int, tonum:int):
    """
    Morphs a contour from 'fromcontour_orig' towards 'tocontour_orig' at an
    intermediate z-level using Shapely for correspondence.
    Operates on float coordinates.

    Args:
        fromcontour_orig: Numpy array of points for the starting contour (N, 2).
        tocontour_orig: Numpy array of points for the target contour (M, 2).
        fromnum: Z-level of fromcontour.
        tonum: Z-level of tocontour.

    Returns:
        newpts: Numpy array of points for the morphed contour at internum.
        pairs_final: List of tuples (point_from_fromcontour_resampled, corresponding_point_on_tocontour_resampled).
        widthlist: List of distances between corresponding points in 'pairs_final'.
    """

    src_contour = fromcontour_orig
    dst_contour = tocontour_orig

    nsteps = tonum-fromnum+1
    stepnum_for_interp = (fromnum+tonum)//2
    swapped = False

    if len(fromcontour_orig)<len(tocontour_orig):
        src_contour = tocontour_orig
        dst_contour = fromcontour_orig
        swapped = True

    # Create a closed LineString for the destination contour for projection
    dst_line = shapely.LineString(np.vstack([dst_contour, dst_contour[0]]))

    pairs_intermediate = [] # Will be (src_pt, corresponding_dst_pt)
    widthlist = []
    newpts_interpolated = []
    for pt_src in src_contour:
        # Find the closest point on the destination LineString
        pt_dst_corresponding: np.ndarray
        param_on_dst = dst_line.project(shapely.Point(pt_src))
        pt_dst_corresponding_candidate = np.array(dst_line.interpolate(param_on_dst).coords[0])
        pt_dst_corresponding = pt_dst_corresponding_candidate
    
        pairs_intermediate.append((pt_src, pt_dst_corresponding))
        
        vec = pt_dst_corresponding - pt_src
        dist = np.linalg.norm(vec)
        widthlist.append(dist)

        if dist == 0:
            newpts_interpolated.append(pt_src)
        else:
            unit_vec = vec / dist
            newpt = pt_src + unit_vec * dist * (stepnum_for_interp / nsteps)
            newpts_interpolated.append(newpt)

    pairs_out = pairs_intermediate
    if swapped:
        pairs_out = [(pair[1],pair[0]) for pair in pairs_out]
    
    return np.array(newpts_interpolated), pairs_out, widthlist

    
def morph_contour3(fromcontour_orig:np.ndarray, tocontour_orig:np.ndarray, 
                   fromnum:int, tonum:int, allow_swap=True):
    """
    Morphs a contour. The first src point gets global correspondence on dst.
    Subsequent src points search locally on dst. The search window on dst
    starts at the previous src point's correspondence and extends by a length
    proportional to the current src segment's length, scaled by the ratio of
    dst_perimeter / src_perimeter.

    Args:
        fromcontour_orig: Numpy array of points for the starting contour (N, 2).
        tocontour_orig: Numpy array of points for the target contour (M, 2).
        fromnum: Z-level of fromcontour.
        tonum: Z-level of tocontour.

    Returns:
        newpts: Numpy array of points for the morphed contour at internum.
        pairs_out: List of tuples (point_from_original_fromcontour, corresponding_point_on_original_tocontour_line).
        widthlist: List of distances between corresponding points in `pairs_out`.
        paired_indices_final: List of tuples (idx_in_fromcontour_orig, idx_in_tocontour_orig) for paired vertices.
    """
    

    # Determine src_contour (iterated over) and dst_contour (projected onto)
    # This also sets the 'swapped' flag for final pair ordering.
    src_contour = fromcontour_orig
    dst_contour = tocontour_orig
    swapped = False
    
    # Ensure contours are treated as closed LineStrings for length calculation and projection
    _src_line_for_length = shapely.LineString(np.vstack([src_contour, src_contour[0]]))
    _dst_line_for_length = shapely.LineString(np.vstack([dst_contour, dst_contour[0]]))

    src_perimeter = _src_line_for_length.length
    dst_perimeter = _dst_line_for_length.length

    if src_perimeter < dst_perimeter and allow_swap:
        # src_contour should be larger
        src_contour = tocontour_orig
        dst_contour = fromcontour_orig
        swapped = True
        tmp = dst_perimeter
        dst_perimeter = src_perimeter
        src_perimeter = tmp
            

    full_dst_line = shapely.LineString(np.vstack([dst_contour, dst_contour[0]]))

    
    perimeter_ratio = 1.0
    if src_perimeter > 1e-9: # Avoid division by zero or extreme ratios
        perimeter_ratio = dst_perimeter / (src_perimeter + 1e-6)

    current_correspondences = [] # List of (pt_from_src_contour, pt_on_dst_line)
    paired_indices_raw = []      # List of (idx_in_current_src_contour, idx_of_closest_vertex_in_current_dst_contour)
    # Stores the dst correspondence (a point) of the previous src point
    pt_dst_correspondence_of_prev_src = None
    # Stores the previous src point itself
    pt_s_previous = None

    for i, pt_s in enumerate(src_contour):
        if i == 0: # First point: Global projection
            param = full_dst_line.project(shapely.Point(pt_s))
            pt_t_current = np.array(full_dst_line.interpolate(param).coords[0])

            # Find closest original vertex in dst_contour to pt_t_current
            distances_to_dst_vertices = np.linalg.norm(dst_contour - pt_t_current, axis=1)
            idx_t_closest = np.argmin(distances_to_dst_vertices)

        else: # Subsequent points: Local projection
            # Parameter on full_dst_line of the previous src point's correspondence
            if pt_dst_correspondence_of_prev_src is None: # Should not happen if i > 0
                raise ValueError("pt_dst_correspondence_of_prev_src is None in local projection step.")
                
            param_prev_dst_correspondence = full_dst_line.project(shapely.Point(pt_dst_correspondence_of_prev_src))

            # Length of the current segment on the src_contour
            current_src_segment_length = np.linalg.norm(pt_s - pt_s_previous)
            scaled_segment_length_for_dst = current_src_segment_length * perimeter_ratio * 2.5

            t_start_local_search = param_prev_dst_correspondence
            # Ensure the search window has a minimal positive length
            t_end_local_search = t_start_local_search + max(1e-6, scaled_segment_length_for_dst)

            local_search_segment = shapely.ops.substring(full_dst_line, t_start_local_search, t_end_local_search, normalized=False)

            assert not( local_search_segment.is_empty or local_search_segment.length < 1e-6)
                # pt_t_current = np.array(full_dst_line.interpolate(param_prev_dst_correspondence).coords[0])
            # else:
            param_on_local_search = local_search_segment.project(shapely.Point(pt_s))
            pt_t_current = np.array(local_search_segment.interpolate(param_on_local_search).coords[0])

            # Find closest original vertex in dst_contour to pt_t_current
            distances_to_dst_vertices = np.linalg.norm(dst_contour - pt_t_current, axis=1)
            idx_t_closest = np.argmin(distances_to_dst_vertices)
        
        current_correspondences.append((pt_s, pt_t_current))
        paired_indices_raw.append((i, idx_t_closest)) # i is the index of pt_s in src_contour
        pt_dst_correspondence_of_prev_src = pt_t_current
        pt_s_previous = pt_s

    # Calculate interpolated points and widthlist based on final correspondences
    # Interpolation is to the midpoint for this function version
    nsteps_total = tonum - fromnum # Total z-distance
    # Effective 'internum' is the midpoint. Interpolation fraction is 0.5.
    interpolation_fraction = 0.5 if nsteps_total !=0 else 0 

    widthlist = []
    newpts_interpolated = []
    for pt_s, pt_t in current_correspondences:
        vec = pt_t - pt_s
        dist = np.linalg.norm(vec)
        widthlist.append(dist)
        if dist == 0:
            newpts_interpolated.append(pt_s)
        else:
            newpts_interpolated.append(pt_s + vec * interpolation_fraction)

    pairs_out = current_correspondences
    if swapped:
        # current_correspondences are (pt_from_tocontour_orig, pt_on_fromcontour_orig_line)
        # paired_indices_raw are (idx_in_tocontour_orig, idx_in_fromcontour_orig)
        pairs_out = [(pair[1],pair[0]) for pair in pairs_out]
        paired_indices_final = [(idx_pair[1], idx_pair[0]) for idx_pair in paired_indices_raw]
    else:
        # current_correspondences are (pt_from_fromcontour_orig, pt_on_tocontour_orig_line)
        # paired_indices_raw are (idx_in_fromcontour_orig, idx_in_tocontour_orig)
        paired_indices_final = paired_indices_raw
    
    return np.array(newpts_interpolated), pairs_out, widthlist, paired_indices_final


# def find_unpaired_point_indices(
#     pairs: List[Tuple[np.ndarray, np.ndarray]],
#     from_contour: np.ndarray,
#     to_contour: np.ndarray,
#     distance_threshold: float = 0.5  # Threshold to consider a point "matched"
# ) -> Tuple[List[int], List[int], List[Tuple[int, int]]]:
#     """
#     Finds the indices of points in from_contour and to_contour that are
#     not closely matched in the provided pairs, and also returns a list of
#     indices for points that are considered paired.

#     The 'pairs' argument is expected to be a list of tuples (p_related_to_from, p_related_to_to),
#     where p_related_to_from is a point from or projected onto the original from_contour,
#     and p_related_to_to is a point from or projected onto the original to_contour.

#     Args:
#         pairs: A list of tuples, where each tuple (p_from, p_to) contains
#                corresponding 2D points. p_from relates to from_contour,
#                and p_to relates to to_contour.
#         from_contour: Numpy array of original points for the 'from' contour (N, 2).
#         to_contour: Numpy array of original points for the 'to' contour (M, 2).
#         distance_threshold: Maximum distance for an original contour vertex to be
#                             considered "matched" to its corresponding point in the pairs.

#     Returns:
#         A tuple (unpaired_from_indices, unpaired_to_indices, paired_indices_list):
#         - unpaired_from_indices: List of indices of points in from_contour
#                                  that are considered unpaired.
#         - unpaired_to_indices: List of indices of points in to_contour
#                                that are considered unpaired.
#         - paired_indices_list: List of tuples (idx_from, idx_to), where
#                                  from_contour[idx_from] and to_contour[idx_to]
#                                  are considered a matched pair of original vertices.
#     """
#     unpaired_from_indices = []
#     unpaired_to_indices = []
#     paired_indices_list = []

#     # Extract the points from 'pairs' that correspond to from_contour and to_contour
#     # pair[0] is related to from_contour, pair[1] is related to to_contour
#     paired_points_for_from_contour = []
#     paired_points_for_to_contour = []
#     if pairs:
#         for pair in pairs:
#             paired_points_for_from_contour.append(pair[0])
#             paired_points_for_to_contour.append(pair[1])

#     # Store which original vertices are considered "matched"
#     is_from_vertex_matched = [False] * len(from_contour)
#     is_to_vertex_matched = [False] * len(to_contour)

#     has_from_contour_points = from_contour.ndim == 2 and from_contour.shape[0] > 0
#     has_to_contour_points = to_contour.ndim == 2 and to_contour.shape[0] > 0

#     # Find unpaired indices in from_contour
#     if has_from_contour_points:
#         if not paired_points_for_from_contour: # No pairs, so all from_contour points are unpaired
#             unpaired_from_indices = list(range(len(from_contour)))
#             # is_from_vertex_matched remains all False
#         else:
#             for i, vertex_from in enumerate(from_contour):
#                 matched_this_vertex = False
#                 for p_from_paired in paired_points_for_from_contour:
#                     if np.linalg.norm(vertex_from - p_from_paired) < distance_threshold:
#                         matched_this_vertex = True
#                         break
#                 if not matched_this_vertex:
#                     unpaired_from_indices.append(i)
#                 is_from_vertex_matched[i] = matched_this_vertex

#     # Find unpaired indices in to_contour
#     if has_to_contour_points:
#         if not paired_points_for_to_contour: # No pairs, so all to_contour points are unpaired
#             unpaired_to_indices = list(range(len(to_contour)))
#             # is_to_vertex_matched remains all False
#         else:
#             for i, vertex_to in enumerate(to_contour):
#                 matched_this_vertex = False
#                 for p_to_paired in paired_points_for_to_contour:
#                     if np.linalg.norm(vertex_to - p_to_paired) < distance_threshold:
#                         matched_this_vertex = True
#                         break
#                 if not matched_this_vertex:
#                     unpaired_to_indices.append(i)
#                 is_to_vertex_matched[i] = matched_this_vertex

#     # Determine paired_indices_list based on the input `pairs`
#     # and the "matched" status of original vertices.
#     if pairs and has_from_contour_points and has_to_contour_points:
#         temp_paired_indices_set = set()

#         for p_rel_from, p_rel_to in pairs:
#             # Find closest original vertex in from_contour to p_rel_from
#             min_dist_from = float('inf')
#             best_idx_from = -1
#             for idx_f, v_from in enumerate(from_contour):
#                 dist = np.linalg.norm(v_from - p_rel_from)
#                 if dist < min_dist_from:
#                     min_dist_from = dist
#                     best_idx_from = idx_f
            
#             # Find closest original vertex in to_contour to p_rel_to
#             min_dist_to = float('inf')
#             best_idx_to = -1
#             for idx_t, v_to in enumerate(to_contour):
#                 dist = np.linalg.norm(v_to - p_rel_to)
#                 if dist < min_dist_to:
#                     min_dist_to = dist
#                     best_idx_to = idx_t

#             if best_idx_from != -1 and best_idx_to != -1:
#                 # Check if these closest original vertices are within threshold of the pair points
#                 # AND if these original vertices were themselves considered "matched".
#                 if min_dist_from < distance_threshold and \
#                    min_dist_to < distance_threshold and \
#                    is_from_vertex_matched[best_idx_from] and \
#                    is_to_vertex_matched[best_idx_to]:
#                     temp_paired_indices_set.add((best_idx_from, best_idx_to))
        
#         paired_indices_list = sorted(list(temp_paired_indices_set))

#     return unpaired_from_indices, unpaired_to_indices, paired_indices_list


class ContourSequenceMesher:
    """
    Accumulates a sequence of 2D contours at different z-levels and builds
    a 3D surface mesh by skinning between consecutive contours.

    The mesh is built incrementally between each pair of consecutive contours
    in the sequence, sorted by z-level.
    """

    def __init__(self, mpp: float, section_thickness_microns:float):
        """
        Initializes the mesher.

        Args:
            mpp: Microns per pixel, used for X and Y scaling.
            section_thickness_microns: Thickness of each section im microns (z-dimension).
        """
        self._mpp = mpp
        self._section_thickness_microns = section_thickness_microns

        # Store contours as numpy arrays of points, keyed by z_level
        
        self._contours: Dict[int, np.ndarray] = {}
        self._mesh: trimesh.Trimesh = trimesh.Trimesh() # Start with an empty mesh
        self._is_built = False # Flag to track if the mesh needs rebuilding
        self._resampled_contours_for_mesh: Dict[int, np.ndarray] = {} # Store resampled contours for reuse

    def add_contour(self, contour:  np.ndarray, z_level: int, homogenize:bool = True):
        """
        Adds a contour at a specific z-level to the sequence.

        Adding a contour invalidates the current mesh, requiring a rebuild
        via `build_mesh()` or `get_mesh()`.

        Args:
            contour: The 2D contour. A numpy array of points (N, 2).
            z_level: The z-coordinate for this contour (secnum).
            homogenize: If True, the contour is resampled to have more uniform segment lengths.
                This can improve the quality of the generated mesh.
                If False, the original contour points are used.
        """
        
        # Store points. morph_contour's boundarymask expects int, but morph_contour
        # itself seems to handle float input and returns float pairs.
        # Let's store as float and ensure morph_contour handles it.
        # If morph_contour truly requires int input, we'd convert here.
        # Based on the provided code, boundarymask converts to int internally.
        # So, passing float points to morph_contour should be fine.
        
        assert len(contour)>2, f"degenerate contour at z-level {z_level}"

        self._contours[z_level] = contour.astype(float)
        if homogenize:
            self._contours[z_level] = _resample_contour2(self._contours[z_level])

        self._is_built = False # Mark mesh as needing rebuild
        self._resampled_contours_for_mesh = {} # Clear cached resampled contours

    def build_mesh(self):
        """
        Builds or rebuilds the 3D mesh from the accumulated contours.
        This method sorts contours by z-level and creates mesh segments
        between each consecutive pair.
        """
        
        sorted_z_levels = sorted(self._contours.keys())
        
        if not sorted_z_levels:
            self._mesh = trimesh.Trimesh()
            self._is_built = True
            return

        maxpts_contour = max([len(c) for z,c in self._contours.items()])
        print('max contour len', maxpts_contour)

        all_segments = []

        medgap = np.median(np.diff(sorted_z_levels)) if len(sorted_z_levels) > 1 else 0

        for i in range(len(sorted_z_levels) - 1):
            z1 = sorted_z_levels[i]
            z2 = sorted_z_levels[i+1]
            
            if medgap > 0 and (z2 - z1) > 2 * medgap:
                logging.warning(f"Gap between z={z1} and z={z2} is larger than 2*median {medgap}.")
                continue
            
            if i==0:
                from_contour = _resample_contour(self._contours[z1], maxpts_contour)
            else:
                from_contour = self._resampled_contours_for_mesh[z1]
                

            to_contour = _resample_contour(self._contours[z2], maxpts_contour)

            _, pairs, _, paired_indices = morph_contour3(from_contour, to_contour, z1, z2) #, contour_lengths[z1], contour_lengths[z2])
            
            idx_left = [] # ordered list
            idx_right = []
            # unpack as left and right
            for idx_from, idx_to in paired_indices:
                idx_left.append(idx_from)
                idx_right.append(idx_to)

            unpaired_from_idx = set(range(len(from_contour)))-set(idx_left)
            unpaired_to_idx = set(range(len(to_contour)))-set(idx_right)

            # unpaired_from_idx, unpaired_to_idx, paired_indices = find_unpaired_point_indices(pairs, from_contour, to_contour, 1)

            print(i, 'unpaired from ', len(unpaired_from_idx), 'unpaired to', len(unpaired_to_idx), 'paired', len(pairs), 'len from', len(from_contour), 'len to', len(to_contour))

            
            new_pair_indices_left = []

            tol_left = np.median(np.diff(sorted(idx_left)))
            print('tol_left',tol_left)
            
            if True:
                for from_ii in unpaired_from_idx:
                    pos = np.argmin(np.abs(np.array(idx_left)-from_ii))
                    v = idx_left[pos]-from_ii
                    if abs(v) < tol_left:
                        nearest_to_ii = idx_right[pos]
                        new_pair_indices_left.append((from_ii,nearest_to_ii))

            new_pair_indices_right = []

            tol_right = np.median(np.diff(sorted(idx_right)))
            print('tol_right', tol_right)
            if False:
                for to_ii in unpaired_to_idx:
                    pos = np.argmin(np.array(idx_right)-to_ii)
                    v = idx_right[pos]-to_ii
                    if v < tol_right:
                        nearest_from_ii = idx_left[pos]
                        new_pair_indices_right.append((nearest_from_ii,to_ii))
            
            # Combine original paired indices with newly found local pairs
            all_paired_indices = paired_indices + new_pair_indices_left + new_pair_indices_right

            # Create the list of actual point pairs based on the indices
            pairs_for_surface = []
            for idx_from, idx_to in all_paired_indices:
                if idx_from < len(from_contour) and idx_to < len(to_contour):
                    pairs_for_surface.append((from_contour[idx_from], to_contour[idx_to]))
                else:
                    logger.warning(f"Invalid index in all_paired_indices: ({idx_from}, {idx_to}) for contours of lengths {len(from_contour)} and {len(to_contour)}")

            # Store resampled contours for the next iteration

            # pairs_for_surface = pairs # debugging

            self._resampled_contours_for_mesh[z1] = from_contour
            self._resampled_contours_for_mesh[z2] = to_contour
            

            z_first = float(z1)*self._section_thickness_microns
            z_second = float(z2)*self._section_thickness_microns

            # Create the mesh segment between these two contours
            segment_mesh = create_surface_between_contours(
                pairs_for_surface,
                z_first,
                z_second,
                self._mpp
            )
            all_segments.append(segment_mesh)

        if all_segments:
            # Concatenate all segment meshes
            # Ensure all segments are valid meshes before concatenating
            valid_segments = [seg for seg in all_segments if seg.vertices.shape[0] > 0 and seg.faces.shape[0] > 0]
            if valid_segments:
                 self._mesh = trimesh.util.concatenate(valid_segments)
            else:
                 self._mesh = trimesh.Trimesh() # No valid segments created
        else:
            self._mesh = trimesh.Trimesh() # No segments created

        self._is_built = True

    def get_mesh(self) -> trimesh.Trimesh:
        """
        Returns the built Trimesh object. Builds the mesh if it's not already built
        or if new contours have been added since the last build.
        """
        if not self._is_built:
            self.build_mesh()
        
        # Post-process the concatenated mesh to close seams and fix topology
        if self._mesh and self._mesh.vertices.shape[0] > 0 and self._mesh.faces.shape[0] > 0:
            logger.debug(f"Mesh before internal processing: {self._mesh.vertices.shape[0]} vertices, {self._mesh.faces.shape[0]} faces. Watertight: {self._mesh.is_watertight}")
            
            self._mesh.merge_vertices()
            logger.debug(f"Mesh after merge_vertices: {self._mesh.vertices.shape[0]} vertices, {self._mesh.faces.shape[0]} faces. Watertight: {self._mesh.is_watertight}")

            if not self._mesh.is_watertight:
                logger.info("Mesh not watertight after merging vertices, attempting to fill holes.")
                trimesh.repair.fill_holes(self._mesh) 
                logger.debug(f"Mesh after fill_holes: Watertight: {self._mesh.is_watertight}")

            self._mesh.fix_normals()
            logger.debug(f"Mesh after fix_normals: Watertight: {self._mesh.is_watertight}")
            
        return self._mesh

    def clear_contours(self):
        """
        Clears all added contours and resets the mesh.
        """
        self._contours = {}
        self._mesh = trimesh.Trimesh()
        self._is_built = False

    def get_z_levels(self) -> List[float]:
        """
        Returns the z-levels of the added contours, sorted.
        """
        return sorted(self._contours.keys())

    # def get_contour(self, z_level: float) -> Union[np.ndarray, None]:
    #     """
    #     Returns the contour (as a numpy array) at the specified z_level.
    #     Returns None if no contour exists at that z-level.
    #     """
    #     return self._contours.get(z_level)
    

def _resample_contour2(contour: np.ndarray) -> np.ndarray:
    """
    Resamples a 2D contour by subdividing segments longer than the
    average segment length of the input contour.

    This function aims to make segment lengths more uniform by adding points
    to longer segments. The total number of points in the output contour
    will be greater than or equal to the number of points in the input contour.

    Args:
        contour: A numpy array of shape (N, 2) representing the 2D contour points.

    Returns:
        A numpy array of shape (M, 2) representing the resampled contour,
        where M >= N.
    """
    num_original_points = len(contour)

    if num_original_points < 2:
        # Not enough points to form segments or define an average
        return contour.copy()

    # Calculate all segment lengths for the closed contour
    # np.vstack appends contour[0] to the end to close the loop for segment calculation
    closed_contour_for_segments = np.vstack([contour, contour[0]])
    segment_vectors = np.diff(closed_contour_for_segments, axis=0)
    segment_lengths = np.linalg.norm(segment_vectors, axis=1)

    # Calculate average segment length, considering only non-negligible segments
    # Use a small epsilon to avoid issues with floating point precision for "zero" length
    epsilon = 1e-9
    valid_segment_lengths = segment_lengths[segment_lengths > epsilon]

    if len(valid_segment_lengths) == 0:
        # All segments are zero or near-zero length (e.g., all points coincident)
        return contour.copy()
    
    avg_segment_length = np.mean(valid_segment_lengths)

    if avg_segment_length < epsilon:
        # Average segment length is effectively zero, no meaningful subdivision possible
        return contour.copy()

    new_points_list = []
    for i in range(num_original_points):
        p_start = contour[i]
        # For the last point, p_end is the first point of the contour
        p_end = contour[(i + 1) % num_original_points]

        new_points_list.append(p_start)

        current_segment_vector = p_end - p_start
        current_segment_length = np.linalg.norm(current_segment_vector)

        # If the current segment is longer than the average, subdivide it
        if current_segment_length > avg_segment_length:
            # Determine how many sub-segments are needed to get lengths approx. avg_segment_length
            num_sub_segments = int(np.ceil(current_segment_length / avg_segment_length))
            
            if num_sub_segments > 1: # Ensure at least two sub-segments (i.e., at least one new point)
                for k in range(1, num_sub_segments): # k from 1 up to num_sub_segments-1
                    fraction = k / float(num_sub_segments)
                    intermediate_point = p_start + fraction * current_segment_vector
                    new_points_list.append(intermediate_point)
    
    if not new_points_list: # Should not happen if num_original_points >=1
        return contour.copy()

    return np.array(new_points_list)

# local utility
def _get_int_ext(shp):

    if is_convex_dist(shp):
        extc = np.array(shp.exterior.xy).T.astype(int)
        intc = None
        if shp.interiors:
        # if len(shp.interiors)>0:
            intc = np.vstack([np.array(elt.xy).T.astype(int) for elt in shp.interiors])
    else:
        extc, intc = make_interior_exterior(shp)

    return extc, intc

def _get_int_ext2(shp: shapely.Geometry):
    """
    Alternative to _get_int_ext that returns exterior and interior contours
    as float coordinates, without casting to int.
    """
    extc = None
    intc = None
    if is_convex_dist(shp):
        extc = np.array(shp.exterior.xy).T # Keep as float
        if shp.interiors:
            intc = np.vstack([np.array(elt.xy).T for elt in shp.interiors]) # Keep as float
    else:
        # make_interior_exterior already returns float coordinates from alphashape
        extc, intc = make_interior_exterior2(shp)

    return extc, intc

#%% - for method 1++ - attempt filling the gaps by interpolating unannotated section positions

def morph_shape(fromshape_in, toshape_in, fromnum, tonum, internum, mpp):
    fromshape = get_valid_shape(fromshape_in)
    
    toshape = get_valid_shape(toshape_in)

    ext_from, int_from = _get_int_ext(fromshape)
    ext_to, int_to  = _get_int_ext(toshape)

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

#%% for method 2

def create_mesh_from_AnnotationSet(
    shapes_by_secnum: 'AnnotationSet', 
    mpp: float,
    section_thickness_microns: float = 60.0
) -> Tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """
    Creates a 3D mesh from a dictionary of Shapely geometries representing
    a single ontological region across multiple sections.
    Holes are created in the mesh based on interior contours.

    Args:
        shapes_by_secnum: A dictionary mapping section number (int) to
                          a dict ontoid:Shapely Geometry 
                          It's assumed this is for a single ontoid.
                          This is produced by annotation_handling.py:AnnotationManager.get_annotations_by_ontoid, with merge_children=True
        mpp: Microns per pixel for x and y dimensions.
        section_thickness_microns: Thickness of each section in microns (z-dimension).

    Returns:
        A tuple containing:
        - The final trimesh.Trimesh object, potentially with holes.
        - A dictionary mapping section number to the original extracted interior
          contour in pixel coordinates (np.ndarray or None).
    """
    # mpp for ContourSequenceMesher will be 1.0 as we pass micron-scaled contours to it.
    # The mpp for morph_contour (used by ContourSequenceMesher) is critical.
    # We assume morph_contour and its boundarymask are robust to handle micron-scale coordinates
    # by adapting to contour bounds rather than fixed-size masks scaled by its mpp argument.
    exterior_mesher = ContourSequenceMesher(mpp, section_thickness_microns) #=1.0)
    hole_volume_mesher = ContourSequenceMesher(mpp, section_thickness_microns) #=1.0)

    # To store original interior contours in pixel coordinates for the return value
    # returned_interior_contours_pixels: Dict[int, Union[np.ndarray, None]] = {}
    # To store interior contours in micron coordinates for hole meshing
    # collected_interior_contours_microns: Dict[float, np.ndarray] = {}

    sorted_secnums = sorted(shapes_by_secnum.keys())

    for secnum in sorted_secnums:
        assert len(shapes_by_secnum[secnum])==1, 'merge_children needs to be done before passing here'
        for ontoid, shape in shapes_by_secnum[secnum].items():
            break
        # z_microns = float(secnum * section_thickness_microns)
        
        if shape is None or shape.is_empty:
            logger.info(f"Shape for section {secnum} is None or empty. Skipping.")
            # returned_interior_contours_pixels[secnum] = None
            continue

        polyshapes = []
        if shape.geom_type=="Polygon":
            polyshapes=[shape]
        elif shape.geom_type=="MultiPolygon":
            polyshapes=shape.geoms

        for shape in polyshapes:
            # _get_int_ext returns contours in pixel coordinates
            extc_pixels, intc_pixels = _get_int_ext2(shape)

            if extc_pixels is not None:
                if extc_pixels.ndim == 2 and extc_pixels.shape[1] == 2:
                    # extc_microns = extc_pixels.astype(float) * mpp
                    # logger.debug(f"  Section {secnum}: Adding exterior contour ({extc_microns.shape[0]} pts) at z={z_microns:.2f} um.")
                    exterior_mesher.add_contour(extc_pixels, secnum)
                # else:
                #     logger.warning(f"  Exterior contour for section {secnum} has unexpected pixel shape: {extc_pixels.shape}. Skipping.")
            # else:
            #     logger.warning(f"  No valid exterior contour extracted for section {secnum}.")

            # returned_interior_contours_pixels[secnum] = intc_pixels # Store original pixel version
            if intc_pixels is not None:
                if intc_pixels.ndim == 2 and intc_pixels.shape[1] == 2:
                    # intc_microns = intc_pixels.astype(float) * mpp
                    # logger.debug(f"  Section {secnum}: Collecting interior contour ({intc_microns.shape[0]} pts) at z={z_microns:.2f} um for hole.")
                    # For hole_volume_mesher, add directly if you want to use its morphing.
                    hole_volume_mesher.add_contour(intc_pixels, secnum)
                # else:
                #     logger.warning(f"  Interior contour for section {secnum} has unexpected pixel shape: {intc_pixels.shape}. Skipping.")
            # else:
            #     logger.debug(f"  Section {secnum}: No interior contour found.")

    logger.info("Building main exterior mesh.")
    main_mesh = exterior_mesher.get_mesh()

    # if not (main_mesh and main_mesh.vertices.shape[0] > 0 and main_mesh.faces.shape[0] > 0):
    #     logger.warning("Main exterior mesh is empty or invalid. Cannot create holes.")
    #     return trimesh.Trimesh(), returned_interior_contours_pixels

    logger.info("Building combined hole volume mesh.")
    combined_hole_mesh = hole_volume_mesher.get_mesh()

    return main_mesh, combined_hole_mesh

#%% for later

def mesh_join(main_mesh, combined_hole_mesh):
    final_mesh = main_mesh

    if combined_hole_mesh and combined_hole_mesh.vertices.shape[0] > 0 and combined_hole_mesh.faces.shape[0] > 0:
        logger.info(f"Combined hole mesh generated with {combined_hole_mesh.vertices.shape[0]} vertices, {combined_hole_mesh.faces.shape[0]} faces.")
        if not combined_hole_mesh.is_watertight:
            logger.info("Combined hole mesh is not watertight. Attempting to fill holes to make it a solid volume.")
            try:
                combined_hole_mesh.fill_holes()
                if combined_hole_mesh.is_watertight:
                    logger.info("Combined hole mesh successfully made watertight by fill_holes().")
                else:
                    # It's possible fill_holes() doesn't make it watertight if boundaries are complex or self-intersecting
                    logger.warning("Combined hole mesh still not watertight after fill_holes(). Boolean difference might be unreliable.")
            except Exception as e:
                logger.error(f"Error during combined_hole_mesh.fill_holes(): {e}. Proceeding with potentially non-watertight hole mesh.")

        logger.info("Performing boolean difference to create holes in the main mesh.")
        try:
            # Ensure main_mesh is processed for robustness in boolean operations
            if not main_mesh.is_watertight:
                logger.warning("Main mesh is not watertight before boolean operation. Attempting to repair.")
                main_mesh.process() # process() tries to make it valid, including fill_holes
                if not main_mesh.is_watertight:
                    logger.error("Main mesh could not be made watertight. Boolean difference is likely to fail or produce incorrect results.")
            
            # Proceed with difference if both meshes seem reasonable (especially the main one)
            if main_mesh.is_watertight: # Crucial for the minuend
                final_mesh = main_mesh.difference(combined_hole_mesh, engine='blender') # 'blender' or 'scad'
                logger.info("Boolean difference operation complete.")
                if not (final_mesh and final_mesh.vertices.shape[0] > 0 and final_mesh.faces.shape[0] > 0):
                    logger.warning("Boolean difference resulted in an empty or invalid mesh. Reverting to the main mesh without holes.")
                    final_mesh = main_mesh
            else:
                logger.warning("Skipping boolean difference as the main mesh is not watertight.")
                final_mesh = main_mesh

        except Exception as e:
            logger.error(f"Boolean difference failed: {e}. Returning main mesh without holes.")
            final_mesh = main_mesh
    else:
        logger.info("No interior contours processed into a hole mesh, or hole mesh is empty. Returning main exterior mesh.")

    return final_mesh #, returned_interior_contours_pixels
