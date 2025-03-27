import s3fs
import json
import numpy as np
import os

from image_access import PyrTifAccessor

from collections import defaultdict
from shapely.geometry import shape as make_shape

class DharaniHelper:
    """
    Helper for simplified access to Dharani image and annotation data from AWS s3 bucket s3://dharani-fetal-brain-atlas
    """
    def __init__(self, specimennum, downsample=3):
        """
        specimennum : [1,2,3,4,5]

        mpp = 2^downsample
        downsample = 3 [default] => mpp=8
        """

        self.specimennum = specimennum
        self.downsample = downsample
        self.s3 = s3fs.S3FileSystem(anon=True)

    def get_section_numbers(self):
        secnumbers = []
        for elt in self.s3.ls(f'dharani-fetal-brain-atlas/data2d/specimen_{self.specimennum}'):
            if elt.endswith('.tif'):
                fname = os.path.basename(elt)
                secnum = fname.split('_')[-1][:-4]
                secnumbers.append(int(secnum))
        return secnumbers

    def get_section_urls(self, secnum:int):
        baseurl_s3 = 's3://dharani-fetal-brain-atlas'
        baseurl = 'https://dharani-fetal-brain-atlas.s3.us-west-2.amazonaws.com'
        imgurl = f'{baseurl}/data2d/specimen_{self.specimennum}/Specimen_{self.specimennum}_{secnum}.tif'
        annoturl = imgurl[:-4]+'.json'
        return imgurl, annoturl
    
    def get_sectionimage(self, secnum):
        s3url = f's3://dharani-fetal-brain-atlas/data2d/specimen_{self.specimennum}/Specimen_{self.specimennum}_{secnum}.tif'
        accessor = PyrTifAccessor(s3url)
        return accessor.get_page(0,self.downsample,0)

    def get_annotation(self, secnum):
        
        jsonpath = f'data2d/specimen_{self.specimennum}/Specimen_{self.specimennum}_{secnum}.json'    
        with self.s3.open('dharani-fetal-brain-atlas/'+jsonpath) as fp:
            annot = json.load(fp)
            # {type: featurecollection, features: [features] }

        # aggregate by ontoid
        shapes = defaultdict(list)
        mpp = 2**self.downsample
        for feat in annot['features']:
            ontoid = feat['properties']['data']['id']
            coordinates = np.abs(np.array(feat['geometry']['coordinates'])).squeeze()/mpp

            updatedgeom = {
                'type':feat['geometry']['type'],
                'coordinates': [coordinates.tolist()]
                           }
        
            shape = make_shape(updatedgeom).buffer(0)
            shapes[ontoid].append(shape)

        # revisit and make multi
        
        outdict = {}
        for ontoid,shplist in shapes.items():
            united = None
            for shp in shplist:
                if united is None:
                    united = shp
                else:
                    united = united.union(shp)

            outdict[ontoid]=united
        return outdict

    def get_viewer_url(self, secnum):
        baseurl = 'https://dharani.humanbrain.in'
        url = f'{baseurl}/code/2dviewer/annotation/public?data={self.specimennum-1}&region=-1&section={secnum}'
        return url
    