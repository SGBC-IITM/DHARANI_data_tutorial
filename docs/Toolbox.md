Dharani/docs/Toolbox

[Back] to `docs`

[Back]:README.md

Refer [Getting Started] | [howto]s | view/create [issues]

[Getting Started]: Getting_started.md

[howto]: HOWTO.md

[issues]: https://github.com/SGBC-IITM/DHARANI_data_tutorial/issues/

# Salient aspects
A compact, flat organization is used for the python modules, which can be imported into the notebooks and used. Functionality is separated into the following modules:
- *Data* access helpers (dharani_functions.py, allen_functions.py) (~300 LOC each).
- *Ontology* management (ontology_handling.py) (~400 LOC)
- *Annotation* processing (annotation_handling.py, annotation_morphing.py) (~500 LOC)

Utility modules used by the above: 
- Low-level image file access (image_access.py).
- Notebook-specific display functions (nb_functions.py).
- Command line scripts (like `make_listings.py`).

A uniform access layer is implemented for two distinct datasets ('dharani' and 'allen_devhuman'). This is achieved through the `DharaniHelper` (dharani_functions.py) and `AllenHelper` (allen_functions.py) classes.

Both helper classes strive to provide a similar set of methods (e.g., `get_section_numbers`, `get_section_urls`, `get_sectionimage`, `get_annotation`, `get_viewer_url`). This allows code that uses these helpers (like analysis notebooks) to interact with either dataset using the same method calls.

## Atlas data
### Images
- Access methods (`get_sectionimage`) return images primarily as NumPy arrays, a standard format for numerical/image processing in Python.
- Support for different resolutions is built-in via the `downsample` parameter, handled differently depending on the source (pyramidal TIFF levels for Dharani, API parameters for Allen).
- Specialized access for pyramidal TIFFs (image_access.py) allows efficient reading of specific resolution levels or tiles directly from S3.

### Annotations

- Annotations represent spatial regions associated with ontology terms.
- The code standardizes annotation representation using `shapely` `geometry` objects (mostly Polygons). This provides a powerful and consistent way to perform geometric operations, regardless of whether the original format was GeoJSON (Dharani) or SVG (Allen).
- Methods like `get_annotation` return annotations grouped by ontology ID in a dictionary (Dict[int, shapely.Geometry]).
- Dedicated modules (annotation_handling.py, annotation_morphing.py) provide functions for analyzing, manipulating, and even interpolating these geometric annotations.

### Nomenclature 
The `TreeHelper` class (ontology_handling.py) provides a unified way to load, parse, navigate (find ancestors, children, siblings), and search (using fuzzy matching) ontology data from both sources.
It abstracts the underlying tree structure (nested dictionaries from JSON) into a more easily queryable format using dictionaries and namedtuples.

The code is designed to be used within *interactive environments* like `Jupyter` notebooks, providing helpers for visualization (matplotlib, shapely.plotting) and interactive exploration (plotly).

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

These are recorded in the requirements txt file, for easy reproduction of the environment using `virtualenv` and `pip`.
