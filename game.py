import time
import json
import os
import re
import textwrap
from arc import return_story_arc, return_story_tree
from storygen import StoryState, generate_initial_story, generate_story_node, save_game_state, load_game_state
from Graph_Classes.Structure import Node, Graph
from Graph_Classes.Interact import Player

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
    pass


def wrap_text(text, width=70):
    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 <= width:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)

    if current_line:
        lines.append(' '.join(current_line))
    return '\n'.join(lines)

def print_box(text, width=70, padding=1):
    """Print text in a decorative box"""
    horizontal = "+" + "-" * width + "+"
    empty = "|" + " " * width + "|"
    
    print(horizontal)
    for _ in range(padding):
        print(empty)
    
    for line in wrap_text(text, width-2).split('\n'):
        print(f"| {line:<{width-2}} |")
    
    for _ in range(padding):
        print(empty)
    print(horizontal)

def print_box_dialogue(raw_dialogue: str, width: int = 70, padding: int = 1):
    """
    Prints dialogue inside a decorative box, inserting line breaks before each speaker tag '['
    (except at start), breaking lines at literal '\\n' or real newlines, and wrapping each part
    to fit within the box width.
    """
    dialogue = re.sub(r'\\\\n|\\n|\n', '\n', raw_dialogue)
    dialogue = re.sub(r'(?<!^)\[', r'\n[', dialogue)
    wrapped_lines = []
    for part in dialogue.splitlines():
        part = part.strip()
        if part:
            wrapped = textwrap.wrap(part, width=width-4) or ['']
            wrapped_lines.extend(wrapped)

    horizontal = "+" + "-" * width + "+"
    empty = "|" + " " * width + "|"
    print(horizontal)
    for _ in range(padding):
        print(empty)
    for line in wrapped_lines:
        print(f"| {line:<{width-2}} |")
    for _ in range(padding):
        print(empty)
    print(horizontal)

def print_state(title, data, indent=2):
    """Print state information in a formatted way"""
    print(f"\n{'='*20} {title} {'='*20}")
    
    if title == "CHARACTERS PRESENT":
        # Check if the main data is a dictionary before using .items()
        if isinstance(data, dict):
            for char_name, char_data in data.items():
                if char_name == "player":
                    continue  
                
                if char_name == "other_characters":
                    # Check if the value under 'other_characters' is also a dict
                    if isinstance(char_data, dict):
                        for npc_name, npc_data in char_data.items():
                            print(f"\n► {npc_name.upper()}")
                            if isinstance(npc_data, dict):
                                health = npc_data.get('health', 0)
                                health_bar = '♥' * (health // 10) + '░' * ((100 - health) // 10)
                                print(f"  Health: [{health_bar}] {health}/100")
                                
                                mood = npc_data.get('mood', 'unknown')
                                mood_emoji = {
                                    'angry': '😠', 'happy': '😊', 'sad': '😢', 
                                    'afraid': '😨', 'determined': '😤', 'sleeping': '😴',
                                    'neutral': '😐', 'aggressive': '😠', 'friendly': '🙂',
                                    'fearful': '😨', 'panicked': '😰', 'suspicious': '🤨'
                                }.get(mood.lower(), '❓')
                                print(f"  Mood: {mood_emoji} {mood}")
                            
                                if npc_data.get('status_effects'):
                                    effects = ', '.join(npc_data['status_effects'])
                                    print(f"  Status Effects: ✨ {effects}")
                                
                                if npc_data.get('relationships'):
                                    print("  Relationships:")
                                    # Check if relationships is a dict before iterating
                                    if isinstance(npc_data['relationships'], dict):
                                        for target, relation in npc_data['relationships'].items():
                                            print(f"   • {target}: {relation}")
                                    else:
                                        print(f"    (Unexpected relationship format: {type(npc_data['relationships'])})")
                            else:
                                print(f"  (Unexpected data format for NPC {npc_name}: {type(npc_data)})")
                    # Handle case where 'other_characters' value is not a dict (e.g., a list)
                    elif isinstance(char_data, list):
                        print("\n► OTHER CHARACTERS (List Format)")
                        for item in char_data:
                            if isinstance(item, dict):
                                name = item.get('name', 'Unknown NPC')
                                print(f"  • {name}") # Basic display for list format
                                # Add more details here if needed and format is known
                            else:
                                print(f"  • Unknown item data: {item}")
                    else:
                        print(f"\n(Unexpected format for 'other_characters': {type(char_data)})")
                else:
                    # Handles other top-level keys like custom character names
                    print(f"\n► {char_name.upper()}")
                    # Optionally print details from char_data if it's a dict
                    if isinstance(char_data, dict):
                       # Example: print mood if available
                       mood = char_data.get('mood', None)
                       if mood:
                           print(f"  Mood: {mood}")
                    # Add more handling as needed
        # Handle case where the top-level 'data' is not a dictionary
        elif isinstance(data, list):
            print("\n(Warning: Character data received in unexpected list format)")
            for item in data:
                 if isinstance(item, dict):
                     name = item.get('name', 'Unknown Character')
                     print(f"\n► {name.upper()} (from list)")
                 else:
                     print(f"\n► Unknown Character Data (from list): {item}")
        else:
             print(f"\n(Warning: Unexpected character data format received: {type(data)})")
    
    elif title == "CURRENT SCENE":
        # Make sure data is a dict before accessing keys
        if isinstance(data, dict):
            print(f"\n🌍 Location: {data.get('location', 'Unknown')}")
            print(f"🕒 Time: {data.get('time_of_day', 'Unknown')}")
            print(f"🌤️  Weather: {data.get('weather', 'Unknown')}")
            print(f"💫 Ambient: {data.get('ambient', 'Unknown')}")
        else:
            print(f"\n(Warning: Unexpected scene data format: {type(data)})")
            print(f"Raw Scene Data: {data}")
    
    print("\n" + "=" * (42 + len(title)))



def main():
    clear_screen()
    print("Welcome to Netflix's AI-Generated CYOA!")
    print("=" * 50)
    
    player_name = input("\nEnter your name: ")
    story_theme = input("\nWhat kind of story would you like to experience?\n(e.g., Star Wars, Lord of the Rings, Dracula, your own movie idea): ")
    while True:
        try:
            max_depth_str = input("\nEnter the desired depth for the pre-generated story (e.g., 5, leave blank for minimal pre-generation = 1): ")
            if not max_depth_str:
                max_depth = 1
                print("Defaulting to pre-generation depth of 1.")
                break
            max_depth = int(max_depth_str)
            if max_depth <= 0:
                print("Please enter a positive number for the pre-generation depth.")
            else:
                break
        except ValueError:
            print("Invalid input. Please enter a number or leave blank.")

    try:
        # Generate story arc first
        story_arc = return_story_arc(story_theme)
        
        # Generate a small story tree template
        story_tree_file = return_story_tree(story_theme)
        try:
            with open(story_tree_file, 'r') as f:
                story_tree = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading story tree: {e}")
            print("Continuing without a template story tree.")
            story_tree = {}
        
        # Load the game state with the correct parameter names and max_depth (for pre-generation)
        graph, story_state = load_game_state(theme=story_theme, story_arc=story_arc, story_tree=story_tree, max_depth=max_depth)
        print(graph)
        # Ensure start_node is correctly identified after loading/generation
        if not graph or not graph.adjacency_list:
             raise Exception("Failed to load or generate a valid starting node.")
        start_node = next(iter(graph.adjacency_list)) # Assumes the first node added is the start

        player = Player(player_name, start_node)

        # Modified game loop condition - removed max_depth check
        while not player.is_dead and \
              not player.current_node.is_end:
            clear_screen()
            print_box(player.current_node.story)
            if player.current_node.dialogue:
                print_box_dialogue(player.current_node.dialogue)
            print_state("CURRENT SCENE", player.current_node.scene_state)
            print_state("CHARACTERS PRESENT", player.current_node.characters)

            print("\n🎮 YOUR STATUS 🎮")
            print(f"╔{'═'*50}╗")
            print(f"║ {player.name:<48} ║")
            print(f"║ Health: [{'♥' * (player.health // 10)}{'░' * ((100 - player.health) // 10)}] {player.health:>3}/100 ║")
            print(f"║ Experience: [{'✦' * (player.experience // 10)}{'░' * ((100 - player.experience) // 10)}] {player.experience:>3} ║")
            if player.inventory:
                print(f"║ 🎒 Inventory:                                          ║")
                for item in player.inventory:
                    print(f"║  • {item:<46} ║")
            else:
                print(f"║ 🎒 Inventory: Empty                                    ║")
            print(f"╚{'═'*50}╝")
            
            choices = list(graph.get_children(player.current_node))
            generation_failed_or_empty = False # Flag for fallback ending
            # Dynamic generation logic if no children exist in the (potentially pre-generated) graph
            if not choices and not player.current_node.is_end:
                print("\nNo pre-generated paths found. Generating new story paths dynamically...")
                try:
                    # Get current step count
                    current_step_count = len(player.traversed_nodes)

                    story_context = {
                        "previous_scene": player.current_node.story,
                        "current_location": player.current_node.scene_state['location'],
                        "time_of_day": player.current_node.scene_state['time_of_day'],
                        "weather": player.current_node.scene_state['weather'],
                        "player_status": {
                            "health": player.health,
                            "inventory": player.inventory
                        },
                        "characters": player.current_node.characters,
                        "recent_events": [node.story for node in player.traversed_nodes[-3:]],
                        # Add step count to context
                        "current_step_count": current_step_count
                    }
                    
                    choice_data = generate_story_node(story_context, story_state, story_arc, story_tree)
                    
                    # Check if generation actually yielded choices
                    if not choice_data or not choice_data.get("choices"):
                        print("\nWarning: AI generation returned no valid choices.")
                        generation_failed_or_empty = True
                    else:
                        # Process valid choices
                        for choice in choice_data["choices"]:
                            new_node = Node(choice["text"], choice_data.get("is_ending", False), choice.get("dialogue", ""))
                            new_node.scene_state = choice_data["scene_state"]
                            new_node.characters = choice_data["characters"]
                            new_node.consequences = choice["consequences"]
                            new_node.backtrack = choice.get("can_backtrack", False)
                            # Add ending type and reason if this is an ending node
                            if choice_data.get("is_ending"):
                                new_node.ending_type = choice_data.get("ending_type", "neutral")
                                new_node.ending_reason = choice_data.get("ending_reason", "The story has reached its conclusion.")
                            graph.add_node(new_node)
                            graph.add_edge(player.current_node, new_node)
                    
                    choices = list(graph.get_children(player.current_node))
                except Exception as e:
                    print(f"\nError in choice generation: {e}")
                    # Instead of break, set flag for fallback ending
                    generation_failed_or_empty = True
            
            if choices and not generation_failed_or_empty: # Proceed only if choices exist and generation was ok
                print("\n🎲 AVAILABLE CHOICES 🎲")
                print(f"╔{'═'*68}╗")
                for i, choice in enumerate(choices, 1):
                    print(f"║ {i}. {wrap_text(choice.story, 64):<64} ║")
                    if hasattr(choice, 'consequences'):
                        consequences = choice.consequences
                        if consequences.get('health_change'):
                            health_change = consequences['health_change']
                            health_symbol = '❤️ +' if health_change > 0 else '💔 '
                            # print(f"║    {health_symbol}{health_change:<61} ║")
                        if consequences.get('item_changes'):
                            for item in consequences['item_changes']:
                                if item.startswith('add_'):
                                    continue
                                    # print(f"║    📦 Get: {item[4:]:<57} ║")
                                elif item.startswith('remove_'):
                                    continue
                                    # print(f"║    ❌ Lose: {item[7:]:<56} ║")
                    if getattr(choice, 'backtrack', False):
                        continue
                        # print(f"║    🔙 Can backtrack{' '*52} ║")
                    print(f"║{'-'*68}║")
                print(f"╚{'═'*68}╝")
        
                while True:
                    try:
                        choice = int(input(f"\nEnter your choice (1-{len(choices)}): "))
                        if 1 <= choice <= len(choices):
                            chosen_node = choices[choice - 1]
                            if hasattr(chosen_node, 'consequences'):
                                health_change = chosen_node.consequences.get('health_change', 0)
                                if health_change < 0:
                                    print(f"\nYou took {abs(health_change)} damage!")
                                player.health += health_change
                                if player.health <= 0:
                                    player.is_dead = True
                                    player.health = 0
                                    death_reason = chosen_node.story
                                    break

                                for item in chosen_node.consequences.get('item_changes', []):
                                    if item.startswith('add_'):
                                        player.inventory.append(item[4:])
                                        print(f"\nYou obtained: {item[4:]}")
                                    elif item.startswith('remove_'):
                                        if item[7:] in player.inventory:
                                            player.inventory.remove(item[7:])
                                            print(f"\nYou lost: {item[7:]}")
                            
                            player.move(graph, chosen_node)
                            story_state.current_scene = chosen_node.scene_state
                            story_state.characters = chosen_node.characters
                            story_state.visited_nodes.add(chosen_node.id)
                            break
                        else:
                            print(f"Please enter a number between 1 and {len(choices)}")
                    except ValueError:
                        print("Please enter a valid number.")
                
                save_game_state(graph, story_state)
            elif not player.current_node.is_end: # Handles the case where generation failed/empty AND it wasn't already an end node
                 print("\nYou've reached an unexpected end to this path!")
            
            # The main loop condition (while not player.is_dead and not player.current_node.is_end)
            # will now catch the forced end state from generation failure or depth limit
            time.sleep(1)
    
        # --- End of Main Loop ---

        clear_screen()
        print("\nGame Over!")
        print("=" * 50)
        if player.is_dead:
            print("\nYou have perished in your adventure!")
            print(f"Cause of death: {death_reason}")
            print(f"Final Health: {player.health}")
        elif player.current_node.is_end:
            ending_type = getattr(player.current_node, 'ending_type', 'neutral')
            ending_reason = getattr(player.current_node, 'ending_reason', 'Your journey has concluded.')
            
            # Ending type symbols
            ending_symbols = {
                'victory': '🏆 VICTORY',
                'defeat': '💔 DEFEAT',
                'neutral': '🔄 CONCLUSION',
                'bittersweet': '🌅 BITTERSWEET',
                'tragic': '⚰️ TRAGIC'
            }
            
            symbol = ending_symbols.get(ending_type, '🔄 CONCLUSION')
            
            print(f"\n{symbol} ENDING!")
            print_box(ending_reason)
            
            # Add specific message if it was a fallback ending due to generation failure
            if generation_failed_or_empty:
                print("(Note: The narrative thread frayed, concluding the adventure unexpectedly.)")
        
        print(f"\nFinal Status:")
        print(f"Health: {player.health}")
        print(f"Experience: {player.experience}")
        print(f"Final Inventory: {', '.join(player.inventory) if player.inventory else 'Empty'}")
            
    except Exception as e:
        print(f"\nError: {e}")
        print("Game initialization failed.")
        return

if __name__ == "__main__":
    if os.path.exists("game_save.json"):
        os.remove("game_save.json")
        
    main()