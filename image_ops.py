import numpy as np

def crop_or_pad(arr, roi):
    # arr: np.ndarray
    # roi: {'r1':xxx, 'c1': xxx, 'r2':xxx, 'c2': xxx}

    r1 = roi['r1']
    c1 = roi['c1']

    r2 = roi['r2']
    c2 = roi['c2']

    shp = arr.shape
    
    pad_r = [0,0]
    
    if r1<0:
        pad_r[0] = -r1
        r1 = 0
        
    if r2>shp[0]:
        pad_r[1] = r2-shp[0]
        r2 += pad_r[0]
        
    pad_c = [0,0]

    if c1<0:
        pad_c[0] = -c1
        c1 = 0
        
    if c2>shp[1]:
        pad_c[1] = c2-shp[1]
        c2 += pad_c[0]

    padvalues = [pad_r, pad_c]
    if len(shp)>2:
        padvalues+=[[0,0]]
    arr_padded = np.pad(arr,padvalues,constant_values=255)
    
    return arr_padded[r1:r2,c1:c2,...]
    