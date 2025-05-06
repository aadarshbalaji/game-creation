import time
import json
import os
import textwrap
from arc import return_story_tree

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



def print_scene_context(node_data, player_name):
    scene = node_data.get("scene_state", {})
    characters = node_data.get("characters", {})
    player = characters.get("player", {})

    location = scene.get("location") or "Crystal Caves"
    time_of_day = scene.get("time_of_day") or "Twilight"
    weather = scene.get("weather") or "Foggy"
    ambient = scene.get("ambient") or "Flickering lights"

    print("\n" + "=" * 30 + " CURRENT SCENE " + "=" * 30)
    print(f"🌍 Location: {location}")
    print(f"🕒 Time: {time_of_day}")
    print(f"🌤️ Weather: {weather}")
    print(f"🐾 Ambient: {ambient}")

    print("\n" + "=" * 28 + " CHARACTERS PRESENT " + "=" * 28)
    for char_name, char_data in characters.items():
        if char_name.lower() == "player":
            continue
        print(f"\n► {char_name.upper()}")
        print(f"Health: [{'♥' * (char_data.get('health', 100) // 10)}] {char_data.get('health', 100)}/100")
        mood = char_data.get("mood", "Unknown")
        print(f"Mood: {'❓' if mood == 'Unknown' else ''} {mood}")
        relationships = char_data.get("relationships", {})
        if relationships:
            print("Relationships:")
            for other, status in relationships.items():
                print(f"• {other}: {status}")

    print("\n" + "=" * 32 + " YOUR STATUS " + "=" * 32)
    print(f"{player_name}")
    health = player.get("health", 100)
    experience = player.get("experience", 10)
    inventory = player.get("inventory", [])
    print(f"Health: [{'♥' * (health // 10)}] {health}/100")
    print(f"Experience: [{'♦' * (experience // 5)}] {experience}")
    print(f"🎒 Inventory: {', '.join(inventory) if inventory else 'Empty'}")


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
            nodes[node_id] = {
                "story": node_data["story"],
                "is_end": node_data.get("is_end", False),
                "dialogue": node_data.get("dialogue", ""),
                "children": [],
                "child_actions": []  # Store action text separately from full scene descriptions
            }
        
        # Add child nodes and create action choices
        for edge in graph_data["edges"]:
            from_id = edge["from"]
            to_id = edge["to"]
            if from_id in nodes:
                nodes[from_id]["children"].append(to_id)
                
                # Generate a concise action choice
                action = generate_action_choice(nodes[to_id]["story"], theme)
                nodes[from_id]["child_actions"].append(action)
                
        return nodes, "node_0", depth
    except Exception as e:
        print(f"Error loading game: {e}")
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
    # ASCII art title
    title_text = """
    █▀▀ ▄▀█ █▀▄▀█ █▀▀   █▀▀ █▄░█ █▀▀ █ █▄░█ █▀▀
    █▄█ █▀█ █░▀░█ ██▄   ██▄ █░▀█ █▄█ █ █░▀█ ██▄
    """
    print(title_text)
    print("\nWelcome to the Interactive Story Generator with ACTION-ORIENTED CHOICES!\n")
    
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
    
    # Display the welcome message
    print(f"\nWelcome to your {theme} adventure, {player_name}!")
    print("Your journey is about to begin...\n")
    time.sleep(1)
    
    # Game loop
    while True:
        # Clear screen
        clear_screen()
        
        # Get current node
        current_node = nodes[current_node_id]
        print_scene_context(current_node, player_name)
        current_node = nodes[current_node_id]
        
        # Display the scene
        print(f"\n📜 YOUR SITUATION 📜")
        print_box(current_node["story"])
        
        if current_node["dialogue"]:
            print("\n💬 RESULT OF YOUR LAST ACTION 💬")
            print_box(current_node["dialogue"])
        
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
                    current_node_id = choices[choice_index][0]
                    valid_choice = True
                else:
                    print(f"Please enter a number between 1 and {len(choices)}.")
            except ValueError:
                print("Please enter a valid number.")
    
    # Game over screen
    print("\nGame Over!")
    print("=" * 50)
    print("\nThanks for playing!")

if __name__ == "__main__":
    main() 
