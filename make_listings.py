from dharani_functions import DharaniHelper
from allen_functions import AllenHelper

import sys
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

    with open(f'directory-listings/{specimenname}.csv','wt') as listing:
        listing.write('section_number, image_url, image_format, image_width, image_height, atlas_url, atlas_format, viewer_url\n')
        for secno in tqdm(sorted(secnumbers)):
            
            imgurl,annoturl = helper.get_section_urls(secno)
            imgwidth,imgheight = helper.get_imagedims(secno)
            
            if annoturl is None:
                annoturl = ''
            viewerurl = helper.get_viewer_url(secno)
            listing.write(','.join([str(secno), imgurl, imagefmt, str(imgwidth), str(imgheight), annoturl, atlasfmt, viewerurl]))
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

