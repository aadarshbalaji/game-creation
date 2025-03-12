import hashlib
import json
class Node:
    def __init__(self, story, is_end=False):
        self.story = story
        self.is_end = is_end
        self.connections = [None] * 4
        self.previous = None
        self.id = self.generate_id(story)

    def generate_id(self, story):
        return hashlib.sha256(story.encode()).hexdigest()
    
    def __repr__(self):
        return str(self.id)


class Graph:
    def __init__(self):
        self.adjacency_list = {}
        self.id_to_node = {}
    def add_node(self, node):
        if node.id not in self.node_map:
            self.node_map[node.id] = node
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
    
    def __repr__(self):
        return json.dumps({str(node): {'parents': list(map(str, data['parents'])), 'children': list(map(str, data['children']))} for node, data in self.adjacency_list.items()}, indent=4)


#Example Usage:
node1 = Node('Once upon a time...')
node2 = Node('There was a princess...')
node3 = Node('She lived in a castle...', is_end=True)

graph = Graph()
graph.add_node(node1)
graph.add_node(node2)
graph.add_node(node3)

graph.add_edge(node1, node2)
graph.add_edge(node1, node3)

print(graph.get_children(graph.get_node_with_id('7cc6caf901b894033626981cd102021727aa59c2548d79e59382649b2c6f50f2')))