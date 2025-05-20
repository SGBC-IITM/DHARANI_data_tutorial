
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
        mpp: Microns per pixel, used for boundarymask size.
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
    assert internum > fromnum and internum < tonum
    
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

    if swapped:
        pairs_fixed = [(pairpt,pt) for pt, pairpt in pairs]
    else:
        pairs_fixed = pairs
    return np.array(newpts), pairs_fixed, widthlist


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

from typing import List, Tuple, Union

def create_surface_between_contours(
    point_pairs: List[Tuple[Union[np.ndarray, List[float]], Union[np.ndarray, List[float]]]],
    z_for_first_points: float,
    z_for_second_points: float
) -> trimesh.Trimesh:
    """
    Creates a 3D surface (Trimesh) between two contours that have point-wise correspondences.
    This function effectively "skins" the two contours to form a tube-like structure.

    Args:
        point_pairs: A list of tuples, where each tuple (p1, p2) contains
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
    if not point_pairs or len(point_pairs) < 2:
        # Not enough points/pairs to form a surface
        return trimesh.Trimesh()

    vertices = []
    for p1, p2 in point_pairs:
        vertices.append([p1[0], p1[1], z_for_first_points])
        vertices.append([p2[0], p2[1], z_for_second_points])
    
    vertices_np = np.array(vertices, dtype=float)

    faces = []
    num_correspondences = len(point_pairs)

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

class ContourSequenceMesher:
    """
    Accumulates a sequence of 2D contours at different z-levels and builds
    a 3D surface mesh by skinning between consecutive contours.

    The mesh is built incrementally between each pair of consecutive contours
    in the sequence, sorted by z-level.
    """

    def __init__(self, mpp: float):
        """
        Initializes the mesher.

        Args:
            mpp: Microns per pixel, used by the morphing function.
        """
        self._mpp = mpp
        # Store contours as numpy arrays of points, keyed by z_level
        # Using float for z_level keys to handle potential non-integer section numbers
        self._contours: Dict[int, np.ndarray] = {}
        self._mesh: trimesh.Trimesh = trimesh.Trimesh() # Start with an empty mesh
        self._is_built = False # Flag to track if the mesh needs rebuilding

    def add_contour(self, contour:  np.ndarray, z_level: int):
        """
        Adds a contour at a specific z-level to the sequence.

        Adding a contour invalidates the current mesh, requiring a rebuild
        via `build_mesh()` or `get_mesh()`.

        Args:
            contour: The 2D contour. Can be a Shapely Polygon, a numpy array
                     of points (N, 2), or a list of (x, y) tuples.
                     If a Shapely Polygon, only the exterior boundary is used.
            z_level: The z-coordinate for this contour.
        """
        
        # Store points. morph_contour's boundarymask expects int, but morph_contour
        # itself seems to handle float input and returns float pairs.
        # Let's store as float and ensure morph_contour handles it.
        # If morph_contour truly requires int input, we'd convert here.
        # Based on the provided code, boundarymask converts to int internally.
        # So, passing float points to morph_contour should be fine.
        self._contours[z_level] = contour.astype(float) # Store as float z_level

        self._is_built = False # Mark mesh as needing rebuild

    def build_mesh(self):
        """
        Builds or rebuilds the 3D mesh from the accumulated contours.
        This method sorts contours by z-level and creates mesh segments
        between each consecutive pair.
        """
        if len(self._contours) < 2:
            logging.info("Need at least two contours to build a mesh.")
            self._mesh = trimesh.Trimesh() # Reset to empty
            self._is_built = True
            return

        sorted_z_levels = sorted(self._contours.keys())
        all_segments = []

        for i in range(len(sorted_z_levels) - 1):
            z1 = sorted_z_levels[i]
            z2 = sorted_z_levels[i+1]
            contour1_np = self._contours[z1]
            contour2_np = self._contours[z2]

            # morph_contour requires internum between fromnum and tonum.
            # The exact value doesn't affect the 'pairs' output used for skinning
            # between the original contours, as long as the swap logic is consistent.
            # Let's use the midpoint.
            # internum = z1 + (z2 - z1) / 2.0
            internum = (z1+z2)//2

            # Call morph_contour to get correspondences
            # We only need the 'pairs' output
            # Note: morph_contour expects fromcontour and tocontour as numpy arrays
            _, pairs, _ = morph_contour(contour1_np, contour2_np, z1, z2, internum, self._mpp)

            if not pairs:
                print(f"Warning: No pairs generated between z={z1} and z={z2}. Skipping segment.")
                continue

            # Determine the correct order of points in pairs for create_surface_between_contours
            # based on morph_contour's internal swap logic.
            # The swap condition from morph_contour:
            # swapped = (tonum - internum < stepnum) or (len(tocontour) > len(fromcontour))
            # where stepnum = internum - fromnum
            # So, swapped = (z2 - internum < internum - z1) or (len(contour2_np) > len(contour1_np))
            # If swapped is True, pairs are (point_from_contour2, point_from_contour1_mask)
            # If swapped is False, pairs are (point_from_contour1, point_from_contour2_mask)

            stepnum_in_morph = internum - z1
            # Replicate the swap logic from morph_contour
            swapped = (z2 - internum < stepnum_in_morph) or (len(contour2_np) > len(contour1_np))

            pairs_for_surface = pairs
            z_first = float(z1)
            z_second = float(z2)

            # Create the mesh segment between these two contours
            segment_mesh = create_surface_between_contours(
                pairs_for_surface,
                z_first,
                z_second
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
    #     Returns the contour (as a numpy array) at the specified z-level.
    #     Returns None if no contour exists at that z-level.
    #     """
    #     return self._contours.get(z_level)
    

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
            
