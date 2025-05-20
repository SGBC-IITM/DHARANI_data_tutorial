import numpy as np

import scipy
from scipy.stats import kurtosis
import numpy as np
from skimage.exposure import adjust_gamma, rescale_intensity
from skimage import transform
from collections import namedtuple

from scipy.ndimage import (
    label, find_objects,
      zoom, shift, rotate
)

#%%  
# single image ops, intensity oriented

from skimage.morphology import (
    dilation,binary_dilation, square, diamond, erosion ,closing , disk
)

def _get_salient_mask(arr,percent=0.2,sz_divisor=100):
    nr,nc=arr.shape[:2]
    assert percent > 0 and percent < 1, str(percent)
    if sz_divisor <= 0 or sz_divisor > min(nr,nc)//20:
        sz_divisor = min(nr,nc)//20
    # (100-percent)th percentile threshold abs(arr), and select top patches which cover the required percentage of image
    
    mapimg = transform.resize(np.abs(arr),(nr//sz_divisor,nc//sz_divisor),order=1)
    
    th = np.percentile(mapimg,100*(1-percent))
    msk_small = closing(mapimg>th,disk(5))
    msk_salient = transform.resize(msk_small,(nr,nc),order=0)
    return msk_salient.astype(bool)

def make_mask(arr):
    # green channel stretched image - for computations
    # note - this is in orig space (no padding no rotation)

    in_range_gr = np.percentile(arr[...,1],(5,99.99)).astype(np.uint8)

    arr1 = rescale_intensity(arr[...,1],in_range=tuple(in_range_gr),
                                        out_range=(0,192)).astype(np.uint8)
        
    pc=(arr1<240).sum()/(arr1.shape[0]*arr1.shape[1])
    mask = _get_salient_mask(255-arr1,max(0.4,min(0.7,1.1*pc)),16)
    mask = binary_dilation(mask,diamond(19))
    return mask

def auto_gamma(arr:np.array, sp='auto', ref_val=192, 
               step = 0.15, tol = 0.01, eta=2, 
               max_iter=30, dbg=False):
    """
    find gamma iteratively until 8% (sp) of blue intensities (arr[...,2]) are < 192;
        sp='auto' - choose setpoint based on kurtosis (indicator of dense or moderate or sparse tile)
        ref_val: 192 (sum(0-192)==75% of dark)
        step: 0.15 (gamma update steps)
        eta: 2 (momentum)
        tol: 0.01 (stopping when pv is close enough)
        max_iter: 30 (10-100)
        dbg: False (print debug info)
    """
    
    assert arr.dtype == np.uint8
    assert step>0
    if sp !='auto':
        assert sp>0 and sp < 1
    else:
        ku = kurtosis(arr[...,2].ravel(), fisher=False)
        sp = 0.08
        if ku < 5: sp = 0.04 # dense
        if ku > 10: sp = 0.12 # sparse
            
    assert ref_val > 100 and ref_val < 240
    assert tol > 0.0001 and tol < 0.05
    
    cnt=arr.shape[0]*arr.shape[1]

    data2 = arr.copy()
    gam = 1
    
    sane_max_iter = max(10,min(100,max_iter)) # sanity

    for _ in range(sane_max_iter):
        pv = np.sum(data2[:,:,2]<ref_val)/cnt
        err = sp-pv
        err_pc = 1-pv/sp
        
        if dbg:print(sp,pv,err,err_pc,gam)

        if np.abs(err) < tol:
            break

        delta = step*err_pc*eta
        gam2 = gam + delta

        if gam2 < 0.01: # can't be negative
            gam = max(0.01, gam*3/4)
        elif gam2 > 20:
            gam = min(20, gam *1.25)
        else:
            gam = gam2

        data2 = adjust_gamma(arr,gam)

    return data2, gam

def auto_gamma_bisection(arr: np.ndarray, sp: Union[str, float] = 'auto',
                         ref_val: int = 192, tol: float = 0.01,
                         max_iter: int = 30, dbg: bool = False,
                         gamma_bounds: Tuple[float, float] = (0.1, 10.0)) -> Tuple[np.ndarray, float]:
    """
    Finds an optimal gamma value using bisection search to meet a target
    percentage (sp) of blue channel pixels (arr[...,2]) below ref_val.

    Args:
        arr: Input image (uint8, assumed to have at least 3 channels if using blue).
        sp: Setpoint percentage (0.0 to 1.0) of pixels to be < ref_val.
            If 'auto', sp is chosen based on blue channel kurtosis.
        ref_val: Reference pixel value (0-255).
        tol: Tolerance for the error abs(pv - sp).
        max_iter: Maximum iterations for the bisection search.
        dbg: If True, print debug information.
        gamma_bounds: Tuple (min_gamma, max_gamma) for the search range.
                      Gamma values outside this range will not be tested beyond initial clamping.

    Returns:
        A tuple containing the gamma-adjusted image and the final gamma value.
    """
    if arr.dtype != np.uint8:
        raise TypeError("Input array 'arr' must be of dtype uint8.")
    if not (arr.ndim >= 3 and arr.shape[2] >= 3):
        raise ValueError("Input array 'arr' must have at least 3 channels for blue channel processing.")
    if not (0 < tol < 0.1):
        raise ValueError("Tolerance 'tol' must be between 0 (exclusive) and 0.1.")
    if not (isinstance(gamma_bounds, tuple) and len(gamma_bounds) == 2 and
            0 < gamma_bounds[0] < gamma_bounds[1]):
        raise ValueError("gamma_bounds must be a tuple (min_gamma, max_gamma) "
                         "with 0 < min_gamma < max_gamma.")

    original_blue_channel = arr[..., 2]
    pixel_count = original_blue_channel.size
    if pixel_count == 0:
        return arr.copy(), 1.0 # Return original for empty channel

    current_sp_val: float
    if sp == 'auto':
        ku = kurtosis(original_blue_channel.ravel(), fisher=False) # fisher=False for Pearson's kurtosis
        if ku < 5:  # dense content
            current_sp_val = 0.04
        elif ku > 10:  # sparse content
            current_sp_val = 0.12
        else:  # moderate content
            current_sp_val = 0.08
        if dbg:
            print(f"Auto sp selected: {current_sp_val:.3f} (kurtosis: {ku:.2f})")
    elif isinstance(sp, (float, int)) and 0.0 < sp < 1.0:
        current_sp_val = float(sp)
    else:
        raise ValueError("sp must be 'auto' or a float between 0 and 1 (exclusive).")

    if not (100 < ref_val < 240): # As per original constraints
        raise ValueError("ref_val must be between 100 and 240 (exclusive).")

    def calculate_pv(gamma_to_test: float, base_channel: np.ndarray) -> float:
        """Calculates percentage of pixels below ref_val for a given gamma."""
        if gamma_to_test <= 0: # Should be caught by gamma_bounds
            # This implies an extremely dark image if gamma is near 0.
            return 1.0 # Assume all pixels are dark
        adjusted_channel = adjust_gamma(base_channel, gamma_to_test)
        return np.sum(adjusted_channel < ref_val) / pixel_count

    gamma_low, gamma_high = gamma_bounds
    final_gamma = 1.0  # Default gamma

    # Evaluate pv at the boundaries of our gamma search range
    # We expect pv(gamma) to be monotonically decreasing with gamma.
    pv_at_gamma_low = calculate_pv(gamma_low, original_blue_channel)
    pv_at_gamma_high = calculate_pv(gamma_high, original_blue_channel)

    if dbg:
        print(f"Target sp: {current_sp_val:.4f}")
        print(f"Gamma bounds: [{gamma_low:.2f}, {gamma_high:.2f}]")
        print(f"PV at gamma_low ({gamma_low:.2f}): {pv_at_gamma_low:.4f}")
        print(f"PV at gamma_high ({gamma_high:.2f}): {pv_at_gamma_high:.4f}")

    # Check if the target sp is achievable within the given gamma_bounds
    if current_sp_val >= pv_at_gamma_low: # Target sp wants image darker than min_gamma allows
        if dbg:
            print(f"Target sp {current_sp_val:.4f} is >= pv_at_gamma_low {pv_at_gamma_low:.4f}. "
                  f"Clamping to gamma_low: {gamma_low:.2f}.")
        final_gamma = gamma_low
    elif current_sp_val <= pv_at_gamma_high: # Target sp wants image brighter than max_gamma allows
        if dbg:
            print(f"Target sp {current_sp_val:.4f} is <= pv_at_gamma_high {pv_at_gamma_high:.4f}. "
                  f"Clamping to gamma_high: {gamma_high:.2f}.")
        final_gamma = gamma_high
    else:
        # Bisection search
        for i in range(max_iter):
            current_gamma_iter = (gamma_low + gamma_high) / 2.0
            pv = calculate_pv(current_gamma_iter, original_blue_channel)
            err = pv - current_sp_val

            if dbg:
                print(f"Iter {i+1:2d}: low={gamma_low:.4f}, high={gamma_high:.4f}, "
                      f"mid_gamma={current_gamma_iter:.4f}, pv={pv:.4f}, err={err:.4f}")

            if abs(err) < tol:
                final_gamma = current_gamma_iter
                if dbg: print(f"Converged in {i+1} iterations.")
                break

            # If pv is too high (image too dark for target sp), we need to increase gamma.
            if err > 0: # pv > current_sp_val
                gamma_low = current_gamma_iter
            else: # pv < current_sp_val (image too bright for target sp)
                gamma_high = current_gamma_iter
            
            final_gamma = current_gamma_iter # Update final_gamma in each iteration

            if i == max_iter - 1 and dbg:
                print(f"Max iterations ({max_iter}) reached. Using last mid_gamma: {final_gamma:.4f}")
    
    adjusted_image = adjust_gamma(arr, final_gamma)
    return adjusted_image, final_gamma

#%% array oriented ops

ROI = namedtuple('ROI', ['row_slice', 'col_slice'])
# instantiate as
# roi_spec = ROI(slice(r1,r2), slice(c1,c2))

def crop_or_pad(arr:np.ndarray, roi:ROI):
    """
    Crops or pads a NumPy array to a specified region of interest (ROI).

    Args:
        arr: The input NumPy array.
        roi: An ROI namedtuple with 'row_slice' and 'col_slice' attributes.
             These slices define the desired [start, stop) interval for rows and columns.
             It's assumed that slice.start and slice.stop are integers.
        constant_values: The value used for padding. Defaults to 255.

    Returns:
        A new NumPy array representing the cropped or padded region.
    """
    r1 = roi.row_slice.start
    c1 = roi.col_slice.start

    r2 = roi.row_slice.stop
    c2 = roi.col_slice.stop

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

def get_bordermean(arr,borderwidth=10):
    """
    Finds a representative grayscale intensity of pixels close to the image border
    """
    
    assert len(arr.shape)==2
    left = np.mean(arr[:,:borderwidth])
    right = np.mean(arr[:,-borderwidth:])
    top = np.mean(arr[:borderwidth,:])
    bot = np.mean(arr[-borderwidth:,:])

    # mean(mean(slightly overlapping edgeboxes))
    return 0.25*(left+top+right+bot) 

def removeblack(img):
    
    # blk = (img[:,:,0]<20) & (img[:,:,1]<20) & (img[:,:,2]<20)
    blk0 = (img.mean(axis=2)<170) & (img[...,2]<120) & (img[:,:,0] < 120)
    if blk0.sum() > 400:
        blk = dilation(erosion(blk0,square(19)),square(29)) # FIXME: need to be adaptive to mpp
        img_r = np.where(blk,255,img[:,:,0]) #XXX: 255 is ok for brightfield nissl - check for others
        img_g = np.where(blk,255,img[:,:,1]) #FIXME: inpaint might be better?
        img_b = np.where(blk,255,img[:,:,2])
        return np.dstack((img_r,img_g,img_b))

def get_gray(img,reduce_op=np.max):
    shp = img.shape
    if len(shp)>2:
        img = reduce_op(img,axis=2)
    return img.copy()

#%% 
# pair of image ops

from skimage.util import compare_images


def make_overlap(img1_in, img2_in):
    img1 = get_gray(img1_in)
    img2 = get_gray(img2_in)
    outimg = np.zeros(list(img1.shape)+[3],img1.dtype)
    outimg[...,0]=img1
    outimg[...,1]=img2
    return outimg

def make_diff_checkerboard(img1_in, img2_in):
    img1 = get_gray(img1_in)
    img2 = get_gray(img2_in)
    shp = img1.shape
    dif=compare_images(img1,img2,'checkerboard',n_tiles=(shp[0]//100,shp[1]//100)) # a checker box every 100 pixels
    return dif

