
from IPython.display import display, HTML, IFrame
from matplotlib import pyplot as plt
from shapely.plotting import plot_polygon
# import json
# import shapely
import numpy as np

from ontology_handling import TreeHelper
# from annotation_handling import get_reachable_parents, get_supershape
from annotation_handling import AnnotationManager

# Annotation = Dict[int,shapely.Geometry]

def _get_print_rec(ontoid, rec, prefix=''):    
    outstr="".join(['&emsp;']*rec.level)+f'{prefix} {ontoid} {rec.acronym} {rec.name} {rec.level} '
    if len(prefix)==0 or prefix[:2]=='(+':
        return f'<p>{outstr}<span style="display:inline-block;width:20px;height:12px;padding:0px;background-color:{rec.color_hex_triplet};"></span></p>'
    else:
        return f'<p>{outstr}</p>'


def plot_shape(shp,color):
    plot_polygon(shp, add_points=False, facecolor=color, edgecolor='k')

def display_shape(im_arr, shp, color):
    plt.figure(figsize=(12,8))
    plt.subplot(1,2,1)
    plt.imshow(im_arr)
    
    plt.subplot(1,2,2)
    plt.imshow(im_arr)
    plot_shape(shp,color)


def display_annotation(im_arr, annot:'Annotation', ontohelper:'TreeHelper', selectedlev=None, ontoids=[], showtree=True, axislimit=[]):
    
    if showtree:
        display_annotation_tree(annot, ontohelper, selectedlev, ontoids)

    plt.figure(figsize=(12,8))
    nplots = 2
    if len(ontoids)>0:
        nplots = 3

    plt.subplot(1,nplots,1)
    plt.imshow(im_arr)
    if len(axislimit)==4:
        plt.axis(axislimit)
    
    plt.subplot(1,nplots,2)
    plt.imshow(im_arr)
    if len(axislimit)==4:
        plt.axis(axislimit)
    
    displayedids = []
    superannot = {}

    for ontoid,shp in sorted(annot.items()):
        rec = ontohelper.onto_lookup[ontoid]

        if selectedlev is None or rec.level == selectedlev or\
              ontoid in ontoids or rec.parentid in ontoids:
            color = rec.color_hex_triplet
            plot_shape(shp,color)
            displayedids.append(ontoid)

    if nplots>2:
        plt.subplot(1,nplots,3)
        plt.imshow(im_arr)
        if len(axislimit)==4:
            plt.axis(axislimit)

        for ontoid in ontoids:
            if ontoid in annot:
                shp = annot[ontoid]
                
            else:
                mgr = AnnotationManager(ontohelper)
                shp,chlist = mgr.get_supershape(ontoid, annot)
                superannot[ontoid]=shp

            if shp is not None:
                rec = ontohelper.onto_lookup[ontoid]
                color = rec.color_hex_triplet
                plot_shape(shp,color)

    return displayedids, superannot


def display_annotation_tree(annot:'Annotation', ontohelper:'TreeHelper', selectedlev=None, ontoids=[]):
    mgr = AnnotationManager(ontohelper)
    reachable = mgr.get_reachable_parents(annot)
    outstr = ''
    for par in reachable:
        parrec = None
        if par>0:
            parrec = ontohelper.onto_lookup[par]
        if selectedlev is not None:
            if parrec is None:
                continue
            if parrec.level!=selectedlev-1 and parrec.level!=selectedlev:
                continue
            
        ann = reachable[par][0]
        if len(ann)>0:
            _, fullacro, _, _ = ontohelper.get_full_name_by_ontoid(par)
            if selectedlev is not None:
                if parrec is not None:
                    if parrec.level==selectedlev:
                        outstr+=_get_print_rec(par, parrec, f'(+{len(ann)}) {fullacro}')
                    else:  
                        outstr+=_get_print_rec(par, parrec, '#'+fullacro)
            else:
                if parrec is not None:
                    outstr+=_get_print_rec(par, parrec, '#'+fullacro)

            for oid in ann:
                rec = ontohelper.onto_lookup[oid]
                
                if par in ontoids or selectedlev is None or rec.level==selectedlev:
                    outstr+=_get_print_rec(oid,rec)
                
    display(HTML(
        '<div style="width: 90%; height: 300px; overflow-y: scroll; border: 1px solid black; padding: 10px;">'+
        outstr+'</div>'))



# a utility function, to grid the page to match tiling


def display_tiling_grid(thumbnailimg, pageinfo=None):
    plt.imshow(thumbnailimg, extent=[0,pageinfo['imagewidth'], pageinfo['imageheight'], 0])
    if pageinfo is not None:
        nr,nc,_ = thumbnailimg.shape
        xrange = np.arange(0,pageinfo['imagewidth']/nc+1,pageinfo['tilewidth']/nc)
        yrange = np.arange(0,pageinfo['imageheight']/nr+1,pageinfo['tilelength']/nr)
        
        plt.xticks(xrange*nc)
        plt.yticks(yrange*nr)
        plt.grid(True)


from mpl_toolkits.mplot3d import Axes3D

import trimesh # Assuming your mesh object is of this type

def display_mesh_wireframe(mesh_to_display: trimesh.Trimesh):
    """
    Displays a Trimesh object as a wireframe plot using Matplotlib.
    """
    if not isinstance(mesh_to_display, trimesh.Trimesh) or \
       mesh_to_display.vertices.shape[0] == 0 or \
       mesh_to_display.edges.shape[0] == 0:
        print("Invalid or empty mesh provided.")
        return

    # Get the unique edges of the mesh
    # mesh.edges_unique returns pairs of vertex indices
    # mesh.vertices[mesh.edges_unique] gives pairs of 3D coordinates for each edge
    edge_vertices = mesh_to_display.vertices[mesh_to_display.edges_unique]

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    for edge in edge_vertices:
        # Each 'edge' is a pair of 3D points (start_point, end_point)
        # edge[0] is the start vertex [x, y, z]
        # edge[1] is the end vertex [x, y, z]
        ax.plot3D(*zip(*edge), color="b") # Unpack points for plot3D

    # Set plot limits to encompass the mesh
    min_bounds = mesh_to_display.bounds[0]
    max_bounds = mesh_to_display.bounds[1]
    ax.set_xlim([min_bounds[0], max_bounds[0]])
    ax.set_ylim([min_bounds[1], max_bounds[1]])
    ax.set_zlim([min_bounds[2], max_bounds[2]])
    
    # Ensure equal aspect ratio for a more accurate representation
    # This can be tricky with matplotlib 3D but here's an attempt
    all_ranges = np.array([ax.get_xlim(), ax.get_ylim(), ax.get_zlim()])
    centers = np.mean(all_ranges, axis=1)
    max_range = np.max(np.abs(all_ranges[:, 1] - all_ranges[:, 0])) / 2.0
    ax.set_xlim(centers[0] - max_range, centers[0] + max_range)
    ax.set_ylim(centers[1] - max_range, centers[1] + max_range)
    ax.set_zlim(centers[2] - max_range, centers[2] + max_range)

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    plt.title("Mesh Wireframe")
    plt.show()

# Example usage (assuming 'your_mesh' is your trimesh.Trimesh object):
# display_mesh_wireframe(your_mesh)
