import time
import json
import os
import re
import textwrap
# Use functions from test_arc for loading/generating predetermined story
from test_arc import load_or_generate_predetermined_story, StoryState as PredeterminedStoryState, ARC_DIR, PREDETERMINED_STORIES_DIR, calculate_story_stage 
# Use generate_story_node from storygen for dynamic generation
from storygen import generate_story_node, StoryState as DynamicStoryState
from Graph_Classes.Structure import Node, Graph
from Graph_Classes.Interact import Player

PLAYER_SAVE_DIR = "player_saves"
os.makedirs(PLAYER_SAVE_DIR, exist_ok=True)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

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
        for char_name, char_data in data.items():
            if char_name == "player":
                continue  
            
            if char_name == "other_characters":
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
                            for target, relation in npc_data['relationships'].items():
                                print(f"   • {target}: {relation}")
            else:
                print(f"\n► {char_name.upper()}")
    
    elif title == "CURRENT SCENE":
        print(f"\n🌍 Location: {data.get('location', 'Unknown')}")
        print(f"🕒 Time: {data.get('time_of_day', 'Unknown')}")
        print(f"🌤️  Weather: {data.get('weather', 'Unknown')}")
        print(f"💫 Ambient: {data.get('ambient', 'Unknown')}")
    
    print("\n" + "=" * (42 + len(title)))

# --- Player Progress Saving/Loading ---

def get_save_filename(player_name, theme):
    safe_player_name = "".join(c for c in player_name if c.isalnum() or c in (' ', '_')).rstrip()
    safe_theme_name = "".join(c for c in theme if c.isalnum() or c in (' ', '_')).rstrip()
    return os.path.join(PLAYER_SAVE_DIR, f"player_{safe_player_name}_theme_{safe_theme_name}.json")

def save_player_progress(player, graph, story_state, filepath):
    """Saves the player's current state and any dynamically added nodes/edges."""
    dynamic_nodes = {}
    dynamic_edges = []

    # Identify nodes/edges not present in the original story state (if available)
    # For now, we assume any node/edge added after initial load is dynamic
    # A more robust approach might compare against the original predetermined graph
    # but that requires loading it again or passing it through.
    # Simple approach: save all nodes/edges for simplicity during gameplay saving.
    
    for node_id, node in graph.nodes_by_id.items():
         dynamic_nodes[node_id] = {
            "story": node.story,
            "dialogue": getattr(node, 'dialogue', ""),
            "scene_state": getattr(node, 'scene_state', {}),
            "characters": getattr(node, 'characters', {}),
            "is_end": node.is_end,
            "story_path": getattr(node, 'story_path', None), # Include story path if exists
            "consequences": getattr(node, 'consequences', None), # Include consequences if exists
            "backtrack": getattr(node, 'backtrack', False) # Include backtrack flag
        }
         for child in graph.adjacency_list.get(node, []):
             dynamic_edges.append({
                 "from": node.id,
                 "to": child.id,
                 "backtrack": getattr(child, 'backtrack', False) # Redundant? saved on node itself
             })

    save_data = {
        "player_state": {
            "name": player.name,
            "current_node_id": player.current_node.id,
            "health": player.health,
            "experience": player.experience,
            "inventory": player.inventory,
            "traversed_node_ids": [node.id for node in player.traversed_nodes]
        },
        "story_state": story_state.to_dict(), # Save dynamic story state
        "dynamic_graph": {
            "nodes": dynamic_nodes,
            "edges": dynamic_edges
        }
    }
    
    try:
        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent=2)
        print(f"\nPlayer progress saved to {filepath}")
    except Exception as e:
        print(f"\nError saving player progress: {e}")

def load_player_progress(filepath, base_graph, base_story_state):
    """Loads player progress, potentially merging dynamic nodes into the base graph."""
    if not os.path.exists(filepath):
        return None, None # No save file found
        
    try:
        with open(filepath, 'r') as f:
            save_data = json.load(f)
            
        print(f"\nLoading player progress from {filepath}...")
        
        player_state_data = save_data["player_state"]
        dynamic_graph_data = save_data["dynamic_graph"]
        loaded_story_state = DynamicStoryState.from_dict(save_data["story_state"])

        # Integrate dynamic nodes/edges into the base graph
        # This assumes base_graph is mutable and we add to it
        nodes_map = {node.id: node for node in base_graph.nodes_by_id.values()} # Map existing nodes

        for node_id, node_data in dynamic_graph_data["nodes"].items():
            if node_id not in nodes_map:
                 # Add new dynamic node
                 node = Node(node_data["story"], node_data["is_end"], node_data.get('dialogue', ''))
                 node.id = node_id # Ensure consistent ID
                 node.scene_state = node_data.get('scene_state', {})
                 node.characters = node_data.get('characters', {})
                 node.story_path = node_data.get('story_path')
                 node.consequences = node_data.get('consequences')
                 node.backtrack = node_data.get('backtrack', False)
                 base_graph.add_node(node) # Add directly to graph
                 nodes_map[node_id] = node # Add to map for edge creation
            # else: Node already exists from base graph, potentially update? For now, assume base is static.

        for edge_data in dynamic_graph_data["edges"]:
            from_node = nodes_map.get(edge_data["from"])
            to_node = nodes_map.get(edge_data["to"])
            if from_node and to_node:
                # Avoid adding duplicate edges
                if to_node not in base_graph.adjacency_list.get(from_node, []):
                    base_graph.add_edge(from_node, to_node)
                    # Backtrack flag is on the node itself, no need to set here
            
        # Restore Player object
        current_node = nodes_map.get(player_state_data["current_node_id"])
        if not current_node:
            print("Error: Could not find player's current node in loaded graph. Starting from beginning.")
            current_node = next(iter(base_graph.adjacency_list)) # Fallback
            
        player = Player(player_state_data["name"], current_node)
        player.health = player_state_data["health"]
        player.experience = player_state_data["experience"]
        player.inventory = player_state_data["inventory"]
        player.traversed_nodes = [nodes_map[nid] for nid in player_state_data["traversed_node_ids"] if nid in nodes_map]

        # Use the loaded dynamic story state for continuation
        current_story_state = loaded_story_state
            
        return player, current_story_state

    except Exception as e:
        print(f"\nError loading player progress: {e}. Starting new game.")
        # Fallback to starting a new game using the base state
        start_node = next(iter(base_graph.adjacency_list)) 
        player = Player(base_story_state.theme, start_node) # Need player name later
        return player, base_story_state 

# --- Main Game Logic ---

def main():
    clear_screen()
    print("Welcome to Netflix's AI-Generated CYOA!")
    print("=" * 50)
    
    player_name = input("\nEnter your name: ")
    story_theme = input("\nWhat kind of story would you like to experience?\n(e.g., Star Wars, Lord of the Rings, Dracula, your own movie idea): ")
    story_depth = 8 # Or make this configurable
    save_filepath = get_save_filename(player_name, story_theme)
    death_reason = None
    
    try:
        # 1. Load or Generate Predetermined Story Graph & Arc Data
        print(f"\nSetting up {story_theme} world...")
        base_graph, base_story_state, arc_data = load_or_generate_predetermined_story(theme=story_theme, depth=story_depth)
        if not base_graph or not base_story_state:
             raise Exception("Failed to load or generate the base story.")
        if not arc_data:
            print("Warning: Story arc data is missing. Dynamic generation might lack guidance.")
            # Try loading arc file directly if load_or_generate didn't return it
            arc_filename = os.path.join(ARC_DIR, f"{story_theme.lower().replace(' ', '_')}_arc.json")
            if os.path.exists(arc_filename):
                 with open(arc_filename, 'r') as f:
                     try:
                         arc_data = json.load(f)
                         print(f"Successfully loaded arc data from {arc_filename}")
                     except json.JSONDecodeError:
                         print(f"Error decoding arc data from {arc_filename}")
            else:
                 print(f"Arc data file not found at {arc_filename}")

        # 2. Load Player Progress (if exists)
        player, current_story_state = load_player_progress(save_filepath, base_graph, base_story_state)

        # 3. Initialize Player if no save loaded
        if not player:
            print("\nStarting a new adventure!")
            start_node = next(iter(base_graph.adjacency_list))
            player = Player(player_name, start_node)
             # Use base story state for new game
            current_story_state = DynamicStoryState() # Create a dynamic state
            current_story_state.theme = base_story_state.theme
            current_story_state.characters = start_node.characters
            current_story_state.current_scene = start_node.scene_state
            current_story_state.inventory = [] # Player starts with empty inventory
            current_story_state.visited_nodes.add(start_node.id)
        else:
            print(f"\nWelcome back, {player.name}!")
            # Ensure player name is correct from save
            player.name = player_name 

        # --- Game Loop ---
        while not player.is_dead and not player.current_node.is_end:
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
            
            choices = list(base_graph.get_children(player.current_node))
            if not choices and not player.current_node.is_end:
                print("\nReached the end of a known path... venturing into the unknown!")
                print("Generating new story paths based on the arc...")
                try:
                    # Prepare context for dynamic generation
                    story_context = {
                        "previous_scene": player.current_node.story,
                        "current_location": player.current_node.scene_state.get('location', 'Unknown'),
                        "time_of_day": player.current_node.scene_state.get('time_of_day', 'Unknown'),
                        "weather": player.current_node.scene_state.get('weather', 'Unknown'),
                        "player_status": {
                            "health": player.health,
                            "inventory": player.inventory
                        },
                        "characters": player.current_node.characters,
                        "recent_events": [node.story for node in player.traversed_nodes[-3:]]
                    }
                    
                    # Determine current stage info (needs improvement)
                    # Simple approach: Use story_path if available, otherwise estimate
                    current_path = getattr(player.current_node, 'story_path', None)
                    stage_index = 0 # Default
                    progression = "Middle" # Default
                    if current_path and arc_data:
                        # Try to parse stage from path like "Stage Name - Progression"
                        parts = current_path.split(' - ')
                        if len(parts) > 0:
                            stage_name = parts[0]
                            if len(parts) > 1: progression = parts[1]
                            # Find matching stage index in arc_data
                            for i, stage in enumerate(arc_data.get('arc', [])):
                                if stage.get('stage') == stage_name:
                                    stage_index = i
                                    break
                        else: # Fallback: Estimate based on traversed nodes? Too complex for now.
                            pass 
                    elif arc_data: # Estimate if no path info but have arc
                         # Very rough estimate based on traversed nodes vs expected depth? 
                         # Or use calculate_story_stage if we track depth?
                         # For now, let's default to a middle stage if unsure.
                         estimated_level = len(player.traversed_nodes) # Very rough approximation
                         stage_index = calculate_story_stage(estimated_level, story_depth * 1.5) # Guess max depth
                         if stage_index == 0: progression = "Beginning"
                         elif stage_index >= len(arc_data.get('arc', [])) -1 : progression = "Late"
                         else: progression = "Middle"
                         
                    current_stage_info = {"stage_index": stage_index, "progression": progression}
                    print(f"Attempting to generate based on Arc Stage: {stage_index} ({progression})")

                    # Call the updated storygen function with arc context
                    choice_data = generate_story_node(
                        story_context, 
                        current_story_state, # Pass the dynamic state 
                        arc_data=arc_data, 
                        current_stage_info=current_stage_info
                    )
                    
                    # Add dynamically generated choices to the graph
                    for choice in choice_data["choices"]:
                        new_node = Node(choice["text"], choice_data.get("is_ending", False), choice.get("dialogue", ""))
                        # Inherit or update scene/characters from choice_data
                        new_node.scene_state = choice_data.get("scene_state", player.current_node.scene_state) 
                        new_node.characters = choice_data.get("characters", player.current_node.characters)
                        new_node.consequences = choice.get("consequences", {})
                        new_node.backtrack = choice.get("can_backtrack", False)
                        # Try to assign a meaningful story_path based on generation context
                        new_node.story_path = choice_data.get("story_path", f"Dynamic - Stage {stage_index}") 
                        base_graph.add_node(new_node)
                        base_graph.add_edge(player.current_node, new_node)
                    
                    choices = list(base_graph.get_children(player.current_node))
                except Exception as e:
                    print(f"\nError in choice generation: {e}")
                    break
            
            if choices:
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
                            
                            player.move(base_graph, chosen_node) # Move player using the main graph
                            # Update dynamic story state
                            current_story_state.current_scene = chosen_node.scene_state
                            current_story_state.characters = chosen_node.characters
                            current_story_state.visited_nodes.add(chosen_node.id)
                            break
                        else:
                            print(f"Please enter a number between 1 and {len(choices)}")
                    except ValueError:
                        print("Please enter a valid number.")
                
                # Save player progress after each choice
                save_player_progress(player, base_graph, current_story_state, save_filepath)
            else:
                print("\nYou've reached the end of this path!")
                break
            
            time.sleep(1.5)
    
        clear_screen()
        print("\nGame Over!")
        print("=" * 50)
        if player.is_dead:
            print("\nYou have perished in your adventure!")
            print(f"Cause of death: {death_reason}")
            print(f"Final Health: {player.health}")
        elif player.current_node.is_end:
            print("\nCongratulations! You've reached an ending!")
        
        print(f"\nFinal Status:")
        print(f"Health: {player.health}")
        print(f"Experience: {player.experience}")
        print(f"Final Inventory: {', '.join(player.inventory) if player.inventory else 'Empty'}")
            
    except Exception as e:
        print(f"\nError: {e}")
        print("Game initialization failed. FUCKCCKCKCKCKCKCK444444")
        return

if __name__ == "__main__":
    main()