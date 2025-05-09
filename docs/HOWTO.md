Dharani/docs/Toolbox

[Back] to `docs`

[Back]:README.md

## Quick start
Refer [Getting Started]

[Getting Started]: Getting_started.md

## HOWTOs

1. **Data handling** 

Find specimens, sections
| * | Refer | Example Notebook |
| :--- | :--- | :--- | 
| Find the list of specimens    |  docs/[Data.md] |       | 
| * Select a specimen to work with, <br> * Get the list of sections available <br> * Filter the list to find only annotated sections   |  DharaniHelper / AllenHelper |  [dharani_sample.ipynb]    | 
---
.

Images
| * | Refer | Example Notebook |
| :--- | :--- | :--- | 
| * Get a macro view of a section image  | DharaniHelper / AllenHelper |  [dharani_sample.ipynb]    | 
| Advanced image access | PyrTifAccessor | [image_handling_dharani.ipynb]
---
.

Annotations + Ontology

| * | Refer | Example Notebook |
| :--- | :--- | :--- | 
|   Load the annotations of a section, and overlay it on the macro view |   DharaniHelper / AllenHelper |  [dharani_sample.ipynb]    | 
|  * Load the ontology entities involved in a section's annotation <br> * List the drawn entities, with their immediate parent <br> * Merge sibling entities to visualize the parent  | TreeHelper, nb_functions, annotation_handling.py:get_supershape |  [dharani_sample.ipynb] |
---
.

With ontology, 

| * | Refer | Example Notebook |
| :--- | :--- | :--- | 
|  * Explore the ontology as a tree | [Dharani tree], [Allen Dev Human Tree] | [dharani_sample.ipynb] |
|  * Explore subtrees, cortical areas, layered areas (zones) <br>* Get special fields like definitions  | TreeHelper | [test_ontology.ipynb] |
| * Search the ontology with fuzzy matching, partial matching | TreeHelper |  
| * Relate between the entities in Dharani ontology and Allen Dev Human ontology by name | | [test_ontology.ipynb] | 
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
| Get the basic properties <br> (representative point within the region, area, perimeter, major axis length, max width, orientation)    |  annotation_handling.py:get_properties  |       |
---
.

Relationship between regions:

| * | Refer | Example Notebook |
| :--- | :--- | :--- | 
|  Get region adjacency (as an adjacency list) | annotation_handling.py:get_adjacency |
---
.

With Annotation + Ontology:

| * | Refer | Example Notebook |
| :--- | :--- | :--- | 
| Given an 'Annotation', find the drawn regions that are at the same level in the ontology | annotation_handling.py:get_level_ids |
| Given an 'Annotation', find the non-leaf entities that have been drawn | annotation_handling.find_superids | 
| Given an 'Annotation', find the parents in the ontology that are reachable (children present in Annotation) | annotation_handling.py:get_reachable_parents | 
| Given an 'Annotation', find the parents that are not involved (can not be reached from the children present in Annotation) | annotation_handling.py:get_nonreachable | 
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
