import json
import s3fs
from collections import defaultdict, namedtuple
import requests

NodeRecord = namedtuple('NodeRecord','acronym,name,level,parentid,color_hex_triplet')

class TreeHelper:
    def __init__(self, ontoname='dharani'):
        if ontoname == 'dharani':
            s3 = s3fs.S3FileSystem(anon=True)
            with s3.open('dharani-fetal-brain-atlas/ontology/ontology.json') as fp:
                self.treenom = json.load(fp)['msg'][0]['children']

        elif ontoname=='allen_devhuman':
            allenonto = requests.get('http://api.brain-map.org/api/v2/structure_graph_download/16.json').json()
            self.treenom = allenonto['msg'][0]['children'][0]['children']

        # self.flatnom = json.load(open('flatnom_189.json'))['msg'][0]['children']
        
        self.groups = {
            'HPF':['HPF'], # hippocampal formation
            'AMY_BN':['AMY','BN'], # amygdala + basal nucleus
            'Mig':['Lms','Rms','GE'], # migratory areas
            'HY':['HY'], # hypothalamus
            'TH':['TH'], # thalamus
            'MB':['MB'], # midbrain
            'HB':['HB'], # hind brain
            'BS':['BS'], # brainstem 
            'CB':['CB'], # cerebellum
            'dev':['dev'], # developmental
            'ft':['ft'], # fiber tracts
            'Vs':['Vs'], # ventricles
            'Ctx':['Ctx'] # fallback cortex 
        }

        self.subtrees = {k:[] for k in self.groups}

        self.onto_lookup:dict[int,NodeRecord] = {} # id:(acronym,name,level,parentid,color_hex_triplet)

        for elt in self.treenom:
            self._find_subtrees(elt)
            self.onto_lookup[elt['id']]=NodeRecord(elt['acronym'],elt['name'],0,0,'#'+elt['color_hex_triplet'])
            if 'children' in elt:
                for child in elt['children']:
                    self._dft(child,1,elt['id'])

        # for elt in self.flatnom:
        #     if elt['id'] not in self.onto_lookup:
        #         self.onto_lookup[elt['id']]=(elt['acronym'],elt['name'],-1,-1)
    
    def _get_node_data(self,elt):
        outdict={}
        for k,v in elt.items():
            if k!='children':
                outdict[k]=v
        return outdict
    
    def _dft(self, elt, level, parentid):
        self.onto_lookup[elt['id']]=NodeRecord(elt['acronym'],elt['name'],level,parentid,'#'+elt['color_hex_triplet'])
        if 'children' in elt:
            for child in elt['children']:
                self._dft(child,level+1,elt['id'])
        

    def _find_subtrees(self,elt):
        self._check_node(elt)
        if 'children' in elt:
            for child in elt['children']:
                self._find_subtrees(child)

    def _check_node(self,elt):
        for grpname, grpparents in self.groups.items():
            if elt['acronym'] in grpparents:
                self.subtrees[grpname].append(elt)
                    
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
        idlist = []
        lastrec = self.onto_lookup[ontoid]
        while lastrec.parentid != 0:
            idlist.append(lastrec.parentid)
            lastrec = self.onto_lookup[lastrec.parentid]

        return list(reversed(idlist))
    
    def _get_node_by_ontoid(self,ontoid):
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

    def get_sibling_ids(self,ontoid:int):
        
        parentid = self.onto_lookup[ontoid].parent
        parentnode = self.get_node_by_ontoid(parentid)

        siblingids = [elt['id'] for elt in parentnode['children']]
        
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
