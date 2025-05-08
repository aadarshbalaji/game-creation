import time
import json
import os
import textwrap
from arc import return_story_tree, generate_scene_dialogue, generate_special_ability, generate_story_node

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



def print_scene_context(node_data, player_name, player_stats):
    scene = node_data.get("scene_state", {})
    characters = node_data.get("characters", {})

    # Get scene data with fallbacks only if the values are missing
    location = scene.get("location")
    if location == "unknown" or not location:
        location = "Crystal Caves"  # Only use fallback if missing or unknown
        
    time_of_day = scene.get("time_of_day")
    if time_of_day == "day" or not time_of_day:
        time_of_day = "Twilight"  # Only use fallback if missing or generic
        
    weather = scene.get("weather")
    if weather == "clear" or not weather:
        weather = "Foggy"  # Only use fallback if missing or generic
        
    ambient = scene.get("ambient")
    if ambient == "mysterious" or not ambient:
        ambient = "Flickering lights"  # Only use fallback if missing or generic

    print("\n" + "=" * 30 + " CURRENT SCENE " + "=" * 30)
    print(f"🌍 Location: {location}")
    print(f"🕒 Time: {time_of_day}")
    print(f"🌤️ Weather: {weather}")
    print(f"🐾 Ambient: {ambient}")

    # Display characters present in the scene (except player)
    other_characters = {name: data for name, data in characters.items() if name.lower() != "player"}
    
    if other_characters:
        print("\n" + "=" * 28 + " CHARACTERS PRESENT " + "=" * 28)
        
        # Group characters by type for better organization
        character_groups = {
            "ally": [],
            "enemy": [],
            "neutral": []
        }
        
        # Sort characters into groups
        for char_name, char_data in other_characters.items():
            char_type = char_data.get("type", "neutral")
            character_groups[char_type].append((char_name, char_data))
        
        # Define icons for character types
        type_icons = {
            "ally": "🤝",
            "enemy": "⚔️",
            "neutral": "❓"
        }
        
        # Display allies first, then neutrals, then enemies
        for char_type in ["ally", "neutral", "enemy"]:
            chars_of_type = character_groups[char_type]
            if chars_of_type:
                print(f"\n{type_icons[char_type]} {char_type.upper()} CHARACTERS:")
                
                for char_name, char_data in chars_of_type:
                    print(f"\n► {char_name.upper()}")
                    
                    # Show character description if available
                    if "description" in char_data:
                        print(f"  {char_data['description']}")
                    
                    # Show health with appropriate visualization
                    health = char_data.get("health", 100)
                    health_icon = "♥" if char_type != "enemy" else "❤️"
                    health_bar = health_icon * (health // 10) + "░" * ((100 - health) // 10)
                    print(f"  Health: [{health_bar}] {health}/100")
                    
                    # Show mood with appropriate emoji
                    mood = char_data.get("mood", "neutral")
                    mood_emoji = {
                        "hostile": "😠", "aggressive": "😠", "angry": "😠", "threatening": "😠",
                        "friendly": "😊", "happy": "😊", "helpful": "😊",
                        "sad": "😢", "upset": "😢",
                        "scared": "😨", "terrified": "😨", "frightened": "😨",
                        "suspicious": "🤨", "cautious": "🤨",
                        "neutral": "😐", "indifferent": "😐",
                        "calm": "😌", "peaceful": "😌",
                        "mysterious": "🧐", "cryptic": "🧐",
                        "wise": "🧙", "knowledgeable": "🧙",
                        "calculating": "🤔", "thoughtful": "🤔"
                    }.get(mood.lower(), "😐")
                    print(f"  Mood: {mood_emoji} {mood}")
                    
                    # Show relationship with player if available
                    relationship = char_data.get("relationships", {}).get("player", "neutral")
                    rel_emoji = {
                        "hostile": "⚔️", "friendly": "🤝", "neutral": "🤲",
                        "suspicious": "🔍", "trusting": "🛡️"
                    }.get(relationship.lower(), "🤲")
                    print(f"  Feels {rel_emoji} {relationship} toward you")
    else:
        print("\n" + "=" * 28 + " NO OTHER CHARACTERS PRESENT " + "=" * 28)

    # Use player_stats directly since that's the authoritative source
    print("\n" + "=" * 32 + " YOUR STATUS " + "=" * 32)
    print(f"{player_name}")
    health = player_stats["health"]
    experience = player_stats["experience"]
    inventory = player_stats["inventory"]
    abilities = player_stats.get("abilities", [])
    
    print(f"Health: [{'♥' * (health // 10)}] {health}/100")
    print(f"Experience: [{'♦' * (experience // 5)}] {experience}")
    print(f"🎒 Inventory: {', '.join(inventory) if inventory else 'Empty'}")
    
    # Display abilities if the player has any
    if abilities:
        print("\n" + "=" * 30 + " YOUR ABILITIES " + "=" * 30)
        for ability in abilities:
            ability_name = ability.get("name", "Unknown Ability")
            ability_desc = ability.get("description", "No description available")
            print(f"✨ {ability_name}: {ability_desc}")

def print_box(text, width=70, padding=1):
    """Print text in a decorative box"""
    horizontal = "+" + "-" * width + "+"
    empty = "|" + " " * width + "|"
    print(horizontal)
    for _ in range(padding):
        print(empty)
    for line in wrap_text(str(text), int(width)-2).split('\n'):
        print(f"| {str(line):<{int(width)-2}} |")
    for _ in range(padding):
        print(empty)
    print(horizontal)

def print_dialogue_box(dialogue_text, width=70):
    """
    Print dialogue between characters in a styled box with proper formatting.
    Each line of dialogue is displayed with proper attribution.
    """
    dialogue_lines = dialogue_text.strip().split("\n")
    
    # Create the box
    horizontal = "+" + "-" * width + "+"
    empty = "|" + " " * width + "|"
    
    print(horizontal)
    print(empty)
    
    # Process each line of dialogue
    for line in dialogue_lines:
        # Split into speaker and text
        if "[" in line and "]:" in line:
            speaker_end = line.find("]:")
            speaker = line[:speaker_end+1]  # Include the closing bracket
            text = line[speaker_end+2:].strip()  # Skip the ]: and any space
            
            # Different formatting for different speakers
            if speaker == "[You]":
                prefix = "❯❯ "  # Double arrow for player
            else:
                prefix = "➤ "  # Single arrow for NPCs
            
            formatted_line = f"{prefix}{speaker}: {text}"
            
            # Wrap the text to fit within the box
            wrapped_text = textwrap.wrap(formatted_line, width=width-4)  # Leave some padding
            
            # Print each wrapped line
            for i, text_line in enumerate(wrapped_text):
                print(f"|  {text_line:<{width-4}}  |")
            
        else:
            # Handle lines that don't follow the [Speaker]: Text format
            wrapped_text = textwrap.wrap(line, width=width-4)
            for text_line in wrapped_text:
                print(f"|  {text_line:<{width-4}}  |")
                
        # Add a small gap between dialogue lines
        print("|" + " " * width + "|")
    
    print(horizontal)

def enrich_node_with_dialogue(node, theme):
    """Add dialogue to a node if it doesn't already have it or if existing text isn't formatted dialogue."""
    # Check if existing dialogue is already properly formatted character/player dialogue
    is_existing_dialogue_formatted = False
    if "dialogue" in node and node["dialogue"] and isinstance(node["dialogue"], str):
        # Simple check: does it contain markers of our dialogue format?
        if "[You]:" in node["dialogue"] or "]:" in node["dialogue"] or "[Player's Thoughts]:" in node["dialogue"]:
            is_existing_dialogue_formatted = True

    if is_existing_dialogue_formatted:
        return # Already has good dialogue

    # If we are here, either no dialogue, or it's not well-formatted (e.g. just consequence text)
    # So, attempt to generate fresh dialogue.
    generated_dialogue = generate_scene_dialogue(node, theme)
    if generated_dialogue:
        node["dialogue"] = generated_dialogue
    # If generate_scene_dialogue returns empty (e.g. it couldn't determine good dialogue 
    # and player thoughts are off by its internal logic for some reason) and there was 
    # some old non-formatted text in node["dialogue"], that old text will remain.
    # This is generally acceptable, as it avoids overwriting potentially useful 
    # (though not well-formatted) consequence text if new dialogue isn't generated.

def print_ability_box(ability, width=70):
    """Print a special ability notification in a decorative box"""
    horizontal = "🔥" + "═" * width + "🔥"
    empty = "║" + " " * width + "║"
    
    print(horizontal)
    print(f"║{' SPECIAL ABILITY UNLOCKED ':=^{width}}║")
    print(empty)
    
    ability_name = ability.get("name", "Unknown Ability")
    ability_desc = ability.get("description", "No description available")
    
    print(f"║ ✨ {ability_name.upper():<{width-4}} ║")
    
    description_lines = wrap_text(ability_desc, width-4).split('\n')
    for line in description_lines:
        print(f"║  {line:<{width-4}}  ║")
    
    print(empty)
    print(horizontal)

def load_game(theme, depth=3, choices_per_node=2):
    """Generate and load a new story tree"""
    # Clean up old story files first
    for f in os.listdir():
        if f.endswith('_story.json'):
            try:
                os.remove(f)
                print(f"Removed old story file: {f}")
            except:
                pass
                
    # Generate a new story tree
    filename = return_story_tree(theme, depth, choices_per_node)
    
    # Load the saved game state
    try:
        with open(filename, 'r') as f:
            save_data = json.load(f)
            
        # Extract graph data
        graph_data = save_data.get("graph", {})
        
        # Build a simple tree for navigation
        nodes = {}
        for node_id, node_data in graph_data["nodes"].items():
            # Store dialogue and consequence separately
            dialogue = node_data.get("dialogue", "")
            consequence = ""
            
            # If this is not the first node, the original dialogue field might contain action consequences
            if node_id != "node_0" and isinstance(dialogue, dict):
                consequence = dialogue
                dialogue = ""
            elif node_id != "node_0" and not dialogue:
                # For older formats, use the original field as consequence text
                consequence = node_data.get("dialogue", "")
            
            nodes[node_id] = {
                "story": node_data["story"],
                "is_end": node_data.get("is_end", False),
                "dialogue": dialogue,  # Character dialogue
                "consequence_dialogue": consequence,  # Result of choices
                "scene_state": node_data.get("scene_state", {}),  # Include scene_state
                "characters": node_data.get("characters", {}),    # Include characters
                "outcome": node_data.get("outcome", {             # Include outcome data
                    "health_change": 0,
                    "experience_change": 0,
                    "inventory_changes": []
                }),
                "children": [],
                "child_actions": []  # Store action text separately from full scene descriptions
            }
        
        # Add child nodes and create action choices
        edge_count = 0
        for edge in graph_data["edges"]:
            from_id = edge["from"]
            to_id = edge["to"]
            if from_id in nodes:
                # Check if this child is already in the list (avoid duplicates)
                if to_id not in nodes[from_id]["children"]:
                    nodes[from_id]["children"].append(to_id)
                    edge_count += 1
                    
                    # Generate a concise action choice if needed
                    if len(nodes[from_id]["child_actions"]) < len(nodes[from_id]["children"]):
                        # Get action text from edge if available
                        if "action" in edge and edge["action"]:
                            action = edge["action"]
                        else:
                            # Generate action from target node's story
                            action = generate_action_choice(nodes[to_id]["story"], theme)
                        
                        nodes[from_id]["child_actions"].append(action)
        
        print(f"Loaded {len(nodes)} nodes with {edge_count} connections")
        
        # Validate that all nodes with children have matching child_actions
        for node_id, node_data in nodes.items():
            if len(node_data["children"]) != len(node_data["child_actions"]):
                print(f"Warning: Node {node_id} has {len(node_data['children'])} children but {len(node_data['child_actions'])} actions")
                # Fix by adding generic actions if needed
                while len(node_data["child_actions"]) < len(node_data["children"]):
                    child_id = node_data["children"][len(node_data["child_actions"])]
                    action = generate_action_choice(nodes[child_id]["story"], theme)
                    node_data["child_actions"].append(action)
                
        return nodes, "node_0", depth
    except Exception as e:
        print(f"Error loading game: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def generate_action_choice(scene_text, theme):
    """Generate a concise action-oriented choice (1-2 sentences) from scene description"""
    # List of action verbs by category
    exploration_verbs = ["Investigate", "Explore", "Search", "Examine", "Scout"]
    movement_verbs = ["Enter", "Climb", "Sneak", "Run", "Jump", "Navigate", "Descend"]
    interaction_verbs = ["Talk to", "Question", "Confront", "Persuade", "Negotiate with"]
    combat_verbs = ["Attack", "Ambush", "Fight", "Defend against", "Charge"]
    stealth_verbs = ["Hide from", "Avoid", "Evade", "Bypass", "Slip past"]
    tech_verbs = ["Hack", "Activate", "Disable", "Repair", "Override"]
    
    # Check scene content to determine appropriate action type
    scene_lower = scene_text.lower()
    
    # If scene text already starts with a verb and is short, it might be a good action already
    first_word = scene_text.split()[0].lower()
    action_verbs = ["search", "investigate", "approach", "examine", "open", "enter", "take", "grab", "talk", "speak", 
                   "fight", "attack", "run", "flee", "hide", "sneak", "climb", "jump", "use", "activate", "disable", 
                   "hack", "break", "repair", "explore"]
    
    if any(first_word == verb or first_word.startswith(verb) for verb in action_verbs) and len(scene_text.split()) < 20:
        # Already a concise action - use it as is or slightly shorten if needed
        sentences = scene_text.split('.')
        if len(sentences) > 2:
            return sentences[0].strip() + '.'
        return scene_text
        
    # Generate an appropriate action based on scene content
    if any(word in scene_lower for word in ["door", "entrance", "exit", "passage", "path", "corridor"]):
        verb = movement_verbs[hash(scene_text) % len(movement_verbs)]
        
        # Find what to enter
        for target in ["doorway", "passage", "corridor", "entrance", "tunnel", "opening"]:
            if target in scene_lower:
                return f"{verb} the {target} to see what lies beyond."
        
        return f"{verb} the area cautiously, ready for whatever awaits."
        
    elif any(word in scene_lower for word in ["person", "figure", "alien", "creature", "officer", "guard", "character"]):
        verb = interaction_verbs[hash(scene_text) % len(interaction_verbs)]
        
        # Find who to interact with
        for target in ["figure", "person", "officer", "alien", "guard", "creature", "individual"]:
            if target in scene_lower:
                return f"{verb} the {target} to learn more about the situation."
        
        return f"{verb} the mysterious figure to gain valuable information."
        
    elif any(word in scene_lower for word in ["terminal", "computer", "console", "device", "technology", "system"]):
        verb = tech_verbs[hash(scene_text) % len(tech_verbs)]
        
        # Find what tech to interact with
        for target in ["terminal", "console", "system", "device", "computer", "machine", "panel"]:
            if target in scene_lower:
                return f"{verb} the {target} to access its data or functions."
        
        return f"{verb} the technology to gain an advantage."
        
    elif any(word in scene_lower for word in ["enemy", "threat", "weapon", "danger", "attack", "fight"]):
        verb = combat_verbs[hash(scene_text) % len(combat_verbs)]
        
        # Find what to fight
        for target in ["enemy", "guard", "creature", "attacker", "threat", "opponent"]:
            if target in scene_lower:
                return f"{verb} the {target} using your available resources."
        
        return f"{verb} the immediate threat before it's too late."
        
    elif any(word in scene_lower for word in ["hide", "stealth", "quiet", "silent", "undetected", "sneak"]):
        verb = stealth_verbs[hash(scene_text) % len(stealth_verbs)]
        
        # Find what to avoid
        for target in ["guard", "patrol", "camera", "sensor", "security", "threat"]:
            if target in scene_lower:
                return f"{verb} the {target} without being detected."
        
        return f"{verb} any potential dangers as you proceed carefully."
    
    else:
        # Default to exploration
        verb = exploration_verbs[hash(scene_text) % len(exploration_verbs)]
        
        # Look for interesting objects to explore
        for target in ["area", "room", "building", "structure", "wreckage", "ruins", "debris"]:
            if target in scene_lower:
                return f"{verb} the {target} to discover what secrets it holds."
        
        # Connect to theme
        if "star wars" in theme.lower() or "space" in theme.lower():
            return f"{verb} the area for signs of Imperial activity or technology."
        elif "fantasy" in theme.lower() or "magic" in theme.lower():
            return f"{verb} the surroundings for magical artifacts or hidden passages."
        elif "cyberpunk" in theme.lower() or "tech" in theme.lower():
            return f"{verb} the location for valuable data or technological advantages."
        else:
            return f"{verb} the surroundings for clues or useful items."

def main():




    print("""
            \033[1;31m███╗   ██╗\033[0m\033[1;31m███████╗\033[0m\033[1;31m████████╗\033[0m\033[1;31m███████╗\033[0m\033[1;31m██╗     \033[0m\033[1;31m██╗\033[0m\033[1;31m██╗  ██╗\033[0m
            \033[1;31m████╗  ██║\033[0m\033[1;31m██╔════╝\033[0m\033[1;31m╚══██╔══╝\033[0m\033[1;31m██╔════╝\033[0m\033[1;31m██║     \033[0m\033[1;31m██║\033[0m\033[1;31m╚██╗██╔╝\033[0m
            \033[1;31m██╔██╗ ██║\033[0m\033[1;31m█████╗  \033[0m\033[1;31m   ██║   \033[0m\033[1;31m█████╗  \033[0m\033[1;31m██║     \033[0m\033[1;31m██║\033[0m\033[1;31m ╚███╔╝ \033[0m
            \033[1;31m██║╚██╗██║\033[0m\033[1;31m██╔══╝  \033[0m\033[1;31m   ██║   \033[0m\033[1;31m██╔══╝  \033[0m\033[1;31m██║     \033[0m\033[1;31m██║\033[0m\033[1;31m ██╔██╗ \033[0m
            \033[1;31m██║ ╚████║\033[0m\033[1;31m███████╗\033[0m\033[1;31m   ██║   \033[0m\033[1;31m██║     \033[0m\033[1;31m███████╗\033[0m\033[1;31m██║\033[0m\033[1;31m██╔╝ ██╗\033[0m
            \033[1;31m╚═╝  ╚═══╝\033[0m\033[1;31m╚══════╝\033[0m\033[1;31m   ╚═╝   \033[0m\033[1;31m╚═╝     \033[0m\033[1;31m╚══════╝\033[0m\033[1;31m╚═╝\033[0m\033[1;31m╚═╝  ╚═╝\033[0m
                                                                
     ██████╗██╗   ██╗ ██████╗  █████╗     ██████╗  █████╗ ███╗   ███╗███████╗
    ██╔════╝╚██╗ ██╔╝██╔═══██╗██╔══██╗    ██╔════╝ ██╔══██╗████╗ ████║██╔════╝
    ██║      ╚████╔╝ ██║   ██║███████║    ██║  ███╗███████║██╔████╔██║█████╗  
    ██║       ╚██╔╝  ██║   ██║██╔══██║    ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝  
    ╚██████╗   ██║   ╚██████╔╝██║  ██║    ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗
     ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝     ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝
    \033[0m""")

    

    print("\nWelcome to the Netflix's CYOA Interactive Story Game!\n")
    
    # Ask what kind of story the player wants
    theme = input("\nWhat kind of story would you like to experience?\n(e.g., Star Wars, Lord of the Rings, Dracula): ")
    
    # Ask for story depth
    depth = 3
    while True:
        try:
            depth_input = input("\nHow deep should the story be?: ")
            depth = int(depth_input)
            if 2 <= depth <= 12:
                break
            print("Please enter a number between 2 and 12.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Ask for choices per node
    choices_per_node = 2
    while True:
        try:
            choices_input = input("\nHow many choices per decision point? (2-4): ")
            choices_per_node = int(choices_input)
            if 2 <= choices_per_node <= 4:
                break
            print("Please enter a number between 2 and 4.")
        except ValueError:
            print("Please enter a valid number.")
    
    print(f"\nGenerating a {theme} story with depth {depth} and {choices_per_node} choices per node...")
    print("This may take a minute or two. Please wait...\n")
    
    # Load or generate the story
    nodes, current_node_id, max_depth = load_game(theme, depth, choices_per_node)
    
    if not nodes or not current_node_id:
        print("Failed to load or generate game!")
        return
    
    print(f"\nStory loaded! Max depth: {max_depth}")
    
    # Ask for player name
    player_name = input("\nWhat is your name, adventurer? ")
    
    # Initialize player stats
    player_stats = {
        "health": 100,
        "experience": 10,
        "inventory": [],
        "abilities": []  # New field for special abilities
    }
    
    # Add a starting ability based on theme
    starting_ability = generate_special_ability(theme, 10)
    if starting_ability:
        player_stats["abilities"].append(starting_ability)
    
    # Display the welcome message
    print(f"\nWelcome to your {theme} adventure, {player_name}!")
    print("Your journey is about to begin...\n")
    
    # Show starting ability if one was generated
    if starting_ability:
        print("\nAs you begin your journey, you realize you have a special ability:")
        print_ability_box(starting_ability)
        input("\nPress Enter to continue...")
    
    time.sleep(1.5)
    
    # Track experience milestones for ability unlocks
    ability_milestones = [30, 60, 100, 150]
    next_ability_milestone = ability_milestones[0]
    
    # Keep track of player's choice path
    choice_path = ["0"]
    
    # Game loop
    while True:
        # Clear screen
        clear_screen()
        
        # Display the choice path at the top
        path_display = " → ".join(choice_path)
        print(f"\n🧭 PATH: {path_display}")
        print("=" * 70)
        
        # Get current node
        current_node = nodes[current_node_id]
        
        
        # Update character data with latest player stats
        if "characters" in current_node and "player" in current_node["characters"]:
            current_node["characters"]["player"]["health"] = player_stats["health"]
            current_node["characters"]["player"]["experience"] = player_stats["experience"]
            current_node["characters"]["player"]["inventory"] = player_stats["inventory"]
        else:
            # Ensure character data exists
            if "characters" not in current_node:
                current_node["characters"] = {}
            current_node["characters"]["player"] = {
                "health": player_stats["health"],
                "experience": player_stats["experience"],
                "mood": "determined",
                "status_effects": [],
                "inventory": player_stats["inventory"]
            }
            
        # Generate dialogue for this node if needed
        enrich_node_with_dialogue(current_node, theme)
        
        # Display scene context and player status
        print_scene_context(current_node, player_name, player_stats)
        
        # Display the scene
        print(f"\n📜 YOUR SITUATION 📜")
        print_box(current_node["story"])
        
        # Display character dialogue in a visually distinct way
        if "dialogue" in current_node and current_node["dialogue"]:
            print_dialogue_box(current_node["dialogue"])
            
        # Display result of the previous choice if available
        if "consequence_dialogue" in current_node and current_node["consequence_dialogue"]:
            print("\n💬 RESULT OF YOUR LAST ACTION 💬")
            if isinstance(current_node["consequence_dialogue"], dict):
                consequence_text = "You see the results of your actions unfold."
                for key, value in current_node["consequence_dialogue"].items():
                    if isinstance(value, str) and value:
                        consequence_text = value
                        break
                print_box(consequence_text)
            else:
                print_box(current_node["consequence_dialogue"])
        
        # Check if we've reached an ending
        is_last_pregenerated = current_node["is_end"] or not current_node["children"]
        at_max_depth = len(choice_path) == max_depth
        dynamic_ending_node = None
        dynamic_ending_choices = None
        dynamic_ending_id = None
        dynamic_conclusion_node = None
        dynamic_conclusion_id = None
        dynamic_ending_context = None

        if is_last_pregenerated and at_max_depth:
            # Dynamically generate the 'ending-pointed' node
            # Gather context: path, choices, results
            story_so_far = []
            node_id = "node_0"
            for idx in range(1, len(choice_path)):
                node_id = node_id + f"_{choice_path[idx]}"
                node = nodes.get(node_id)
                if node:
                    story_so_far.append(f"Step {idx}: {node['story']}")
                    if node.get('consequence_dialogue'):
                        story_so_far.append(f"Result: {node['consequence_dialogue']}")
            context_text = "\n".join(story_so_far)
            # Use the same number of choices as the user selected at the start
            num_choices = choices_per_node
            prompt = f"""
            The player has reached the climax of their interactive story. Here is the journey so far:
            {context_text}
            
            Now, generate a climactic scene that feels like the penultimate moment before the story's true ending. The scene should be highly specific to the events and choices so far. Offer exactly {num_choices} action-oriented choices, each clearly leading to a final outcome. Make it rich but concise: 5 sentences maximum. Format as a JSON object:
            {{
                "story": "Rich, dramatic text for the climactic scene",
                "choices": [
                    {{"text": "Action the player takes (verb first)", "consequences": "Immediate result"}},
                    ...
                ]
            }}
            """
            dynamic_ending_node = generate_story_node(prompt)
            if not dynamic_ending_node:
                # Fallback if Gemini fails
                fallback_choices = [
                    {"text": "Face your destiny head-on.", "consequences": "You brace yourself for the outcome."},
                    {"text": "Try to escape fate.", "consequences": "You look for a way out, but the end draws near."},
                    {"text": "Seek help from an unexpected ally.", "consequences": "You call out, hoping someone will answer."},
                    {"text": "Reflect on your journey and prepare for the end.", "consequences": "You gather your thoughts for what comes next."}
                ]
                dynamic_ending_node = {
                    "story": "You stand at the threshold of your final challenge.",
                    "choices": fallback_choices[:num_choices]
                }
            dynamic_ending_choices = dynamic_ending_node.get("choices", [])
            dynamic_ending_id = "dynamic_ending_node"
            dynamic_ending_context = context_text

            # Present the dynamic ending node
            print(f"\n📜 FINAL CHALLENGE 📜")
            print_box(dynamic_ending_node["story"])
            # Show choices
            max_box_width = 70
            choice_prefixes = [f"{i+1}. " for i in range(len(dynamic_ending_choices))]
            wrapped_choices = []
            for i, choice in enumerate(dynamic_ending_choices):
                prefix = choice_prefixes[i]
                wrapped = textwrap.wrap(choice["text"], width=max_box_width - len(prefix) - 3)
                if not wrapped:
                    wrapped = [""]
                lines = []
                for idx, line in enumerate(wrapped):
                    if idx == 0:
                        lines.append(prefix + line)
                    else:
                        lines.append(" " * len(prefix) + line)
                wrapped_choices.append(lines)
            print(f"╔{'═'*max_box_width}╗")
            for i, lines in enumerate(wrapped_choices):
                for line in lines:
                    print(f"║ {line:<{max_box_width-1}}║")
                if i < len(wrapped_choices) - 1:
                    print(f"║{'-'*max_box_width}║")
            print(f"╚{'═'*max_box_width}╝")

            # Get player choice for the dynamic ending node
            valid_choice = False
            while not valid_choice:
                try:
                    choice_input = input("\nEnter your choice (number): ").strip()
                    choice_index = int(choice_input) - 1
                    if 0 <= choice_index < len(dynamic_ending_choices):
                        chosen_ending_choice = dynamic_ending_choices[choice_index]
                        valid_choice = True
                    else:
                        print(f"Please enter a number between 1 and {len(dynamic_ending_choices)}.")
                except ValueError:
                    print("Please enter a valid number.")

            # Now, generate the final conclusion node
            final_context = context_text + f"\nFinal Choice: {chosen_ending_choice['text']}\nResult: {chosen_ending_choice.get('consequences','')}"
            conclusion_prompt = f"""
            The player has completed their interactive story. Here is the full journey:
            {final_context}
            
            Write a powerful, natural conclusion to the story. The ending should reflect the player's choices and actions, and can be positive, negative, or mixed. Make the ending concise: keep it to 2-4 sentences maximum. Format as a JSON object:
            {{
                "ending": "A rich but brief, satisfying conclusion to the story (2-4 sentences)."
            }}
            """
            dynamic_conclusion_node = generate_story_node(conclusion_prompt)
            if not dynamic_conclusion_node or "ending" not in dynamic_conclusion_node:
                dynamic_conclusion_node = {"ending": "Your journey comes to an end. The consequences of your actions echo into the future."}
            print(f"\n🏁 STORY CONCLUSION 🏁")
            print_box(dynamic_conclusion_node["ending"])
            break

        # (rest of the original loop follows as before)
        if is_last_pregenerated and not at_max_depth:
            print("\nYou've reached the end of your journey!")
            break
        
        # Get child nodes with their action choices (not full scene descriptions)
        choices = []
        for i, child_id in enumerate(current_node["children"]):
            if i < len(current_node["child_actions"]):
                action_text = current_node["child_actions"][i]
                choices.append((child_id, action_text))
            else:
                # Fallback if we somehow don't have an action choice
                choices.append((child_id, "Investigate further to see what happens."))
        
        # Display choices
        print("\n🎲 WHAT WILL YOU DO? 🎲")

        max_box_width = 70  # Set the maximum width for the box
        choice_prefixes = [f"{i+1}. " for i in range(len(choices))]
        wrapped_choices = []
        for i, (_, choice_text) in enumerate(choices):
            prefix = choice_prefixes[i]
            # The first line gets the prefix, subsequent lines are indented
            wrapped = textwrap.wrap(choice_text, width=max_box_width - len(prefix) - 3)  # 3 for space and borders
            if not wrapped:
                wrapped = [""]
            lines = []
            for idx, line in enumerate(wrapped):
                if idx == 0:
                    lines.append(prefix + line)
                else:
                    lines.append(" " * len(prefix) + line)
            wrapped_choices.append(lines)
        # Draw the top border
        print(f"╔{'═'*max_box_width}╗")
        for i, lines in enumerate(wrapped_choices):
            for line in lines:
                print(f"║ {line:<{max_box_width-1}}║")
            # Add a separator between choices, except after the last one
            if i < len(wrapped_choices) - 1:
                print(f"║{'-'*max_box_width}║")
        # Draw the bottom border
        print(f"╚{'═'*max_box_width}╝")
        
        # Get player choice
        valid_choice = False
        while not valid_choice:
            try:
                choice_input = input("\nEnter your choice (number): ").strip()
                choice_index = int(choice_input) - 1
                
                if 0 <= choice_index < len(choices):
                    # Store the current node ID before changing
                    previous_node_id = current_node_id
                    
                    # Update current node to the chosen one
                    current_node_id = choices[choice_index][0]
                    
                    # Update choice path
                    choice_path.append(str(choice_index + 1))
                    
                    # Get the current node and mark it as visited
                    current_node = nodes[current_node_id]
                    current_node["visited"] = True
                    
                    # Save the current state to JSON
                    save_data = {
                        "story_state": {
                            "characters": {
                                "player": {
                                    "health": player_stats["health"],
                                    "experience": player_stats["experience"],
                                    "mood": "determined",
                                    "status_effects": [],
                                    "inventory": player_stats["inventory"]
                                }
                            },
                            "current_scene": current_node,
                            "inventory": player_stats["inventory"],
                            "visited_nodes": choice_path,
                            "theme": theme,
                            "max_depth": max_depth
                        },
                        "graph": nodes
                    }
                    
                    # Save to a file
                    filename = f"{theme.lower().replace(' ', '_')}_story.json"
                    with open(filename, 'w') as f:
                        json.dump(save_data, f, indent=2)
                    
                    chosen_node = nodes[current_node_id]
                    
                    # Move any dialogue to consequence_dialogue if it's not a character dialogue
                    if "dialogue" in chosen_node and chosen_node["dialogue"] and not chosen_node["dialogue"].startswith("[You]"):
                        chosen_node["consequence_dialogue"] = chosen_node["dialogue"]
                        chosen_node["dialogue"] = ""
                    
                    # Apply outcome effects from the chosen node immediately
                    if "outcome" in chosen_node:
                        outcome = chosen_node["outcome"]
                        
                        # Apply health changes
                        health_change = outcome.get("health_change", 0)
                        
                        if health_change != 0:
                            old_health = player_stats["health"]
                            
                            # Apply health change (ensuring it's noticeable)
                            if health_change < 0:
                                player_stats["health"] = max(1, player_stats["health"] - max(5, abs(health_change)))
                            else:
                                player_stats["health"] = min(100, player_stats["health"] + max(5, health_change))
                                
                            new_health = player_stats["health"]
                            
                            if health_change > 0:
                                print(f"\n💓 HEALTH UPDATE 💓")
                                print_box(f"You gained {new_health - old_health} health points.")
                            else:
                                print(f"\n💓 HEALTH UPDATE 💓")
                                print_box(f"You lost {old_health - new_health} health points.")
                        
                        # Apply experience changes
                        exp_change = outcome.get("experience_change", 0)
                        if exp_change > 0:
                            old_exp = player_stats["experience"]
                            player_stats["experience"] += exp_change
                            new_exp = player_stats["experience"]
                            
                            print(f"\n✨ EXPERIENCE GAINED ✨")
                            print_box(f"You gained {exp_change} experience points.")
                            
                            # Check if player reached an ability milestone
                            current_abilities = [a["name"] for a in player_stats["abilities"]]
                            
                            # If we crossed a milestone, grant a new ability
                            if old_exp < next_ability_milestone and new_exp >= next_ability_milestone:
                                # Generate a new special ability
                                new_ability = generate_special_ability(theme, new_exp, current_abilities)
                                
                                if new_ability:
                                    # Add the ability
                                    player_stats["abilities"].append(new_ability)
                                    
                                    # Notify the player
                                    print("\n✨✨✨ NEW ABILITY UNLOCKED ✨✨✨")
                                    print_ability_box(new_ability)
                                    input("\nPress Enter to continue...")
                                
                                # Update to next milestone
                                for milestone in ability_milestones:
                                    if new_exp < milestone:
                                        next_ability_milestone = milestone
                                        break
                                else:
                                    # If we've passed all milestones, set a high value
                                    next_ability_milestone = 1000
                        
                        # Apply inventory changes
                        inventory_changes = outcome.get("inventory_changes", [])
                        items_added = []
                        for change in inventory_changes:
                            if "add" in change:
                                items_added.append(change["add"])
                                if change["add"] not in player_stats["inventory"]:
                                    player_stats["inventory"].append(change["add"])
                            elif "remove" in change and change["remove"] in player_stats["inventory"]:
                                player_stats["inventory"].remove(change["remove"])
                        
                        if items_added:
                            print(f"\n🎒 ITEMS ACQUIRED 🎒")
                            print_box(f"You found: {', '.join(items_added)}")
                        
                        # A brief pause to let the player read the updates
                        time.sleep(2.2)
                    
                    valid_choice = True
                else:
                    print(f"Please enter a number between 1 and {len(choices)}.")
            except ValueError:
                print("Please enter a valid number.")
    
    # Game over screen
    print("\nGame Over!")
    print("=" * 50)
    print(f"\nFinal Stats for {player_name}:")
    print(f"Health: {player_stats['health']}/100")
    print(f"Experience: {player_stats['experience']}")
    
    # Show acquired abilities
    if player_stats["abilities"]:
        print("\nAbilities Acquired:")
        for ability in player_stats["abilities"]:
            print(f"✨ {ability['name']}: {ability['description']}")
    
    # Show collected items
    if player_stats["inventory"]:
        print(f"\nItems Collected: {', '.join(player_stats['inventory'])}")
    else:
        print("\nItems Collected: None")
    
    # Show path taken
    print(f"\nYour journey path: {' → '.join(choice_path)}")
    
    print("\nThanks for playing!")

if __name__ == "__main__":
    main() 
