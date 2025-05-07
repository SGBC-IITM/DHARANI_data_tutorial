Dharani/docs/Image

[Back] to `docs`

[Back]:README.md

# Image handling 

The `DharaniHelper` and `AllenHelper` both take two arguments:

 1. `specimennum` or `atlas_id` : refer [data page] which gives a table showing the allowable values and their meaning
 2. `downsample`: this is an optional argument, defaulting to the value of `3`. The value is used to convert to the resolution (mpp) of need, using the expression: ```mpp=2^downsample```. A value of 3 (the default), sets the operating resolution to 8 micron per pixel.

Both helper classes provide the function `get_sectionimage`, which returns a numpy array of shape ```(dim1, dim2, 3)```, where `dim1` is the height of the downsampled image, `dim2` is the width of the downsampled image, and 3 represents channels R,G,B. The data type is unsigned 8 bit integer.

This function does not entertain `downsample` values less than 3. 

For accessing high-resolution data (which can be very large in `dim1` and `dim2`), we recommend the use the function `get_zoomable_img_url` - which produces a download url. The downloaded image can be viewed in any Digital Pathology viewer such as [Aperio ImageScope] or [Huron viewer].

For accessing high-resolution tiles without downloading the image, we provide a sample notebook [image_handling_dharani.ipynb] 

[Aperio ImageScope]: https://www.leicabiosystems.com/en-in/digital-pathology/manage/aperio-imagescope/
[Huron viewer]:https://www.hurondigitalpathology.com/resource/download-huronviewer/
[image_handling_dharani.ipynb]: ../notebooks/image_handling_dharani.ipynb