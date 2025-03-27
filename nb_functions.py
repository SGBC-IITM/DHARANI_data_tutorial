
from IPython.display import display, HTML
from matplotlib import pyplot as plt
from shapely.plotting import plot_polygon
import json
import shapely

from typing import Dict, List
from ontology_handling import TreeHelper
from annotation_handling import get_reachable_parents

Annotation = Dict[int,shapely.Geometry]

def print_rec(ontoid, rec, prefix=''):    
    outstr="".join(['&emsp;']*rec.level)+f'{prefix} {ontoid} {rec.acronym} {rec.name} {rec.level} '
    if len(prefix)==0:
        display(HTML(f'<p>{outstr}<span style="display:inline-block;width:20px;height:12px;padding:0px;background-color:{rec.color_hex_triplet};"></span></p>'))
    else:
        display(HTML(f'<p>{outstr}</p>'))


def plot_shape(shp,color):
    plot_polygon(shp, add_points=False, facecolor=color, edgecolor='k')

def display_annotation(im_arr, annot:'Annotation', ontohelper:'TreeHelper', selectedlev=None):
    plt.figure(figsize=(12,8))
    plt.subplot(1,2,1)
    plt.imshow(im_arr)
    
    plt.subplot(1,2,2)
    plt.imshow(im_arr)
    for ontoid,shp in sorted(annot.items()):
        rec = ontohelper.onto_lookup[ontoid]

        if selectedlev is None or rec.level == selectedlev:
            print_rec(ontoid,rec)
            color = rec.color_hex_triplet
            plot_shape(shp,color)

def display_annotation_tree(annot:'Annotation', ontohelper:'TreeHelper'):
    reachable = get_reachable_parents(annot,ontohelper)

    for par in reachable:
        ann = reachable[par][0]
        if len(ann)>0:
            print_rec(par,ontohelper.onto_lookup[par],'#')
            for oid in ann:
                print_rec(oid,ontohelper.onto_lookup[oid])
                
#%% for showing jstree

html_head_jstree ="""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jstree/3.3.12/themes/default/style.min.css" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jstree/3.3.12/jstree.min.js"></script>
    """

html_code_jstree = """
    <input type="text" id="search_input" placeholder="Search tree..." style="margin-bottom:10px;width:200px;padding:5px;"/>
    <div id="jstree_demo"></div>

    <script>
        $(document).ready(function() {
            // Initialize jstree with search plugin
            $('#jstree_demo').jstree({
                
                'core': {
                    'multiple' : false,
                    'animation' : 0,
                    'themes': {'icons':false,},
                    'data': %s,
                },                
                'plugins': ['search'],
                'search': {
                    'show_only_matches':true,
                    'show_only_matches_children':true,
                }
            });
            
            // Bind search input to jstree search function
            $('#search_input').on('keyup', function() {
                var searchValue = $(this).val();
                $('#jstree_demo').jstree(true).search(searchValue);
            });
        });
    </script>
"""


def show_jstree(ontohelper:'TreeHelper'):
    tree_data = json.dumps(ontohelper.treenom)

    display(HTML(html_head_jstree))

    display(HTML(html_code_jstree % tree_data))


#%% for showing ol 
html_head_ol="""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/openlayers/openlayers.github.io@master/en/v6.14.1/css/ol.css" type="text/css">
    <script src="https://cdn.jsdelivr.net/npm/ol@v10.4.0/dist/ol.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/geotiff"></script>
    """


html_code_ol = """
    <div id="map-container"></div>
    <script type="text/javascript">

    const sourceExtent = [0, 0, 64000, 64000];
    const olMap = new ol.Map({
        target: 'map-container',
        view: new ol.View({
        zoom: 1,
          minZoom: 10,
            maxZoom: 17,
        })
      });
      const geoTiffLayer = new ol.layer.WebGLTile({
        id: `geoTiffs`,
        zIndex: 3,
        source: new ol.source.GeoTIFF({
          sources: [
            {
              url: %s,
            },
          ],
        }),
      });

      olMap.addLayer(geoTiffLayer);
      olMap.getView().fit(sourceExtent);
    </script>
"""

def show_inline_viewer(imageurl:str):
    # 'https://dharani-fetal-brain-atlas.s3.us-west-2.amazonaws.com/data2d/specimen_2/Specimen_2_1000.tif'
    # use helper.get_section_urls

    display(HTML(html_head_ol))

    display(HTML(html_code_ol % imageurl))

