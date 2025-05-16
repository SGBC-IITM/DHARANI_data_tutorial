Dharani/docs/HOWTO

[Back] to `docs`

[Back]:README.md

(c) 2025, SGBC-IITM

 Refer [Quick Start] | [Data]

[Quick Start]: Getting_started.md
[Data]: Data.md

## HowTo

1. **Data handling** 

Find specimens, sections
| * | Refer | Example Notebook |
| :--- | :--- | :--- | 
| Find the list of specimens    |  docs/[Data.md] |       | 
| * Select a specimen to work with, <br> * Get the list of sections available <br> * Filter the list to find only annotated sections   |  DharaniHelper / AllenHelper, csv_handling.py:load_csv |  [image_handling_dharani.ipynb]    | 
---
.

Images
| * | Refer | Example Notebook |
| :--- | :--- | :--- | 
| * Get a macro view of a section image  | DharaniHelper / AllenHelper |  [dharani_sample.ipynb]    | 
| Advanced image access <br> *Get viewer URL <br> * Get a thumbnail image in numpy format <br> * Get a tile at specified level and tile_index <br> * Get a region at specified level and ROI (left, top, width, height) | PyrTifAccessor, nb_functions.py:display_tiling_grid | [image_handling_dharani.ipynb] |
| Registering adjacent images, forming a stack | valis.registration.Valis | |
 
---
.

Annotations + Ontology

| * | Refer | Example Notebook |
| :--- | :--- | :--- | 
|   Load the annotations of a section, and overlay it on the macro view |   DharaniHelper / AllenHelper |  [dharani_sample.ipynb]    | 
|  * Load the ontology entities involved in a section's annotation <br> * List the drawn entities, with their immediate parent <br> * Merge sibling entities to visualize the parent  | TreeHelper, nb_functions, annotation_handling.py:get_supershape |  [dharani_sample.ipynb] |
| * Find parent ontology entities whose children  were not marked at all in a given brain | |
---
.

With ontology, 

| * | Refer | Example Notebook |
| :--- | :--- | :--- | 
|  * Explore the ontology as a tree | [Dharani tree], [Allen Dev Human Tree] | [dharani_sample.ipynb] |
|  * Explore subtrees, cortical areas, layered areas (zones) <br>* Get special fields like definitions (info) | TreeHelper | [test_ontology.ipynb] |
| * Search the ontology with fuzzy matching, partial matching | TreeHelper |  
| * Relate between the entities in Dharani ontology and Allen Dev Human ontology by name | | [test_ontology.ipynb] | 
| * Find divergences (non-leaf entities that are not relatable) between Dharani and Allen Dev Human ontology | | 
---

.

2. **Working with region annotations**

Main data type : **Annotation** -
represented by a python dict: [ontoid, shape]
This is returned by DharaniHelper.`get_annotation`(secnum:int) 
and also AllenHelper.`get_annotation`(secnum:int)

With a region in isolation:

| * | Refer | Example Notebook |
| :--- | :--- | :--- | 
| Get the basic properties <br> (representative point within the region, area, perimeter, major axis length, max width, orientation)    |  annotation_handling.py:get_properties  |  [dharani_annotation_properties.ipynb]     |
---
.

Relationship between regions:

| * | Refer | Example Notebook |
| :--- | :--- | :--- | 
|  Get region adjacency by shared boundaries (as an adjacency list), make a (di)graph and display it, <br> * inspect graph components | annotation_handling.py:get_adjacency | [dharani_annotation_properties.ipynb] |
| Get planar positional adjacency (inferior, superior, left, right) | | |
---
.

With Annotation + Ontology:

| Given an 'Annotation', ... | Refer | Example Notebook |
| :--- | :--- | :--- | 
|  find the drawn regions that are at the same level in the ontology | annotation_handling.py:get_level_ids | |
|  find the non-leaf entities that have been drawn | annotation_handling.find_superids | |
|  find the parents in the ontology that are reachable (children present in Annotation) | annotation_handling.py:get_reachable_parents | 
| * Gathering child annotations that form a parent | TreeHelper.get_successor_ids(parentid) | | 
| find the parents that are not involved (can not be reached from the children present in Annotation) | annotation_handling.py:get_nonreachable | |
| * Integrating properties of annotated children, to aggregate the properties of a parent | | |
---
.

With all annotations of a specimen

| * | Refer | Example Notebook |
| :--- | :--- | :--- | 
| * Getting all annotations of a specimen | DharaniHelper.get_annotations() | [dharani_annotation_stats.ipynb]|
| * Forming 3d mesh by integrating across sections | annotation_morphing.py:make_mesh | |
| * Interpolating annotations at gaps (un-annotated section numbers) | annotation_morphing.py:morph_shape | [dharani_annotation_morph.ipynb] |
| * Rendering the integration result | plotly.graph_objects.Mesh3d, trimesh.show() | [dharani_3d_sample1.ipynb] |
| * Tabulating the volume of a given brain region across specimens | | |
---

[Data.md]: ../docs/Data.md
[Docs]:../docs/README.md
[Top]:../README.md
[image_handling_dharani.ipynb]:../notebooks/image_handling_dharani.ipynb
[dharani_sample.ipynb]:../notebooks/dharani_sample.ipynb
[test_ontology.ipynb]: ../notebooks/test_ontology.ipynb
[test_ontology.ipynb]: ../notebooks/test_ontology.ipynb
[Dharani tree]: https://sgbc-iitm.github.io/dharani_tree.html
[Allen Dev Human tree]: https://sgbc-iitm.github.io/allen_tree.html
[dharani_annotation_stats.ipynb]: ../notebooks/dharani_annotation_stats.ipynb
[dharani_3d_sample1.ipynb]: ../notebooks/dharani_3d_sample1.ipynb
[dharani_annotation_properties.ipynb]: ../notebooks/dharani_annotation_properties.ipynb
[dharani_annotation_morph.ipynb]: ../notebooks/dharani_annotation_morph.ipynb
