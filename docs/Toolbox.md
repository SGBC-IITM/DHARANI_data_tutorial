Dharani/docs/Toolbox

[Back] to `docs`

[Back]:README.md

# Salient aspects
Functionality is separated into different files:
- Data access helpers (dharani_functions.py, allen_functions.py).
- Ontology management (ontology_handling.py).
- Annotation processing (annotation_handling.py, annotation_morphing.py).
- Low-level image file access (image_access.py).
- Notebook-specific display functions (nb_functions.py).
- Utility scripts (make_listings.py).

A uniform access layer is implemented for two distinct datasets ('dharani' and 'allen_devhuman'). This is achieved through the DharaniHelper (dharani_functions.py) and AllenHelper (allen_functions.py) classes.

Both helper classes strive to provide a similar set of methods (e.g., get_section_numbers, get_section_urls, get_sectionimage, get_annotation, get_viewer_url, get_annotations). This allows code that uses these helpers (like analysis notebooks) to interact with either dataset using the same method calls

## Atlas data
### Images
- Access methods (get_sectionimage) return images primarily as NumPy arrays, a standard format for numerical/image processing in Python.
- Support for different resolutions is built-in via the downsample parameter, handled differently depending on the source (pyramidal TIFF levels for Dharani, API parameters for Allen).
- Specialized access for pyramidal TIFFs (image_access.py) allows efficient reading of specific resolution levels or tiles directly from S3.

### Annotations

- Annotations represent spatial regions associated with ontology terms.
- The code standardizes annotation representation using shapely geometry objects (mostly Polygons). This provides a powerful and consistent way to perform geometric operations, regardless of whether the original format was GeoJSON (Dharani) or SVG (Allen).
- Methods like get_annotation return annotations grouped by ontology ID in a dictionary (Dict[int, shapely.Geometry]).
- Dedicated modules (annotation_handling.py, annotation_morphing.py) provide functions for analyzing, manipulating, and even interpolating these geometric annotations.

### Nomenclature 
The TreeHelper class (ontology_handling.py) provides a unified way to load, parse, navigate (find ancestors, children, siblings), and search (using fuzzy matching) ontology data from both sources.
It abstracts the underlying tree structure (nested dictionaries from JSON) into a more easily queryable format using dictionaries and namedtuples.

The code is designed to be used within `interactive environments` like Jupyter notebooks, providing helpers for visualization (matplotlib, shapely.plotting) and interactive exploration (jstree, OpenLayers integration stubs).

## Dependencies
The code effectively utilizes established scientific and data handling Python libraries: 
- numpy (numerical operations), 
- scipy (scientific computing, image resizing), 
- shapely (geometric operations), 
- s3fs/fsspec (S3 access), 
- requests (HTTP requests),
- PIL/Pillow (image manipulation), 
- json (data serialization), 
- tifffile (TIFF reading), 
- joblib (caching, parallelization), 
- rapidfuzz (fuzzy string matching).

