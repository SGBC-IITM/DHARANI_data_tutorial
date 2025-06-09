
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
    
    pairs = []
    widthlist = []
    newpts = []
    
    for pt in srcpts:
        
        pairpt = distidx[:,int(round(pt[1])),int(round(pt[0]))].T.squeeze()[::-1].tolist() # maintain x,y notation
        
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
    
    del dstmsk
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

    def add_contour(self, contour:  np.ndarray, z_level: int):
        """
        Adds a contour at a specific z-level to the sequence.

        Adding a contour invalidates the current mesh, requiring a rebuild
        via `build_mesh()` or `get_mesh()`.

        Args:
            contour: The 2D contour. A numpy array of points (N, 2).
            z_level: The z-coordinate for this contour (secnum).
        """
        
        # Store points. morph_contour's boundarymask expects int, but morph_contour
        # itself seems to handle float input and returns float pairs.
        # Let's store as float and ensure morph_contour handles it.
        # If morph_contour truly requires int input, we'd convert here.
        # Based on the provided code, boundarymask converts to int internally.
        # So, passing float points to morph_contour should be fine.
        self._contours[z_level] = contour.astype(float)

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

        medgap = np.median(np.diff(sorted_z_levels))

        for i in range(len(sorted_z_levels) - 1):
            z1 = sorted_z_levels[i]
            z2 = sorted_z_levels[i+1]
            contour1_orig = self._contours[z1]
            contour2_orig = self._contours[z2]
    
            if z2-z1 > 2*medgap:
                logging.warning(f"Gap between z={z1} and z={z2} is larger than 2*median {medgap}.")
                continue

            # Determine a consistent number of points for resampling
            # Using max length ensures detail isn't lost from the denser contour,
            # but could be a fixed number too.
            num_resample_points = max(len(contour1_orig), len(contour2_orig))
            if num_resample_points < 3: # Need at least 3 points for a polygon/morphing
                logging.warning(f"Contours between z={z1} and z={z2} have too few points ({num_resample_points}) for resampling. Skipping segment.")
                continue
            contour1_resampled = _resample_contour(contour1_orig, num_resample_points)
            contour2_resampled = _resample_contour(contour2_orig, num_resample_points)

            # morph_contour requires internum between fromnum and tonum.
            # The exact value doesn't affect the 'pairs' output used for skinning
            # between the original contours, as long as the swap logic is consistent.
            # Let's use the midpoint.
            # internum = z1 + (z2 - z1) / 2.0
            internum = (z1+z2)//2

            # Call morph_contour to get correspondences
            # We only need the 'pairs' output
            # Note: morph_contour expects fromcontour and tocontour as numpy arrays
            _, pairs, _ = morph_contour(contour1_resampled, contour2_resampled, z1, z2, internum, self._mpp)

            if not pairs:
                logging.warning(f"No pairs generated between z={z1} and z={z2}. Skipping segment.")
                continue

            # Determine the correct order of points in pairs for create_surface_between_contours
            # based on morph_contour's internal swap logic.
            # The swap condition from morph_contour:
            # swapped = (tonum - internum < stepnum) or (len(tocontour) > len(fromcontour))
            # where stepnum = internum - fromnum
            # So, swapped = (z2 - internum < internum - z1) or (len(contour2_np) > len(contour1_np))
            # If swapped is True, pairs are (point_from_contour2, point_from_contour1_mask)
            # If swapped is False, pairs are (point_from_contour1, point_from_contour2_mask)

            # stepnum_in_morph = internum - z1
            # Replicate the swap logic from morph_contour
            # swapped = (z2 - internum < stepnum_in_morph) or (len(contour2_np) > len(contour1_np))

            pairs_for_surface = pairs
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
            extc_pixels, intc_pixels = _get_int_ext(shape)

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
