import time
import json
import os
import re
import textwrap
import traceback
from arc import return_story_tree
from storygen import StoryState, enrich_scene
from json_cleaner import clean_and_parse_json

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
    for line in wrap_text(str(text), int(width)-2).split('\n'):
        try:
            print(f"| {str(line):<{int(width)-2}} |")
        except Exception as e:
            print(f"| ERROR PRINTING LINE: {e} | {line}")
    for _ in range(padding):
        print(empty)
    print(horizontal)

def print_box_dialogue(raw_dialogue: str, width: int = 70, padding: int = 1):
    """
    Prints dialogue inside a decorative box, inserting line breaks before each speaker tag '['
    (except at start), breaking lines at literal '\\n' or real newlines, and wrapping each part
    to fit within the box width.
    """
    dialogue = re.sub(r'\\\\n|\\n|\n', '\n', str(raw_dialogue))
    dialogue = re.sub(r'(?<!^)\[', r'\n[', dialogue)
    wrapped_lines = []
    for part in dialogue.splitlines():
        part = part.strip()
        if part:
            try:
                wrapped = textwrap.wrap(str(part), width=int(width)-4) or ['']
            except Exception as e:
                print(f"ERROR WRAPPING DIALOGUE: {e} | {part}")
                wrapped = [str(part)]
            wrapped_lines.extend(wrapped)
    horizontal = "+" + "-" * width + "+"
    empty = "|" + " " * width + "|"
    print(horizontal)
    for _ in range(padding):
        print(empty)
    for line in wrapped_lines:
        try:
            print(f"| {str(line):<{int(width)-2}} |")
        except Exception as e:
            print(f"| ERROR PRINTING DIALOGUE LINE: {e} | {line}")
    for _ in range(padding):
        print(empty)
    print(horizontal)

import sys # Added for potential detailed error printing if needed

def print_state(title, data, indent=2):
    """Print state information in a formatted way"""
    print(f"\n{'='*20} {title} {'='*20}")
    try:
        if title == "CHARACTERS PRESENT":
            # Check if the main data is a dictionary before processing
            if isinstance(data, dict):
                for char_name, char_data in data.items():
                    if char_name == "player":
                        continue  # Skip player character if found at this level

                    # Use elif to handle 'other_characters' specifically
                    elif char_name == "other_characters":
                        # Check if the value under 'other_characters' is a dict (expected)
                        if isinstance(char_data, dict):
                            print("\n► OTHER CHARACTERS (Dict Format)") # Clarify format
                            for npc_name, npc_data in char_data.items():
                                print(f"\n  ► {str(npc_name).upper()}")
                                if isinstance(npc_data, dict):
                                    # Health Bar
                                    health = int(npc_data.get('health', 0))
                                    # Ensure health is within 0-100 for bar display
                                    health = max(0, min(100, health))
                                    health_bar = '♥' * (health // 10) + '░' * ((100 - health) // 10)
                                    # Ensure bar is always 10 characters long
                                    health_bar = health_bar.ljust(10, '░')
                                    print(f"    Health: [{health_bar}] {health}/100")

                                    # Mood
                                    mood = str(npc_data.get('mood', 'unknown')).lower()
                                    mood_emoji = {
                                        'angry': '😠', 'happy': '😊', 'sad': '😢',
                                        'afraid': '😨', 'determined': '😤', 'sleeping': '😴',
                                        'neutral': '😐', 'aggressive': '😠', 'friendly': '🙂',
                                        'fearful': '😨', 'panicked': '😰', 'suspicious': '🤨'
                                    }.get(mood, '❓') # Use mood directly after lowercasing
                                    print(f"    Mood: {mood_emoji} {mood.capitalize()}") # Capitalize mood string

                                    # Status Effects
                                    if npc_data.get('status_effects'):
                                        effects = ', '.join(map(str, npc_data['status_effects']))
                                        print(f"    Status Effects: ✨ {effects}")

                                    # Relationships
                                    if npc_data.get('relationships'):
                                        print("    Relationships:")
                                        if isinstance(npc_data['relationships'], dict):
                                            for target, relation in npc_data['relationships'].items():
                                                print(f"     • {str(target)}: {str(relation)}")
                                        else:
                                            print(f"      (Unexpected relationship format: {type(npc_data['relationships'])})")
                                else:
                                    # Handle case where npc_data is not a dict
                                    print(f"    (Unexpected data format for NPC {npc_name}: {type(npc_data)})")
                        # Handle case where 'other_characters' value is a list
                        elif isinstance(char_data, list):
                            print("\n► OTHER CHARACTERS (List Format)")
                            for item in char_data:
                                if isinstance(item, dict):
                                    name = item.get('name', 'Unknown NPC')
                                    # Maybe print more details if available?
                                    print(f"    • {str(name)}")
                                else:
                                    print(f"    • Unknown item data: {str(item)}")
                        else:
                             # Handle unexpected format for 'other_characters' value
                            print(f"\n  (Unexpected format for 'other_characters' value: {type(char_data)})")

                    # Handle other top-level keys in the data dictionary (besides 'player' and 'other_characters')
                    else:
                        print(f"\n► {str(char_name).upper()} (Top Level)")
                        if isinstance(char_data, dict):
                           mood = char_data.get('mood', None)
                           if mood:
                                print(f"    Mood: {str(mood)}")
                           # Add more fields as needed for other top-level character types
                        else:
                            print(f"    (Data: {str(char_data)})") # Show the data if not a dict

            # Handle case where the main 'data' for characters is a list, not a dict
            elif isinstance(data, list):
                print("\n(Warning: Character data received in unexpected list format)")
                for item in data:
                     if isinstance(item, dict):
                         name = item.get('name', 'Unknown Character')
                         print(f"\n► {str(name).upper()} (from list)")
                         # Potentially add more details here if available in the dict item
                     else:
                         print(f"\n► Unknown Character Data (from list): {str(item)}")
            else:
                # Handle case where the main 'data' is neither a dict nor a list
                 print(f"\n(Warning: Unexpected character data format received: {type(data)})")
                 print(f"Raw Data: {str(data)}")

        elif title == "CURRENT SCENE":
            if isinstance(data, dict):
                print(f"\n  🌍 Location: {str(data.get('location', 'Unknown'))}")
                print(f"  🕒 Time: {str(data.get('time_of_day', 'Unknown'))}")
                print(f"  🌤️  Weather: {str(data.get('weather', 'Unknown'))}")
                print(f"  💫 Ambient: {str(data.get('ambient', 'Unknown'))}")
                # Add other scene details if necessary
            else:
                # Handle unexpected format for scene data
                print(f"\n  (Warning: Unexpected scene data format: {type(data)})")
                print(f"  Raw Scene Data: {str(data)}")

        # Add elif blocks here for other potential titles

    except Exception as e:
        # More detailed error printing
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = exc_tb.tb_frame.f_code.co_filename
        print(f"\n[PRINT_STATE ERROR] Type: {exc_type}, File: {fname}, Line: {exc_tb.tb_lineno}")
        print(f"  Error Message: {e}")
        print(f"  Problematic Data (type: {type(data)}): {str(data)[:200]}...") # Print start of data

    # Footer line matches header length
    print("\n" + "=" * (42 + len(str(title))))

def load_game(theme, depth=3, choices_per_node=2):
    """Generate and load a new story tree"""
    # Clean up old story files first
    for f in os.listdir():
        if f.startswith('story_') and f.endswith('.json'):
            try:
                os.remove(f)
                print(f"Removed old story file: {f}")
            except:
                pass
                
    # Generate a new story tree
    print(f"\nGenerating a {theme} story with depth {depth} and {choices_per_node} choices per node...")
    print("This may take a minute or two while we create an interesting adventure for you...\n")
    
    filename = return_story_tree(theme, depth, choices_per_node)
    
    # Load the saved game state
    try:
        with open(filename, 'r') as f:
            save_data = json.load(f)
            
        # Extract graph data
        graph_data = save_data.get("graph", {})
        
        # Build a proper tree structure for navigation
        nodes = {}
        
        # First pass: create all nodes
        for node_id, node_data in graph_data["nodes"].items():
            story_text = node_data["story"]
            
            # Ensure the story text is complete and well-formatted
            if not story_text.endswith(('.', '!', '?')):
                story_text += '.'
                
            nodes[node_id] = {
                "story": story_text,
                "is_end": node_data.get("is_end", False),
                "dialogue": node_data.get("dialogue", ""),
                "children": []
            }
        
        # Create a mapping of parent to child nodes
        parent_to_children = {}
        for edge in graph_data["edges"]:
            from_id = edge["from"]
            to_id = edge["to"]
            if from_id not in parent_to_children:
                parent_to_children[from_id] = []
            parent_to_children[from_id].append(to_id)
        
        # Second pass: add child nodes to parents
        for node_id in nodes:
            if node_id in parent_to_children:
                nodes[node_id]["children"] = parent_to_children[node_id]
                
                # For each child node that represents a choice, ensure it's a concise action
                for child_id in parent_to_children[node_id]:
                    child_text = nodes[child_id]["story"]
                    
                    # Create a concise, action-oriented choice text
                    action_verbs = ["Investigate", "Explore", "Search", "Talk to", "Approach", "Examine", 
                                   "Hide", "Ask", "Move", "Look", "Find", "Go", "Take", "Use", "Try",
                                   "Call", "Fight", "Attack", "Defend", "Retreat", "Run", "Escape",
                                   "Sneak", "Climb", "Jump", "Swim", "Dive", "Grab", "Push", "Pull"]
                    
                    # Store the original story text in a full_story field
                    nodes[child_id]["full_story"] = child_text
                    
                    # Determine if the text already starts with a verb
                    found_verb = None
                    for verb in action_verbs:
                        if child_text.startswith(verb):
                            found_verb = verb
                            break
                    
                    # Extract first sentence only for the choice
                    first_sentence = ""
                    sentences = re.split(r'(?<=[.!?])\s+', child_text)
                    if sentences:
                        first_sentence = sentences[0]
                    else:
                        first_sentence = child_text
                    
                    # If it doesn't start with a verb, add one
                    if not found_verb:
                        # Choose an appropriate verb based on the content
                        verb_to_use = "Investigate"
                        choice_text = f"{verb_to_use} {first_sentence}"
                    else:
                        # Just use the first sentence as is, since it already starts with a verb
                        choice_text = first_sentence
                    
                    # Ensure choice text is appropriate length (max 80 chars)
                    if len(choice_text) > 80:
                        words = choice_text.split()
                        choice_text = " ".join(words[:10])
                        if not choice_text.endswith(('.', '!', '?')):
                            choice_text += "..."
                    
                    # Store the concise choice text
                    nodes[child_id]["choice_text"] = choice_text
        
        # Print debug info
        print(f"Successfully loaded story with {len(nodes)} nodes.")
        return nodes, "node_0", depth
    except Exception as e:
        print(f"Error loading game: {e}")
        traceback.print_exc()
        return None, None, None

def main():
    # Initialize story state and player
    try:

        print("\nWelcome to the Interactive Story Generator!\n")
        
        # Get user input for theme
        theme = input("Enter a theme for your adventure (e.g., space, fantasy, mystery): ").strip()
        if not theme:
            theme = "adventure"
            
        # Get depth and choices per node from user
        depth = 6  # Default
        choices_per_node = 2  # Default
        
        try:
            depth_input = input(f"How deep would you like your story to be? (default: {depth}): ").strip()
            if depth_input:
                depth = int(depth_input)
                if depth < 3:
                    depth = 3
                    print("Minimum depth is 3. Using depth = 3.")
                elif depth > 12:
                    depth = 12
                    print("Maximum depth is 12. Using depth = 12.")
        except ValueError:
            print(f"Invalid input. Using default depth = {depth}.")
            
        try:
            choices_input = input(f"How many choices at each decision point? (2-4, default: {choices_per_node}): ").strip()
            if choices_input:
                choices_per_node = int(choices_input)
                if choices_per_node < 2:
                    choices_per_node = 2
                    print("Minimum choices is 2. Using choices = 2.")
                elif choices_per_node > 4:
                    choices_per_node = 4
                    print("Maximum choices is 4. Using choices = 4.")
        except ValueError:
            print(f"Invalid input. Using default choices = {choices_per_node}.")
        
    
        # Load game state
        nodes, current_node_id, max_depth = load_game(theme, depth, choices_per_node)
        
        if not nodes:
            print("Failed to initialize game. Exiting.")
            return
        
        # Game loop
        story_state = StoryState(theme=theme, max_depth=max_depth)
        
        while True:
            # Clear screen
            clear_screen()
            
            # Get current node
            current_node = nodes[current_node_id]
            
            # Update story state
            story_state.current_scene = current_node["story"]
            story_state.visited_nodes.append(current_node_id)
            
            # Display the scene
            print(f"\n📜 CURRENT SCENE 📜")
            print_box(current_node["story"])
            
            # Add dialogue if available
            scene_dialogue = current_node.get("dialogue", "")
            if not scene_dialogue and current_node_id != "node_0":
                # Generate scene dialogue using AI for non-start nodes
                try:
                    scene_dialogue = enrich_scene(story_state)
                    current_node["dialogue"] = scene_dialogue
                except Exception as e:
                    print(f"Could not generate dialogue: {e}")
            
            if scene_dialogue:
                print("\n💬 REACTION 💬")
                print_box(scene_dialogue)
            
            # Check if we've reached an ending
            if current_node["is_end"] or not current_node["children"]:
                print("\nYou've reached the end of your journey!")
                break
            
            # Get child nodes (choices) for the current node
            choices = []
            for child_id in current_node["children"]:
                # Use the concise choice_text if available, otherwise fallback to story
                choice_text = nodes[child_id].get("choice_text", nodes[child_id]["story"])
                choices.append((child_id, choice_text))
            
            # Display choices
            print("\n🎲 AVAILABLE CHOICES 🎲")
            print(f"╔{'═'*68}╗")
            
            for i, (_, choice_text) in enumerate(choices):
                # Wrap the choice text to fit within the box
                wrapped_lines = textwrap.wrap(choice_text, width=66)
                
                # Print the first line with the choice number
                first_line = wrapped_lines[0] if wrapped_lines else ""
                print(f"║ {i+1}. {first_line:<65} ║")
                
                # Print any additional lines
                for line in wrapped_lines[1:]:
                    print(f"║    {line:<65} ║")
                
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
                        # Get the child node ID
                        child_id = choices[choice_index][0]
                        
                        # When we select a choice, use the full story text for display in the next scene
                        if "full_story" in nodes[child_id]:
                            nodes[child_id]["story"] = nodes[child_id]["full_story"]
                            
                        # Update current node
                        current_node_id = child_id
                        valid_choice = True
                    else:
                        print(f"Please enter a number between 1 and {len(choices)}.")
                except ValueError:
                    print("Please enter a valid number.")
        
        # Game over screen
        print("\nGame Over!")
        print("=" * 50)
        print("\nThanks for playing!")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    if os.path.exists("game_save.json"):
        os.remove("game_save.json")
        
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        print("Game initialization failed. Please try again.")