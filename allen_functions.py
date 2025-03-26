import urllib.request
import json
import requests

from PIL import Image
from io import BytesIO
import numpy as np
from collections import defaultdict

#%% low level functions specific to Allen dataset

# ref  https://community.brain-map.org/t/atlas-drawing-and-ontologies/2864

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

#%%

class AllenHelper:
    def __init__(self, atlas_id:int = 3, downsample:int = 3):
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

    def _get_img(self,secnum:int):
        secnos = self.get_section_numbers()
        img = self.images[secnos.index(secnum)]
        return img

    def get_section_urls(self, secnum:int):
        img = self._get_img(secnum)
        image_url = get_image_url(self.atlas_id, img, self.downsample, False)
        annot_url = get_svg_url(self.atlas_id, img, self.graphic_groups, self.downsample)
        return image_url, annot_url

    def get_sectionimage(self,secnum:int):
        imgurl, annoturl = self.get_section_urls(secnum)
        req = requests.get(imgurl, timeout=500, stream=True)
        im = Image.open(BytesIO(req.content))
        return np.array(im)
    
    def get_annotation(self, secnum:int):
        imgurl, annoturl = self.get_section_urls(secnum)
        req = requests.get(annoturl, timeout=500)
        
        outdict = {}
        if req.status_code==200:
            # FIXME: MAGIC: 3 was found empirically 
            shapes = get_svg_paths_as_shapes(req.text, scale=3/(2**(self.downsample)))

            for ontoid,shplist in shapes.items():
                united = None
                for shp in shplist:
                    if united is None:
                        united = shp
                    else:
                        united=united.union(shp)
                        
                outdict[ontoid] = united
        return outdict
        
    
    def get_viewer_url(self, secnum:int):
        baseurl = 'https://atlas.brain-map.org'
        img = self._get_img(secnum)
        plate=img['lims1_id']
        url = f'{baseurl}/atlas?atlas={self.atlas_id}&plate={plate}&zoom=-5'
        return url

#%% util functions for handling svg, shapely 

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


# from shapely.geometry import mapping # LineString, Polygon,

# def make_geojson_feature(structureid,shape):
#     # reverse of make_shape
#     return  {
#         "type": "Feature", 
#         "geometry": mapping(shape),
#         "properties": {"id":structureid}
#     }
    

def _path_to_coords(path_d, scale):

    path = parse_path(path_d)
    coords = []
    for ii,seg in enumerate(path):
        # pt1 = [seg.start.real, seg.start.imag]
        # pt2 = [seg.end.real, seg.end.imag]
        # if ii == 0:
        #     coords.append(pt1)
        # coords.append(pt2)
        
        for t in np.linspace(0, 1, num=10):  # More points = smoother
            pt = seg.point(t)
            pt2 = (pt.real,pt.imag)
            coords.append(pt2)
    
    return np.array(coords)*scale

def get_svg_paths_as_shapes(svg_data, scale=1):
    root = ET.fromstring(svg_data)

    shapes = defaultdict(list)

    for elt in root.findall(".//{*}path"):
        ontoid = int(elt.attrib['structure_id']) # NOTE: from xml default type is str
        pathd = elt.attrib['d']
        coords = _path_to_coords(pathd,scale)
        # print(ontoid,len(coords))
        shp = make_polyshape([coords],make_valid=True)
        
        shapes[ontoid].append(shp)

    return shapes

