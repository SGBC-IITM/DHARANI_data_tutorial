import s3fs
import json
import numpy as np
import os

from image_access import PyrTifAccessor

from collections import defaultdict
from shapely.geometry import shape as make_shape

class DharaniHelper:
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
                secnumbers.append(secnum)
        return secnumbers

    def get_dharani_sectionimage(self, secnum):
        s3url = f's3://dharani-fetal-brain-atlas/data2d/specimen_{self.specimennum}/Specimen_{self.specimennum}_{secnum}.tif'
        accessor = PyrTifAccessor(s3url)
        return accessor.get_page(0,self.downsample,0)

    def get_dharani_annotation(self, secnum):
        
        jsonpath = f'data2d/specimen_{self.specimennum}/Specimen_{self.specimennum}_{secnum}.json'    
        with self.s3.open('dharani-fetal-brain-atlas/'+jsonpath) as fp:
            annot = json.load(fp)
            # {type: featurecollection, features: [features] }

        # aggregate by ontoid
        outdict = defaultdict(list)
        mpp = 2**self.downsample
        for feat in annot['features']:
            ontoid = feat['properties']['data']['id']
            coordinates = np.abs(np.array(feat['geometry']['coordinates'])).squeeze()/mpp

            updatedgeom = {
                'type':feat['geometry']['type'],
                'coordinates': [coordinates.tolist()]
                           }
        
            shape = make_shape(updatedgeom)
            outdict[ontoid].append(shape)

        return outdict
