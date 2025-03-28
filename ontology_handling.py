import json
import s3fs
from collections import defaultdict, namedtuple
import requests

from rapidfuzz.process import extract as fuzzy_similarity
from rapidfuzz import fuzz


NodeRecord = namedtuple('NodeRecord','acronym,name,color_hex_triplet,level,parentid,numchildren')

class TreeHelper:
    """
    Abstracts ontology tree reading, searching and navigation for Dharani and Allen nomenclature
    """

    def __init__(self, ontoname='dharani'):
        """ ontoname: ['dharani', 'allen_devhuman'] """

        if ontoname == 'dharani':
            s3 = s3fs.S3FileSystem(anon=True)
            with s3.open('dharani-fetal-brain-atlas/ontology/ontology.json') as fp:
                self.treenom = json.load(fp)['msg'][0]['children']

        elif ontoname=='allen_devhuman':
            allenonto = requests.get('http://api.brain-map.org/api/v2/structure_graph_download/16.json').json()
            self.treenom = allenonto['msg'][0]['children'][0]['children']

        # self.flatnom = json.load(open('flatnom_189.json'))['msg'][0]['children']
        
        self.groups = {
            'HPF':['HPF','HIP'], # hippocampal formation
            'AMY_BN':['AMY','BN','CN'], # amygdala + basal nucleus, cerebral nuclei
            'Mig':['Lms','Rms','GE','FTS'], # migratory areas, transient structures of forebrain
            'HY':['HY','HTH'], # hypothalamus
            'TH':['TH','THM'], # thalamus
            'MB':['MB','M'], # midbrain
            'HB':['HB','H'], # hind brain
            'BS':['BS'], # brainstem 
            'CB':['CB'], # cerebellum
            'dev':['dev'], # developmental
            'ft':['ft','FWM'], # fiber tracts
            'Vs':['Vs','FV'], # ventricles
            'Ctx':['Ctx','FGM'] # fallback cortex 
        }

        self.subtrees = {k:[] for k in self.groups}

        self.onto_lookup:dict[int,NodeRecord] = {} # id:(acronym,name,level,parentid,color_hex_triplet)

        self.ontoids_by_group:dict[str,list] = {k:[] for k in self.groups}

        for elt in self.treenom:
            self._find_subtrees(elt)

            if 'text' not in elt:
                elt['text']=elt['acronym'] + ' : ' + elt['name']
            
            numchildren = 0
            if 'children' in elt:
                numchildren =len(elt['children'])
            self.onto_lookup[int(elt['id'])]=NodeRecord(elt['acronym'],elt['name'],'#'+elt['color_hex_triplet'],0,0,numchildren)
            if 'children' in elt:
                for child in elt['children']:
                    self._dft(child,1,int(elt['id']))

        # for elt in self.flatnom:
        #     if elt['id'] not in self.onto_lookup:
        #         self.onto_lookup[elt['id']]=(elt['acronym'],elt['name'],-1,-1)

        self.search_dict = {k:v.name.lower() for k,v in self.onto_lookup.items()}
    
    def __len__(self):
        return len(self.onto_lookup)
    
    def _get_node_data(self,elt):
        outdict={}
        for k,v in elt.items():
            if k!='children':
                outdict[k]=v
        return outdict
    
    def _dft(self, elt, level, parentid):
        
        if 'text' not in elt:
            elt['text']=elt['acronym'] + ' : ' + elt['name']
        
        numchildren = 0
        if 'children' in elt:
            numchildren =len(elt['children'])
        self.onto_lookup[int(elt['id'])]=NodeRecord(elt['acronym'],elt['name'],'#'+elt['color_hex_triplet'],level,parentid,numchildren)

        if 'children' in elt:
            for child in elt['children']:
                self._dft(child,level+1,int(elt['id']))
        

    def _find_subtrees(self,elt, grprootname=None):
        foundgrp=self._check_node(elt)
        if foundgrp is not None:
            self.ontoids_by_group[foundgrp].append(elt['id'])
        if grprootname is not None:
            self.ontoids_by_group[grprootname].append(elt['id'])
        if 'children' in elt:
            for child in elt['children']:
                self._find_subtrees(child, foundgrp or grprootname)

    def _check_node(self,elt):
        for grpname, grpparents in self.groups.items():
            if elt['acronym'] in grpparents:
                self.subtrees[grpname].append(elt)
                return grpname
        return None            
    # def get_group_by_acronym(self, rgnname):
    #     for grpname in self.subtrees:
    #         for subtr in self.subtrees[grpname]:
    #             if self._find_node_by_acronym(subtr,rgnname):
    #                 return grpname
    #     return None

    # def _find_node_by_acronym(self,seednode, rgnname):
    #     if seednode['acronym']==rgnname:
    #         return True
    #     if 'children' in seednode:
    #         for child in seednode['children']:
    #             if self._find_node_by_acronym(child, rgnname):
    #                 return True
    #     return False

    # def get_group_by_ontoid(self, ontoid):
    #     for grpname in self.subtrees:
    #         for subtr in self.subtrees[grpname]:
    #             if self._find_node_by_id(subtr, ontoid):
    #                 return grpname

    # def _find_node_by_id(self, seednode, ontoid):
    #     # dfs
    #     if seednode['id']==ontoid:
    #         return True
    #     if 'children' in seednode:
    #         for child in seednode['children']:
    #             if self._find_node_by_id(child, ontoid):
    #                 return True
    #     return False
              
    def get_ancestor_ids(self, ontoid:int):
        """get a list of ancestor ids, general to specialized"""
        idlist = []
        if ontoid>0:
            lastrec = self.onto_lookup[ontoid]
            while lastrec.parentid != 0:
                idlist.append(lastrec.parentid)
                lastrec = self.onto_lookup[lastrec.parentid]

        return list(reversed(idlist))
    
    def get_full_name_by_ontoid(self,ontoid:int):
        anclist = self.get_ancestor_ids(ontoid)
        fullname = ""
        fullacro = ""
        for anc in anclist:
            ancrec = self.onto_lookup[anc]
            fullname+=ancrec.name+'/'
            fullacro+=ancrec.acronym+'/'

        return fullname[:-1], fullacro[:-1] # skip trailing /
    
    def _get_node_by_ontoid(self,ontoid:int):
        ancestorids = self.get_ancestor_ids(ontoid)
        ancnode = None
        
        for elt in self.treenom:
            # print(elt['id'])
            if elt['id'] in ancestorids:
                ancnode = elt
                break

        # traverse ancestors from root down, to get the parentnode
        node = None
        while node is None:
            # print(ancnode['id'])
            if 'children' in ancnode:
                for ch in ancnode['children']:
                    if ch['id'] in ancestorids:
                        ancnode = ch 
                    elif ch['id']==ontoid:
                        node = ch
                        break
            else:
                break

        return node

    def get_children_ids(self, ontoid:int):
        nd = self._get_node_by_ontoid(ontoid)
        if 'children' in nd:
            return [int(ch['id']) for ch in nd['children']]
        return []

    def get_sibling_ids(self,ontoid:int):
        
        parentid = self.onto_lookup[ontoid].parentid
        parentnode = self._get_node_by_ontoid(parentid)

        siblingids = [int(elt['id']) for elt in parentnode['children']]
        
        return siblingids
    

    def get_group_by_ontoid(self, ontoid:int):

        ancestorids = self.get_ancestor_ids(ontoid)
        for grpname in self.subtrees:
            for subtr in self.subtrees[grpname]:
                if subtr['id'] in ancestorids or subtr['id']==ontoid:
                    return grpname
        
        return None
    
    def _get_id_by_acronym(self,acro:str):
        for id, rec in self.onto_lookup.items():
            if acro == rec.acronym:
                return id
        return None
    
    def get_group_by_acronym(self, acro:str):
        ontoid = self._get_id_by_acronym(acro)
        if ontoid is not None:
            return self.get_group_by_ontoid(ontoid)
        return None

    def print_tree(self):
        print('[lvl] id (acronym) name')
        print('---------------------')
        for toplevel in self.treenom:
            # print(toplevel['id'],toplevel['name'])
            self._show_children(toplevel)
        
    def _show_children(self,elt,level=0):
        lvlstr='[%d]'%level
        if '-' in elt['acronym']:
            parts = elt['acronym'].split('-')
            if parts[0] in ('SGL','MZ','CP','SP','IZ','SVZ','VZ'):
                lvlstr = '[*]'
                
        print(''.join(['  ']*level),lvlstr, elt['id'],'('+elt['acronym']+')',elt['name'])
        if 'children' not in elt:
            pass
            # print('@no children')
        else:
            if len(elt['children'])>0:
                for child in elt['children']:
                    self._show_children(child,level+1)


    def get_ids_by_level(self,level:int):
        idlist = []
        for id,rec in self.onto_lookup.items():
            if rec.level==level:
                idlist.append(id)

        return idlist

    def get_ids_of_cortical_areas(self):
        idlist = defaultdict(list)
        areanamesuffixes = ['-FCTx', '-ORB', '-PAR', '-OCC', '-TEMP', '-INS', '-CING', '-ENT']

        for id,rec in self.onto_lookup.items():
            for areanamesuffix in areanamesuffixes:
                if rec.acronym.endswith(areanamesuffix):
                    idlist[areanamesuffix].append(id)
        
        return idlist
    
    def get_ids_of_layered_areas(self):
        # FIXME: this is dharani-specific - can be generalized to Allen ontology
        idlist = defaultdict(list)
        zoneprefixes = ['SGL-','MZ-','CP-','SP-','IZ-','SVZ-','VZ-']

        for id,rec in self.onto_lookup.items():
            for zoneprefix in zoneprefixes:
                if rec.acronym.startswith(zoneprefix) and rec.acronym!=zoneprefix+'CTX':
                    idlist[zoneprefix].append(id)
        return idlist
    
    def print_subtree(self, grpname:str):
        print('[lvl] id (acronym) name')
        print('---------------------')
        for root in self.subtrees[grpname]:
            self._show_children(root)


    def print_subtree_at_id(self, ontoid:int):
        nd = self._get_node_by_ontoid(ontoid)
        lev = self.onto_lookup[ontoid].level
        self._show_children(nd,lev)

    def search(self, searchstr, partial=False, num_results=5):
        # set num_results to -1 for no limit
        query = searchstr.lower() # .replace(',', ' in')
        scorer = fuzz.ratio
        if partial:
            scorer=fuzz.partial_token_sort_ratio
        ret = fuzzy_similarity(query, self.search_dict, scorer=scorer, score_cutoff=85, limit=num_results)

        if not partial:
            for elt in ret:
                if elt[1]==100:
                    ret = [elt] # suppress other elts
                    break
        if len(ret)==0 and not partial:
            ret = fuzzy_similarity(query, self.search_dict, scorer=fuzz.token_ratio, score_cutoff=90, limit=5)
        
        if len(ret)==0:
            ret = fuzzy_similarity(query, self.search_dict, scorer=fuzz.partial_token_sort_ratio, score_cutoff=90, limit=5)

        if ' of ' not in searchstr:

            out = []
            for elt in ret:                
                if ' of ' not in elt[0]:
                    out.append(elt)
            
            ret = out

        return ret
    