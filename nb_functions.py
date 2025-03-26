
from IPython.display import display, HTML
from matplotlib import pyplot as plt
from shapely.plotting import plot_polygon
import json

def print_rec(ontoid,rec):    
    outstr="".join(['&emsp;']*rec.level)+f'{ontoid} {rec.acronym} {rec.name} {rec.level} '
    display(HTML(f'<p>{outstr}<span style="display:inline-block;width:20px;height:12px;padding:0px;background-color:{rec.color_hex_triplet};"></span></p>'))

def plot_shape(shp,color):
    plot_polygon(shp, add_points=False, facecolor=color, edgecolor='k')

def display_annotation(im_arr, annot, ontohelper, selectedlev=None):
    plt.figure(figsize=(12,8))
    plt.subplot(1,2,1)
    plt.imshow(im_arr)
    
    plt.subplot(1,2,2)
    plt.imshow(im_arr)
    for ontoid,shp in annot.items():
        rec = ontohelper.onto_lookup[ontoid]

        if selectedlev is None or rec.level == selectedlev:
            print_rec(ontoid,rec)
            color = rec.color_hex_triplet
            plot_shape(shp,color)

#%% for showing jstree

html_head="""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jstree/3.3.12/themes/default/style.min.css" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jstree/3.3.12/jstree.min.js"></script>
    """

html_code = """
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


def show_jstree(ontohelper):
    tree_data = json.dumps(ontohelper.treenom)

    display(HTML(html_head))

    display(HTML(html_code % tree_data))
    