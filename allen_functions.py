import urllib.request
import json
import os
from tqdm import tqdm
import requests


def fetch_atlas_metadata( atlas_id ) :
    
    # RMA query to find images for atlas
    query_url = "http://api.brain-map.org/api/v2/data/query.json?criteria=model::Atlas"
    query_url += ",rma::criteria,[id$eq%d]" % (atlas_id)
    query_url += ",rma::include,structure_graph(ontology),graphic_group_labels"

    webURL = urllib.request.urlopen(query_url)
    data = webURL.read()
    JSON_object = json.loads(data.decode('utf-8'))['msg'][0]
    return JSON_object


def fetch_atlas_images( atlas_metadata ) :
    
    # RMA query to find images for atlas
    query_url = "http://api.brain-map.org/api/v2/data/query.json?criteria=model::AtlasImage"
    # query_url += ",rma::criteria,[annotated$eqtrue]"
    query_url += ",atlas_data_set(atlases[id$eq%d])" % (atlas_metadata['id'])
    query_url += ",rma::options[order$eq'sub_images.section_number'][num_rows$eqall]"
    
    webURL = urllib.request.urlopen(query_url)
    data = webURL.read()
    JSON_object = json.loads(data.decode('utf-8'))['msg']
    return JSON_object


def fetch_graphic_groups( atlas_metadata ) :
    
    gg = [x['id'] for x in atlas_metadata['graphic_group_labels'] if 'Sulci' not in x['name'] and 'Hotspots' not in x['name']]
    return gg
    

def get_image_url(atlas_id, img, downsample, annotation=False): #, output_directory):
    if annotation :
        image_type = 'annotation'
        annotation_attr = 'true'
    else :
        image_type = 'primary'
        annotation_attr = 'false'
    
    # image_path = os.path.join( output_directory, '%04d_%d_%s.jpg' % (img['section_number'],img['id'],image_type) )
    #print(image_path)
    
    image_url  = "http://api.brain-map.org/api/v2/atlas_image_download/%d?" % (img['id'])
    image_url += "downsample=%d" % (downsample)
    image_url += "&annotation=%s" % (annotation_attr)
    image_url += "&atlas=%d" % (atlas_id)
    return image_url

def get_svg_url(atlas_id, img, graphic_groups, downsample): #, output_directory):
    if img['annotated']:    
        # svg_path = os.path.join( output_directory, '%04d_%d.svg' % (img['section_number'],img['id']) )
        #print(svg_path)
        
        groups_attr = (',').join([str(g) for g in graphic_groups])
                
        svg_url  = "http://api.brain-map.org/api/v2/svg/%d?" % (img['id'])
        svg_url += "downsample=%d" % (downsample)
        svg_url += "&groups=%s" % (groups_attr)

        return svg_url
    
    return None

class AllenHelper:
    def __init__(self, atlas_id=3, downsample = 3):
        """
        atlas ids:
        * 3 = 21 pcw cerebrum [default]
        * 287730656 = 21 pcw brainstem
        * 138322603 = 15 pcw

        mpp = 2^downsample
        downsample=3 [default] => mpp=8
        """
        self.atlas_id = atlas_id
        metadata = fetch_atlas_metadata( atlas_id )
        self.images = fetch_atlas_images( metadata )
        self.graphic_groups = fetch_graphic_groups( metadata )
        self.downsample = downsample

    def get_section_numbers(self):
        return [elt['section_number'] for elt in self.images]
            
    def get_section_urls(self, secnum):
        secnos = self.get_section_numbers()
        img = self.images[secnos.index(secnum)]
        image_url = get_image_url(self.atlas_id, img, self.downsample, False)
        annot_url = get_svg_url(self.atlas_id, img, self.graphic_groups, self.downsample)
        return image_url, annot_url

import xml.etree.ElementTree as ET
# from svgpathtools import parse_path
from svg.path import parse_path
import shapely

def make_polyshape(feat, make_valid=False):

    # feat is a list of coords [(x,y)] or ( [(x,y)], [(x,y)], ... )
    # where first is outer, all next are holes
    if len(feat)>1:
        shp = shapely.Polygon(shell=feat[0],holes=feat[1:])
        
    else:
        shp = shapely.Polygon(feat[0])
        if make_valid:
            shp = shp.buffer(0)
    
    return shp


def _path_to_coords(path_d):

    path = parse_path(path_d)
    coords = []
    for ii,seg in enumerate(path):
        pt1 = [seg.start.real, seg.start.imag]
        pt2 = [seg.end.real, seg.end.imag]
        if ii == 0:
            coords.append(pt1)
        coords.append(pt2)
    
    return coords

def get_svg_paths(svg_data):
    root = ET.fromstring(svg_data)
    svgpaths = {}
    for elt in root.findall(".//{*}path"):
        ontoid = elt.attrib['structure_id']
        pathd = elt.attrib['d']
        if ontoid not in svgpaths:
            svgpaths[ontoid]=[_path_to_coords(pathd)]
        else:
            svgpaths[ontoid].append(_path_to_coords(pathd))
    return svgpaths

