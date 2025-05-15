import s3fs
import json
import numpy as np
import os
from scipy.ndimage import zoom
from image_access import PyrTifAccessor
from PIL import Image
from io import BytesIO
import base64

from collections import defaultdict
from shapely.geometry import shape as make_shape

from joblib import Parallel, delayed
import logging

logger = logging.getLogger(__name__)

s3 = s3fs.S3FileSystem(anon=True)

class DharaniHelper:
    """
    Helper for simplified access to Dharani image and annotation data from 
    AWS s3 bucket s3://dharani-fetal-brain-atlas
    """

    def __init__(self, specimennum:int, downsample=3):
        """
        Args:
            specimennum : [1,2,3,4,5]

                mpp = 2^downsample
            downsample = 3 [default] => mpp=8 ; allowed [0..7]
        """
        assert downsample >=0 and downsample <= 7 
        self._specimennum = specimennum
        self._downsample = downsample
        

    def __str__(self):
        return f'{self.get_specimenname()}, downsample={self._downsample}'

    def get_specimenname(self):
        """
        Returns string name of this specimen
        """
        return 'Dharani_Specimen_'+str(self._specimennum)
    
    def get_section_numbers(self):
        """        
        Returns list of section numbers in this specimen
        """
        secnumbers = []
        for elt in s3.ls(f'dharani-fetal-brain-atlas/data2d/specimen_{self._specimennum}'):
            if elt.endswith('.tif') and '_geo.tif' not in elt:
                fname = os.path.basename(elt)
                secnum = fname.split('_')[-1][:-4]
                secnumbers.append(int(secnum))
        return list(sorted(secnumbers))

    def get_s3_key(self):
        return f'dharani-fetal-brain-atlas/data2d/specimen_{self._specimennum}'

    def get_filenames(self):
        contents_1=s3.ls(self.get_s3_key())
        tiflist = []
        jsonlist = []
        for elt in contents_1:
            if '_geo.tif' in elt:
                continue
            bn = os.path.basename(elt)
            if len(bn)==0:
                continue
            parts = bn.split('.')
            if parts[1]=='json':
                jsonlist.append(parts[0])
            elif parts[1]=='tif':
                tiflist.append(parts[0])

        outdict = {}
        for tifname in tiflist:
            secnum = int(tifname.split('_')[-1])
            outdict[secnum]={'image':tifname+'.tif'}
            if tifname in jsonlist:
                outdict[secnum]['annotation']=tifname+'.json'

        imagemissinglist=[]
        for jsonname in jsonlist:
            if jsonname not in tiflist:
                imagemissinglist.append(jsonname)

        if len(imagemissinglist)>0:
            raise Exception(f'Image missing for {imagemissinglist}')
            
        return outdict

    def get_section_urls(self, secnum:int):
        """
        Returns image and annotation urls for this section
        Args:
            secnum: section number
        Returns:
            image url, annotation url
            image url: url to access the section image
            annotation url: url to access the annotation json

        """

        baseurl_s3 = 's3://dharani-fetal-brain-atlas'
        baseurl = 'https://dharani-fetal-brain-atlas.s3.us-west-2.amazonaws.com'

        annoturl = f'data2d/specimen_{self._specimennum}/Specimen_{self._specimennum}_{secnum}.json'
        annoturl_http = f'{baseurl}/{annoturl}'
        if not s3.exists(f'{baseurl_s3}/{annoturl}'):
            annoturl_http = None
        if self._downsample > 2:
            imgurl = self._get_base64_imgurl(secnum)
        elif self._downsample==0:
            imgurl =  annoturl_http.replace('.json','.tif')
        else: 
            raise NotImplementedError # downsample = 1 or 2
        
        return imgurl, annoturl_http
    

    def get_zoomable_img_url(self, secnum:int):
        """
        Returns zoomable image url for this section
        """

        baseurl_s3 = f's3://dharani-fetal-brain-atlas'
        baseurl = 'https://dharani-fetal-brain-atlas.s3.us-west-2.amazonaws.com'

        httpurl = f'{baseurl}/data2d/specimen_{self._specimennum}/Specimen_{self._specimennum}_{secnum}.tif'
        s3url = f'{baseurl_s3}/data2d/specimen_{self._specimennum}/Specimen_{self._specimennum}_{secnum}.tif'
        return httpurl, s3url
    
    def get_imagedims(self, secnum:int):
        """
        returns original image dimensions (does not heed the constructor's downsample argument) 
        for this section.
        """

        s3url = f's3://dharani-fetal-brain-atlas/data2d/specimen_{self._specimennum}/Specimen_{self._specimennum}_{secnum}.tif'
        accessor = PyrTifAccessor(s3url)
        info = accessor.get_info(0,0,0)
        return info['imagewidth'], info['imageheight']
    
    def _get_base64_imgurl(self,secnum:int):

        secimg_np = self.get_sectionimage(secnum)
        pil_img = Image.fromarray(secimg_np)
        buffer = BytesIO()
        pil_img.save(buffer, format='JPEG')
        base64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return f'data:image/png;base64,{base64_str}'

    def get_sectionimage(self, secnum:int):
        """
        returns section image as numpy array.
        For this to work, constructor's downsample argument should be >2.
        """
        
        s3url = f's3://dharani-fetal-brain-atlas/data2d/specimen_{self._specimennum}/Specimen_{self._specimennum}_{secnum}.tif'
        accessor = PyrTifAccessor(s3url)
        maxlevel = len(accessor.infodict['series'][0]['levels'])-1
        assert self._downsample > 2, "Section image access for mpp<8 not supported"
        lev = self._downsample
        postresizefactor = 1
        if self._downsample > maxlevel:
            lev = maxlevel
            postresizefactor = 2**(self._downsample - lev)
        
        page = accessor.get_page(0,lev,0)

        if postresizefactor > 1:
            shp = page.shape
            out = np.zeros((shp[0]//postresizefactor, shp[1]//postresizefactor, shp[2]),page.dtype)
            for ch in range(3):
                out[...,ch] = zoom(page[...,ch],1/postresizefactor)
        else:
            out = page
        return out

    def get_annotation(self, secnum:int):
        """
        returns annotation as dict where
        keys are ontoid, values are shapely.Geometry
        """
        
        jsonpath = f'data2d/specimen_{self._specimennum}/Specimen_{self._specimennum}_{secnum}.json'
        if not s3.exists('dharani-fetal-brain-atlas/'+jsonpath):
            return {}

        with s3.open('dharani-fetal-brain-atlas/'+jsonpath) as fp:
            annot = json.load(fp)
            # {type: featurecollection, features: [features] }

        # aggregate by ontoid
        shapes = defaultdict(list)
        mpp = 2**self._downsample
        for feat in annot['features']:
            ontoid = int(feat['properties']['data']['id'])
            coordinates = np.abs(np.array(feat['geometry']['coordinates'])).squeeze()/mpp

            if feat['geometry']['type']!='Polygon':
                logger.warning(f"sec {secnum} - skipped {ontoid} : geomtype {feat['geometry']['type']}")
                continue

            if len(coordinates)<4:
                logger.warning(f"sec {secnum} - skipped {ontoid} : too few coordinates {coordinates.shape}")
                continue

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

    def get_viewer_url(self, secnum:int):
        """ 
        returns the web url which shows the Dharani section
        """
        baseurl = 'https://brainportal.humanbrain.in'
        url = f'{baseurl}/code/2dviewer/annotation/public?data={self._specimennum-1}&region=-1&section={secnum}'
        return url
    
    def get_annotations(self, concurrent=False):
        """
        returns all annotations as dict where
        keys are ontoids, values are dict of secno:shapely.Geometry
        """

        secnos = self.get_section_numbers()
        outdict = defaultdict(dict)

        def workerfunc(secnum):
            try:
                annot_seci = self.get_annotation(secnum)
                return secnum, annot_seci
            except:
                logger.error(f'ERR: sec {secnum}')
                return secnum, None

        if not concurrent:
            for secnum in secnos:
                secnum, annot_seci = workerfunc(secnum)
                for ontoid,shp in annot_seci.items():
                    outdict[ontoid][secnum]=shp
                
        else:
            results = Parallel(n_jobs=4)(
                delayed(workerfunc)(secnum) for secnum in secnos
            )
            for secnum, annot_seci in results:
                for ontoid,shp in annot_seci.items():
                    outdict[ontoid][secnum]=shp
                    
        return outdict
    
