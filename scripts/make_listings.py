#! python
# Script to generate the csv files in directory-listings
# run from repo toplevel as:
# python scripts/make_listings.py [dataset] [specimennum]
# dataset: dharani or allen
# specimennum: refer docs/Data.md

import sys
sys.path.append('.')

from dharani_functions import DharaniHelper
from allen_functions import AllenHelper


from tqdm import tqdm

def main(helper):
    
    secnumbers = helper.get_section_numbers()
    specimenname = helper.get_specimenname()

    if 'Dharani' in specimenname:
        atlasfmt = 'geojson'
        imagefmt = 'tif'
    elif 'Allen' in specimenname:
        atlasfmt = 'svg'
        imagefmt = 'jpg'

    resolution = '1'
    with open(f'directory-listings/{specimenname}.csv','wt') as listing:
        listing.write('section_number, image_url, image_format, image_resolution_mpp, image_width, image_height, atlas_url, atlas_format, viewer_url\n')
        for secno in tqdm(sorted(secnumbers)):
            
            imgurl,annoturl = helper.get_section_urls(secno)
            imgwidth,imgheight = helper.get_imagedims(secno)
            
            viewerurl = helper.get_viewer_url(secno)

            thisatlasfmt = atlasfmt
            thisresolution = resolution

            if annoturl is None:
                annoturl = ''
                thisatlasfmt = ''
                viewerurl += '&type=hd'
                thisresolution = '4'
            
            listing.write(','.join([str(secno), imgurl, imagefmt, thisresolution, str(imgwidth), str(imgheight), annoturl, thisatlasfmt, viewerurl]))
            listing.write('\n')



if __name__=="__main__":

    dataset = sys.argv[1]
    specimennum_in = int(sys.argv[2])
    
    if dataset=='dharani':
        helper = DharaniHelper(specimennum=specimennum_in, downsample=0)
        
    elif dataset=='allen':
        helper = AllenHelper(atlas_id=specimennum_in, downsample=0)

    else:
        raise NotImplementedError
    
    main(helper)

