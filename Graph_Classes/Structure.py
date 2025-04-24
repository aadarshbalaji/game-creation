import hashlib
import json
class Node:
    def __init__(self, story, is_end=False, dialogue = ""):
        self.story = story
        self.dialogue = dialogue
        self.is_end = is_end
        self.connections = [None] * 4
        self.previous = None
        self.id = self.generate_id(story)
        self.scene_state = {}
        self.characters = {}
        self.consequences = {}
        self.backtrack = False

    def generate_id(self, story):
        return hashlib.sha256(story.encode()).hexdigest()
    
    def __repr__(self):
        return str(self.id)


class Graph:
    def __init__(self):
        self.adjacency_list = {}
        self.id_to_node = {}
    def add_node(self, node):
        if node.id not in self.id_to_node:
            self.id_to_node[node.id] = node
            self.adjacency_list[node] = {'parents': set(), 'children': set()}
    
    def add_edge(self, parent, child):
        if parent not in self.adjacency_list:
            self.add_node(parent)
        if child not in self.adjacency_list:
            self.add_node(child)
        
        self.adjacency_list[parent]['children'].add(child)
        self.adjacency_list[child]['parents'].add(parent)
    
    def get_parents(self, node):
        if node in self.adjacency_list:
            return self.adjacency_list[node]['parents']
        return None
    
    def get_node_with_id(self, id):
        return self.id_to_node.get(id, None)
    
    def get_children(self, node):
        if node in self.adjacency_list:
            return self.adjacency_list[node]['children']
        return None
    
    def _build_json_structure(self, node):
        return {str(node): {"children": [self._build_json_structure(child) for child in self.adjacency_list[node]['children']]}}
    def __repr__(self):
        root_nodes = [node for node in self.adjacency_list if not self.adjacency_list[node]['parents']]
        return json.dumps({str(node): self._build_json_structure(node)[str(node)] for node in root_nodes}, indent=4)


