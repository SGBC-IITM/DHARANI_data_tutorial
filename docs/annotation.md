Dharani/docs/helpers

[Back] to `docs`

[Back]:README.md

# Annotation handling 

Both `DharaniHelper` and `AllenHelper` provide the function `get_annotation`, which takes a section number (int) as argument.

The function return a python `dict` where keys are `ontology_id`, and values are `shapely.Geometry`.

## Ontology IDs
The Dharani dataset has annotations marked on the high resolution images, and the annotations are named against an ontology of brain regions. The ontology can be looked up with the link below:

https://sgbc-iitm.github.io/dharani_tree.html

https://sgbc-iitm.github.io/allen_tree.html

For example, the *Corpus callosum* has id of `238` in the Dharani ontology. In the Allen ontology, the id for *Corpus callosum* is `10561`.

## Dharani Annotations
In the case of DHARANI dataset, each annotation is stored as a geojson feature, with the ontology_id, and the annotations of a section image are grouped together into a geojson featurecollection.

The handling of geojsons is simplified by `DharaniHelper.get_annotation`, which loads the features as separate `shapely` Geometry objects.

The function `get_annotation` returns a python `dict` where keys are `ontology_id`, and values are `shapely.Geometry` - i.e., each drawn feature is indexable by ontology_id. shapely provides numerous capabilities and advantages, including validity tests, computational geometry algorithms.

## Allen Annotations
In the case of the Allen developing human brain atlas dataset, each annotation is stored in svg format, using strokes. The `AllenHelper.get_annotation` function behaves identically to the Dharani counterpart, interpreting the strokes in svg, and decoding it into shapely Geometry objects.

