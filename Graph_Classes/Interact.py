from Structure import Graph, Node


class Player:
    def __init__(self, name, start_node):
        self.name = name
        self.current_node = start_node
        self.traversed_nodes = [start_node] #can be changed for just checkpoints
        self.inventory = []
        self.health = 100
        self.experience = 0
        self.is_dead = False

    def get_checkpoint(self):
        if self.traversed_nodes:
            return self.traversed_nodes[-1]
        return None
    
    def move(self, graph, new_node):
        if new_node in graph.get_children(self.current_node):
            self.current_node = new_node
            self.traversed_nodes.append(new_node)
            self.experience += 10  # Gain experience for moving
            print(f"{self.name} moved to {new_node}")
        else:
            print(f"{new_node} is not accessible from {self.current_node}")
    
    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            print(f"{self.name} has died!")
    
    def heal(self, amount):
        if not self.is_dead:
            self.health = min(100, self.health + amount)
            print(f"{self.name} healed to {self.health} HP")
    
    def collect_item(self, item):
        self.inventory.append(item)
        print(f"{self.name} collected {item}")

    def show_choices(self, graph):
        choices = graph.get_children(self.current_node)
        if choices:
            print(f"Choices from {self.current_node}: {', '.join(map(str, choices))}")
        else:
            print(f"No available moves from {self.current_node}")


    
    def show_status(self):
        print(f"Player: {self.name}\nCurrent Node: {self.current_node}\nHealth: {self.health}\nExperience: {self.experience}\nInventory: {self.inventory}\nTraversed Nodes: {self.traversed_nodes}\nIs Dead: {self.is_dead}")

node1 = Node('Once upon a time...')
node2 = Node('There was a princess...')
node3 = Node('She lived in a castle...', is_end=True)
node4 = Node('The castle was guarded by a dragon...')
graph = Graph()
graph.add_node(node1)
graph.add_node(node2)
graph.add_node(node3)

graph.add_edge(node1, node2)
graph.add_edge(node1, node3)
graph.add_edge(node3, node4)
p1 = Player('Alice',  node1)
#p1.move(graph, node2)
print(graph)