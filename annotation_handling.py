from collections import defaultdict


def get_supershape(ontoid, annot, ontohelper):
    #  construct parent shapes by merging shapes 

    if ontoid in annot:
        return annot[ontoid]
    
    parshp = None
    chlist = []
    for annot_id in annot:
        anclist = ontohelper.get_ancestor_ids(annot_id)
        if ontoid in anclist:
            chlist.append(annot_id)
            if parshp is None:
                parshp = annot[annot_id]
            else:
                parshp = parshp.union(annot[annot_id])
    
    return parshp, chlist

def find_superids(annot,ontohelper):

    superids = defaultdict(list)

    for ontoid in annot:
        parentids = ontohelper.get_ancestor_ids(ontoid)
        
        for drawnid in annot:
            if drawnid in parentids:
                superids[drawnid].append(ontoid)

    return superids
    
    