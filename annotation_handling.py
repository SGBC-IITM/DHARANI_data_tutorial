from collections import defaultdict
import shapely
import shapely.ops
import numpy as np
from ontology_handling import TreeHelper

import logging

from joblib import Parallel, delayed


logger = logging.getLogger(__name__)

#%% type alias and hints

from typing import Dict, List, Optional

# shape :- a 2d annotation, possibly MultiPolygon

Annotations = Dict[int,shapely.Geometry] # ontoid: shape 
    # this is a container for annotations of a section

AnnotationSet = Dict[int, Annotations] # secnum: {ontoid:shape}
    # this is a collection of annotations across multiple sections

from dharani_functions import DharaniHelper
from allen_functions import AllenHelper

#%% Geometry handling 

def get_longest_side_line(shape:shapely.Geometry, side='right'):

    mrr = shape.minimum_rotated_rectangle
    if isinstance(mrr, shapely.Polygon):
        mbr_points = list(zip(*mrr.exterior.coords.xy))
        mbr_lines = [shapely.LineString((mbr_points[i], mbr_points[i + 1])) for i in range(len(mbr_points) - 1)]
        mbr_line_lengths = [line.length for line in mbr_lines]
        lineidx = np.argmax(mbr_line_lengths)

        long_length = mbr_line_lengths[lineidx]
        short_length = mbr_line_lengths[(lineidx + 1) % 4]

        p1, p2 = mbr_points[lineidx], mbr_points[lineidx + 1]
        p1a, p2a = mbr_points[(lineidx + 2) % 4], mbr_points[(lineidx + 3) % 4]

        if (side == 'right' and max(p1a[0], p2a[0]) > max(p1[0], p2[0])) or (side == 'left' and min(p1a[0], p2a[0]) < min(p1[0], p2[0])):
            return p1a, p2a, long_length, short_length

        return p1, p2, long_length, short_length
    return None, None, 0 ,0   


def _line_orientation(p1, p2):
    return np.arctan2(p2[1] - p1[1], p2[0] - p1[0]) * 180 / np.pi
    
def shape_orientation(shape:shapely.Geometry):
    p1, p2, long_length, short_length = get_longest_side_line(shape)
    if p1 is not None:
        if p1[0] > p2[0]:
            return _line_orientation(p2, p1)
        else:
            return _line_orientation(p1, p2)
    return 0

def get_max_width(shape:shapely.Geometry):
    # find largest incircle
    center = shape.representative_point()
    radius = shape.boundary.distance(center)
    
    return 2*radius

def get_properties(shape:shapely.Geometry):

    num_comp = 1
    if shape.geom_type=='MultiPolygon':
        num_comp = len(shape.geoms)

    p1,p2, long_length, short_length = get_longest_side_line(shape)

    ori = None
    if p1 is not None:
        if p1[0] > p2[0]:
            ori = _line_orientation(p2, p1)
        else:
            ori = _line_orientation(p1, p2)
    
    return {
        'pt': shape.representative_point().coords[0],
        'area': shape.area, # in sq pixel units (need to convert to sq.micron by multiplying mpp*mpp)
        'perimeter': shape.length, # in pixel units
        'numcomp': num_comp,
        'bbox': shape.bounds,
        'aspectratio': long_length/short_length,
        'obb': shape.minimum_rotated_rectangle,
        'majoraxislength': long_length, # in pixel units
        'minoraxislength': short_length, # in pixel units
        'maxwidth': get_max_width(shape),  # in pixel units
        'orientation': ori,         # positive clockwise
    }

#%% 2d annotation relationships

def get_adjacency(annot:'Annotations'):
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

#%% 

def _remove_small_interiors(shp:shapely.Geometry):
    if shp.geom_type=='MultiPolygon':
        polylist = shp.geoms
    else:
        polylist = [shp]

    clean_polylist = []
    for poly in polylist:
        clean_interiors = []
        for ring_i in poly.interiors:
            rlen = ring_i.length
            ar = shapely.Polygon(ring_i).area
            if rlen/ar>150: #XXX: MAGIC
                continue
            if rlen>10 and ar>10:
                clean_interiors.append(ring_i)

        clean_poly = shapely.Polygon(shell=poly.exterior, holes=clean_interiors)
        clean_polylist.append(clean_poly)
    
    if len(clean_polylist)>1:
        return shapely.MultiPolygon(clean_polylist)
    else:
        return clean_polylist[0]





class AnnotationManager:
    """
    Manages annotations obtained from a source (e.g., DharaniHelper) and
    provides methods to retrieve them, potentially by aggregating successor ontoids.
    """

    def __init__(self,
                 tree_helper: TreeHelper):
        """
        Initializes the AnnotationManager.

        Args:
            tree_helper: An instance of TreeHelper to resolve ontology relationships.
        """
        self.annotations_data:Dict[int,'Annotations'] = {} # secno:{ontoid:shape}
        self.tree_helper: TreeHelper = tree_helper
        
    def __len__(self):
        return len(self.annotations_data)
    
    def load_annotations_from_helper(self, helperobj:'DharaniHelper|AllenHelper', concurrent=False):
        # was dharani_functions.py:DharaniHelper.def get_annotations(self, concurrent=False):
        """
        returns all annotations as dict where
        keys are ontoids, values are dict of secno:shapely.Geometry
        """
        assert len(self)==0, "can't load more than once"
        # secnos = self.get_section_numbers()
        filenamedict = helperobj.get_filenames()
        secnos = [int(key) for key in filenamedict if 'annotation' in filenamedict[key]]

        # outdict = defaultdict(dict)

        def workerfunc(secnum):
            try:
                annot_seci = helperobj.get_annotation(secnum)
                return secnum, annot_seci
            except:
                logger.error(f'ERR: sec {secnum}')
                return secnum, {}

        if not concurrent:
            for secnum in secnos:
                secnum, annot_seci = workerfunc(secnum)
                self.annotations_data[secnum]=annot_seci
                # for ontoid,shp in annot_seci.items():
                #     outdict[ontoid][secnum]=shp
                
        else:
            with Parallel(n_jobs=4) as executor:
                results = executor(
                    delayed(workerfunc)(secnum) for secnum in secnos
                )
                for secnum, annot_seci in results:
                    self.annotations_data[secnum]=annot_seci
                    # for ontoid,shp in annot_seci.items():
                    #     outdict[ontoid][secnum]=shp
                    
        self.all_sections: List[int] = sorted(list(self.annotations_data.keys()))
        # return dict(outdict)
    
    def get_annotations_by_ontoid(
        self,
        ontoid: int,
        merge_children=True,
    ) -> 'AnnotationSet':
        """
        Retrieves annotations for a given ontoid across all available sections.

        If the ontoid is not directly available and `allow_successors` is True,
        it attempts to find and union shapes from its successor (child) ontoids.

        Args:
            ontoid: The ontoid  to retrieve annotations for.
            
        Returns:
            A dictionary mapping section numbers to the Shapely Geometry for the
            ontoid (or its unioned successors), or None if not found.
        """
        result_shapes_by_secnum: 'AnnotationSet' = {} # secnum:{ontoid:shape}

        # Iterate through sections in sorted order
        for sec_num in self.all_sections:
            section_annotations = self.annotations_data.get(sec_num, {})
            successor_ids = self.tree_helper.get_successor_ids(ontoid) #  List[int]
        
            successor_shapes = {} # successor_ontoid: shape
            parshp = None
            for succ_id in [ontoid]+successor_ids: 
                if succ_id in section_annotations:
                    shp = section_annotations.get(succ_id)
                    if merge_children:
                        if parshp is None:
                            parshp = shp
                        else:
                            try:
                                parshp = _remove_small_interiors(parshp.union(shp).buffer(0))
                            except:
                                print(f"sec {sec_num}, ontoid {ontoid} succ_id {succ_id}, parshp geom_type {parshp.geom_type}")
                                raise
                    else:
                        successor_shapes[succ_id] = shp

            if merge_children:
                if parshp is not None:
                    result_shapes_by_secnum[sec_num] = {ontoid:parshp}
            else:
                if len(successor_shapes)>0:
                    result_shapes_by_secnum[sec_num] = successor_shapes
        
        return result_shapes_by_secnum
    
    def get_annotations_by_secnum(self, secnum:int)->'Annotations':
        return self.annotations_data[secnum]
    
    def get_level_ids(self, annot:'Annotations'):
        # annot can be obtained by calling get_annotations_by_secnum

        level_ids = defaultdict(list) # level:[ids]

        for ontoid in annot:
            rec = self.tree_helper.onto_lookup[ontoid]
            level_ids[rec.level].append(ontoid)
        
        return dict(level_ids)


    def get_reachable_parents(self, annot:'Annotations'):
        reachable1 = defaultdict(list) # parent: [annotated]
        reachable2 = defaultdict(list) # parent: [aggregatable]

        for ontoid in annot:
            
            par = self.tree_helper.onto_lookup[ontoid].parentid
            if ontoid not in reachable1[par]:
                reachable1[par].append(ontoid)

            anclist = list(reversed(self.tree_helper.get_ancestor_ids(ontoid)))
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

    def get_nonreachable(self, annot:'Annotations'):

        reachable = defaultdict(list) # anc: [successors]

        for ontoid in annot:
            anclist = self.tree_helper.get_ancestor_ids(ontoid)
            for anc in reversed(anclist):
                reachable[anc].append(ontoid)
        
        nonreachable = []
        for ontoid,rec in self.tree_helper.onto_lookup.items():
            if ontoid not in reachable and ontoid not in annot:
                nonreachable.append(ontoid)

        # organize as parent:[children]
        nrdict = defaultdict(list)
        leaves = []    
        for oid in nonreachable:
            parentid = self.tree_helper.onto_lookup[oid].parentid
            
            if parentid in nonreachable:
                nrdict[parentid].append(oid)
            else:
                leaves.append(oid)
        return dict(nrdict), leaves

    def get_supershape(self, ontoid:int, annot:'Annotations'):
        #  construct parent shapes by merging shapes 

        if ontoid in annot:
            return annot[ontoid]
        
        parshp = None
        chlist = []
        for annot_id in annot:
            anclist = self.tree_helper.get_ancestor_ids(annot_id)
            # FIXME: instead of ancestors of each annot_id, the successors of ontoid can be lookedup in annot
            # refer AnnotationManager.get_annotations_by_ontoid
            if ontoid in anclist:
                chlist.append(annot_id)
                if parshp is None:
                    parshp = annot[annot_id]
                else:
                    parshp = _remove_small_interiors(parshp.union(annot[annot_id])).buffer(0)
        
        return parshp, chlist

    def find_superids(self, annot:'Annotations'):

        superids = defaultdict(list)

        for ontoid in annot:
            parentids = self.tree_helper.get_ancestor_ids(ontoid)
            
            for drawnid in annot:
                if drawnid in parentids:
                    superids[drawnid].append(ontoid)

        return dict(superids)

    
    