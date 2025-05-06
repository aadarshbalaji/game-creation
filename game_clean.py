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
    
    # Initialize player stats
    player_stats = {
        "health": 100,
        "experience": 10,
        "inventory": []
    }
    
    # Display the welcome message
    print(f"\nWelcome to your {theme} adventure, {player_name}!")
    print("Your journey is about to begin...\n")
    time.sleep(1.5)
    
    # Game loop
    while True:
        # Clear screen
        clear_screen()
        
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
        
        # Display scene context and player status
        print_scene_context(current_node, player_name, player_stats)
        
        # Display the scene
        print(f"\n📜 YOUR SITUATION 📜")
        print_box(current_node["story"])
        
        # Display result of the previous choice if there's dialogue
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
                    # Store the current node ID before changing
                    previous_node_id = current_node_id
                    
                    # Update current node to the chosen one
                    current_node_id = choices[choice_index][0]
                    chosen_node = nodes[current_node_id]
                    
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
                            player_stats["experience"] += exp_change
                            print(f"\n✨ EXPERIENCE GAINED ✨")
                            print_box(f"You gained {exp_change} experience points.")
                        
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
    if player_stats["inventory"]:
        print(f"Items Collected: {', '.join(player_stats['inventory'])}")
    else:
        print("Items Collected: None")
    print("\nThanks for playing!")

if __name__ == "__main__":
    main() 
