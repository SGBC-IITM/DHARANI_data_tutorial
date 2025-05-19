
from IPython.display import display, HTML, IFrame
from matplotlib import pyplot as plt
from shapely.plotting import plot_polygon
# import json
import shapely
import numpy as np

from typing import Dict, List
from ontology_handling import TreeHelper
from annotation_handling import get_reachable_parents, get_supershape

Annotation = Dict[int,shapely.Geometry]

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
                shp,chlist = get_supershape(ontoid, annot, ontohelper)
                superannot[ontoid]=shp

            if shp is not None:
                rec = ontohelper.onto_lookup[ontoid]
                color = rec.color_hex_triplet
                plot_shape(shp,color)

    return displayedids, superannot


def display_annotation_tree(annot:'Annotation', ontohelper:'TreeHelper', selectedlev=None, ontoids=[]):

    reachable = get_reachable_parents(annot,ontohelper)
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
