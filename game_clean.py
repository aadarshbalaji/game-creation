import time
import json
import os
import textwrap
from arc import return_story_tree, generate_scene_dialogue, generate_special_ability

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
    """Add dialogue to a node if it doesn't already have it"""
    # Skip if the node already has dialogue
    if "dialogue" in node and node["dialogue"]:
        return
    
    # Generate dialogue based on node content and theme
    dialogue = generate_scene_dialogue(node, theme)
    if dialogue:
        node["dialogue"] = dialogue

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
    theme = input("\nWhat kind of story would you like to experience?\n(e.g., Star Wars, Lord of the Rings, Cyberpunk): ")
    
    # Ask for story depth
    depth = 3
    while True:
        try:
            depth_input = input("\nHow deep should the story be? (2-5): ")
            depth = int(depth_input)
            if 2 <= depth <= 5:
                break
            print("Please enter a number between 2 and 5.")
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
        if current_node["is_end"] or not current_node["children"]:
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
        print(f"╔{'═'*68}╗")
        
        for i, (_, choice_text) in enumerate(choices):
            # Wrap the choice text to fit within the box
            wrapped_lines = textwrap.wrap(choice_text, width=66)
            
            # Print the first line with the choice number
            first_line = wrapped_lines[0] if wrapped_lines else ""
            print(f"║ {i+1}. {first_line:<65} ║")
            
            # Print any additional lines (max one more line to keep it concise)
            if len(wrapped_lines) > 1:
                print(f"║    {wrapped_lines[1]:<65} ║")
            
            # Add a separator between choices
            if i < len(choices) - 1:
                print(f"║{'-'*68}║")
            else:
                print(f"╚{'═'*68}╝")
        
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
                        time.sleep(3)
                    
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
