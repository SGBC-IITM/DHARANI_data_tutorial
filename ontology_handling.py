import json
import s3fs
from collections import defaultdict, namedtuple

NodeRecord = namedtuple('NodeRecord','acronym,name,level,parentid')

class TreeHelper:
    def __init__(self):
        s3 = s3fs.S3FileSystem(anon=True)
        with s3.open('dharani-fetal-brain-atlas/ontology/ontology.json') as fp:
            self.treenom = json.load(fp)['msg'][0]['children']
        
        # self.flatnom = json.load(open('flatnom_189.json'))['msg'][0]['children']
        
        self.groups = {
            'HPF':['HPF'], # hippocampal formation
            'AMY_BN':['AMY','BN'], # amygdala + basal nucleus
            'Mig':['Lms','Rms','GE'], # migratory areas
            'HY':['HY'], # hypothalamus
            'TH':['TH'], # thalamus
            'MB':['MB'], # midbrain
            'HB':['HB'], # hind brain 
            'CB':['CB'], # cerebellum
            'dev':['dev'], # developmental
            'ft':['ft'], # fiber tracts
            'Vs':['Vs'], # ventricles
            'Ctx':['Ctx'] # fallback cortex 
        }

        self.subtrees = {k:[] for k in self.groups}

        self.onto_lookup = {} # id:(acronym,name,level,parentid)

        for elt in self.treenom:
            self._find_subtrees(elt)
            self.onto_lookup[elt['id']]=NodeRecord(elt['acronym'],elt['name'],0,0)
            if 'children' in elt:
                for child in elt['children']:
                    self.dft(child,1,elt['id'])

        # for elt in self.flatnom:
        #     if elt['id'] not in self.onto_lookup:
        #         self.onto_lookup[elt['id']]=(elt['acronym'],elt['name'],-1,-1)
    
    def dft(self, elt, level, parentid):
        self.onto_lookup[elt['id']]=NodeRecord(elt['acronym'],elt['name'],level,parentid)
        if 'children' in elt:
            for child in elt['children']:
                self.dft(child,level+1,elt['id'])
        

    def _find_subtrees(self,elt):
        self._check_node(elt)
        if 'children' in elt:
            for child in elt['children']:
                self._find_subtrees(child)

    def _check_node(self,elt):
        for grpname, grpparents in self.groups.items():
            if elt['acronym'] in grpparents:
                self.subtrees[grpname].append(elt)
                    
    def get_group_by_name(self, rgnname):
        for grpname in self.subtrees:
            for subtr in self.subtrees[grpname]:
                if self._find_node_by_name(subtr,rgnname):
                    return grpname
        return None

    def _find_node_by_name(self,seednode, rgnname):
        if seednode['acronym']==rgnname:
            return True
        if 'children' in seednode:
            for child in seednode['children']:
                if self._find_node_by_name(child, rgnname):
                    return True
        return False

    def get_group_by_ontoid(self, ontoid):
        for grpname in self.subtrees:
            for subtr in self.subtrees[grpname]:
                if self._find_node_by_id(subtr, ontoid):
                    return grpname

    def _find_node_by_id(self, seednode, ontoid):
        if seednode['id']==ontoid:
            return True
        if 'children' in seednode:
            for child in seednode['children']:
                if self._find_node_by_id(child, ontoid):
                    return True
        return False
              
        
    def print_tree(self):
        print('[lvl] id (acronym) name')
        print('---------------------')
        for toplevel in self.treenom:
            # print(toplevel['id'],toplevel['name'])
            self.show_children(toplevel)
        
    def show_children(self,elt,level=0):
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
                    self.show_children(child,level+1)


    def get_ids_by_level(self,level):
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
    
    def print_subtree(self, grpname):
        print('[lvl] id (acronym) name')
        print('---------------------')
        for root in self.subtrees[grpname]:
            self.show_children(root)
