from collections import defaultdict
import shapely
import numpy as np
from ontology_handling import TreeHelper
from typing import Dict, List

Annotation = Dict[int,shapely.Geometry]

def get_longest_side_line(shape:shapely.Geometry, side='right'):

    mrr = shape.minimum_rotated_rectangle
    if isinstance(mrr, shapely.Polygon):
        mbr_points = list(zip(*mrr.exterior.coords.xy))
        mbr_lines = [shapely.LineString((mbr_points[i], mbr_points[i + 1])) for i in range(len(mbr_points) - 1)]
        mbr_line_lengths = [line.length for line in mbr_lines]
        lineidx = np.argmax(mbr_line_lengths)

        short_length = mbr_line_lengths[(lineidx + 1) % 4]

        p1, p2 = mbr_points[lineidx], mbr_points[lineidx + 1]
        p1a, p2a = mbr_points[(lineidx + 2) % 4], mbr_points[(lineidx + 3) % 4]

        if (side == 'right' and max(p1a[0], p2a[0]) > max(p1[0], p2[0])) or (side == 'left' and min(p1a[0], p2a[0]) < min(p1[0], p2[0])):
            return p1a, p2a, short_length

        return p1, p2, short_length
    return None, None, 0    


def _line_orientation(p1, p2):
    return np.arctan2(p2[1] - p1[1], p2[0] - p1[0]) * 180 / np.pi
    
def shape_orientation(shape:shapely.Geometry):
    p1, p2, _ = get_longest_side_line(shape)
    if p1 is not None:
        if p1[0] > p2[0]:
            return _line_orientation(p2, p1)
        else:
            return _line_orientation(p1, p2)
    return 0


def get_adjacency(annot:'Annotation'):
    edges = {'touches':[], 'crosses':[], 'intersects':[], 'overlaps':[]}
    for onto_i in annot:
        for onto_j in annot:
            if onto_i==onto_j:
                continue
            if annot[onto_i].touches(annot[onto_j]):
                edges['touches'].append((onto_i,onto_j))
            if annot[onto_i].crosses(annot[onto_j]):
                edges['crosses'].append((onto_i,onto_j))
            if annot[onto_i].intersects(annot[onto_j]):
                edges['intersects'].append((onto_i,onto_j))
            if annot[onto_i].overlaps(annot[onto_j]):
                edges['overlaps'].append((onto_i,onto_j))    
                
    return edges


def get_properties(shape:shapely.Geometry):
    return {
        'pt': shape.representative_point(),
        'area': shape.area,
        'perimeter': shape.length,
        'numcomp': len(shape.geoms),
        'obb': shape.minimum_rotated_rectangle,
        'majoraxis': get_longest_side_line(shape)[:2],
        'smallestwidth': 0, # FIXME: this should help to find at what zoom the structure will start to dissolve
    }


def nearest_shape(shp:shapely.Geometry,otherlist:List[shapely.Geometry]):
    distances = [shapely.hausdorff_distance(shp,other) for other in otherlist]
    if len(distances)==0:
        return None, np.inf
    minidx = np.argmin(distances)
    dv = distances[minidx]
    nr = otherlist[minidx]
    minx,miny,maxx,maxy=nr.bounds
    width = max((maxx-minx),(maxy-miny))
    if dv > width:
        return None, np.inf

    minx,miny,maxx,maxy=shp.bounds
    width = max((maxx-minx),(maxy-miny))
    if dv > width:
        return None, np.inf
    return nr, dv


def get_level_ids(annot:'Annotation', ontohelper:'TreeHelper'):
    
    level_ids = defaultdict(list) # level:[ids]

    for ontoid in annot:
        rec = ontohelper.onto_lookup[ontoid]
        level_ids[rec.level].append(ontoid)
    
    return level_ids


def get_reachable_parents(annot:'Annotation', ontohelper:'TreeHelper'):
    reachable1 = defaultdict(list) # parent: [annotated]
    reachable2 = defaultdict(list) # parent: [aggregatable]

    for ontoid in annot:
        
        par = ontohelper.onto_lookup[ontoid].parentid
        if ontoid not in reachable1[par]:
            reachable1[par].append(ontoid)

        anclist = list(reversed(ontohelper.get_ancestor_ids(ontoid)))
        oid = par # same as anclist[0]
        for ii in range(1,len(anclist)): 
            par = anclist[ii]
            if oid not in reachable2[par] and oid not in annot:
                reachable2[par].append(oid)
            oid = par

    reachable = {}
    for k in reachable1:
        reachable[k]=[reachable1[k],[]]

    for k in reachable2:
        if k in reachable:
            reachable[k][1]=reachable2[k]
        else:
            reachable[k]=[[],reachable2[k]]

    return reachable

def get_nonreachable(annot:'Annotation', ontohelper:'TreeHelper'):

    reachable = defaultdict(list) # anc: [successors]

    for ontoid in annot:
        anclist = ontohelper.get_ancestor_ids(ontoid)
        for anc in reversed(anclist):
            reachable[anc].append(ontoid)
    
    nonreachable = []
    for ontoid,rec in ontohelper.onto_lookup.items():
        if ontoid not in reachable and ontoid not in annot:
            nonreachable.append(ontoid)

    # organize as parent:[children]
    nrdict = defaultdict(list)
    leaves = []    
    for oid in nonreachable:
        parentid = ontohelper.onto_lookup[oid].parentid
        
        if parentid in nonreachable:
            nrdict[parentid].append(oid)
        else:
            leaves.append(oid)
    return nrdict, leaves


def get_supershape(ontoid:int, annot:'Annotation', ontohelper:'TreeHelper'):
    #  construct parent shapes by merging shapes 

    if ontoid in annot:
        return annot[ontoid]
    
    parshp = None
    chlist = []
    for annot_id in annot:
        anclist = ontohelper.get_ancestor_ids(annot_id)
        if ontoid in anclist:
            chlist.append(annot_id)
            if parshp is None:
                parshp = annot[annot_id]
            else:
                parshp = parshp.union(annot[annot_id])
    
    return parshp, chlist

def find_superids(annot:'Annotation',ontohelper:'TreeHelper'):

    superids = defaultdict(list)

    for ontoid in annot:
        parentids = ontohelper.get_ancestor_ids(ontoid)
        
        for drawnid in annot:
            if drawnid in parentids:
                superids[drawnid].append(ontoid)

    return superids
    
    