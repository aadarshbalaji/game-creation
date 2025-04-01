from Graph_Classes.Structure import Node, Graph
from Graph_Classes.Interact import Player
import os
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_story(node):
    print("\n" + "="*50)
    print(node.story)
    print("="*50 + "\n")

def create_story_graph():
    # Create nodes for our story
    start = Node("You wake up in a mysterious room. The air is thick with anticipation. The room is dimly lit by a single candle on a wooden desk. You notice a dusty book on the desk and a strange symbol carved into the wall.")
    
    # First set of choices
    examine_book = Node("You carefully open the dusty book. It's written in an ancient language, but you can make out some words about a hidden treasure and a powerful artifact.")
    examine_symbol = Node("The symbol on the wall seems to glow faintly as you touch it. It looks like a combination of a dragon and a key.")
    look_around = Node("Looking around the room more carefully, you notice a loose floorboard near the desk and a small keyhole in the wall.")
    sit_and_think = Node("You sit down and try to remember how you got here. Your mind is foggy, but you recall a strange dream about a dragon.")
    
    # Second set of choices
    read_book = Node("As you read more of the book, you discover it's a diary of an ancient wizard who hid a powerful artifact in this very castle.")
    touch_symbol = Node("When you touch the glowing symbol, it begins to shift and change, revealing a hidden compartment in the wall.")
    check_floorboard = Node("You carefully lift the floorboard and find a small golden key hidden underneath.")
    meditate = Node("You close your eyes and meditate, hoping to clear your mind. You feel a strange energy coursing through you.")
    
    # Third set of choices
    find_artifact = Node("Following the diary's instructions, you locate the hidden artifact - a magical amulet that grants its wearer the power to control dragons!")
    dragon_encounter = Node("Suddenly, a massive dragon appears from the shadows! It seems the symbol you touched was actually a dragon's seal.")
    escape_attempt = Node("You try to escape through the window, but the dragon's breath has weakened the castle walls!")
    unlock_memory = Node("Your meditation unlocks a memory of a secret passage in the castle. You decide to find it.")
    
    # Fourth set of choices
    confront_dragon = Node("With the amulet in hand, you bravely confront the dragon, ready to tame it.")
    hide_from_dragon = Node("You hide behind a pillar, hoping the dragon doesn't notice you.")
    search_for_exit = Node("You search frantically for an exit, knowing the dragon is close.")
    follow_memory = Node("You follow the memory's guidance and find a hidden door leading to safety.")
    
    # End nodes
    victory = Node("With the dragon-controlling amulet in your possession, you successfully tame the dragon and escape the castle as its new master. Congratulations!", is_end=True)
    defeat = Node("The dragon's fiery breath proves too powerful. Despite your best efforts, you succumb to the flames. Game Over!", is_end=True)
    escape = Node("Using the golden key, you unlock a secret passage and escape the castle just as it collapses. You live to tell the tale!", is_end=True)
    safe_haven = Node("You find a safe haven beyond the hidden door, where you can rest and plan your next move. You've survived for now.", is_end=True)

    # Create the graph
    graph = Graph()
    
    # Add all nodes
    nodes = [start, examine_book, examine_symbol, look_around, sit_and_think,
             read_book, touch_symbol, check_floorboard, meditate,
             find_artifact, dragon_encounter, escape_attempt, unlock_memory,
             confront_dragon, hide_from_dragon, search_for_exit, follow_memory,
             victory, defeat, escape, safe_haven]
    
    for node in nodes:
        graph.add_node(node)
    
    # Add edges to create the story paths
    # First level
    graph.add_edge(start, examine_book)
    graph.add_edge(start, examine_symbol)
    graph.add_edge(start, look_around)
    graph.add_edge(start, sit_and_think)
    
    # Second level
    graph.add_edge(examine_book, read_book)
    graph.add_edge(examine_symbol, touch_symbol)
    graph.add_edge(look_around, check_floorboard)
    graph.add_edge(sit_and_think, meditate)
    
    # Third level
    graph.add_edge(read_book, find_artifact)
    graph.add_edge(touch_symbol, dragon_encounter)
    graph.add_edge(check_floorboard, escape_attempt)
    graph.add_edge(meditate, unlock_memory)
    
    # Fourth level
    graph.add_edge(find_artifact, confront_dragon)
    graph.add_edge(dragon_encounter, hide_from_dragon)
    graph.add_edge(escape_attempt, search_for_exit)
    graph.add_edge(unlock_memory, follow_memory)
    
    # Ensure each node has 4 choices
    # Adding loops for choices to ensure 4 options
    graph.add_edge(confront_dragon, confront_dragon)  # Loop back to itself
    graph.add_edge(confront_dragon, hide_from_dragon)  # Additional choice
    graph.add_edge(confront_dragon, search_for_exit)  # Additional choice
    graph.add_edge(confront_dragon, follow_memory)  # Additional choice
    
    graph.add_edge(hide_from_dragon, confront_dragon)  # Loop back to itself
    graph.add_edge(hide_from_dragon, search_for_exit)  # Additional choice
    graph.add_edge(hide_from_dragon, follow_memory)  # Additional choice
    graph.add_edge(hide_from_dragon, victory)  # Additional choice
    
    graph.add_edge(search_for_exit, confront_dragon)  # Loop back to itself
    graph.add_edge(search_for_exit, hide_from_dragon)  # Additional choice
    graph.add_edge(search_for_exit, follow_memory)  # Additional choice
    graph.add_edge(search_for_exit, escape)  # Additional choice
    
    graph.add_edge(follow_memory, confront_dragon)  # Loop back to itself
    graph.add_edge(follow_memory, hide_from_dragon)  # Additional choice
    graph.add_edge(follow_memory, search_for_exit)  # Additional choice
    graph.add_edge(follow_memory, safe_haven)  # Additional choice
    
    return graph, start

def main():
    clear_screen()
    print("Welcome to the Dragon's Castle Adventure!")
    print("========================================")
    
    # Get player name
    player_name = input("\nEnter your name: ")
    
    # Create the story graph and get starting node
    graph, start_node = create_story_graph()
    
    # Create player
    player = Player(player_name, start_node)
    
    # Main game loop
    while not player.is_dead:
        clear_screen()
        
        # Show current story node
        print_story(player.current_node)
        
        # Show player status
        print("\nYour Status:")
        print(f"Health: {player.health}")
        print(f"Experience: {player.experience}")
        print(f"Inventory: {', '.join(player.inventory) if player.inventory else 'Empty'}")
        
        # Get available choices
        choices = graph.get_children(player.current_node)
        if not choices:
            print("\nYou've reached the end of this path!")
            break
        
        # Show choices
        print("\nAvailable choices:")
        for i, choice in enumerate(choices, 1):
            print(f"{i}. {choice.story[:50]}...")
        
        # Get player choice
        while True:
            try:
                choice = int(input(f"\nEnter your choice (1-{len(choices)}): "))
                if 1 <= choice <= len(choices):
                    # Move to the chosen node
                    next_node = list(choices)[choice - 1]
                    player.move(graph, next_node)
                    break
                else:
                    print(f"Please enter a number between 1 and {len(choices)}")
            except ValueError:
                print("Please enter a valid number.")
        
        # Add some delay for dramatic effect
        time.sleep(1)
    
    # Game over
    clear_screen()
    print("\nGame Over!")
    print("==========")
    print(f"Final Status:")
    print(f"Health: {player.health}")
    print(f"Experience: {player.experience}")
    print(f"Path taken: {' -> '.join(str(node) for node in player.traversed_nodes)}")

if __name__ == "__main__":
    main() 