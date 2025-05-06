from google import genai
import json
import os
import time
import hashlib
import traceback
from Graph_Classes.Structure import Node, Graph
import re
from clean_and_parse_json import clean_and_parse_json

GOOGLE_API_KEY = "AIzaSyAEcjdAjZjmecdsKIb21-Gu2bq6m7zfKaE"
client = genai.Client(api_key=GOOGLE_API_KEY)

class StoryState:
    def __init__(self):
        self.characters = {}
        self.current_scene = {}
        self.inventory = []
        self.visited_nodes = set()
        self.theme = ""  

    def to_dict(self):
        return {
            "characters": self.characters,
            "current_scene": self.current_scene,
            "inventory": self.inventory,
            "visited_nodes": list(self.visited_nodes),
            "theme": self.theme  
        }

    @classmethod
    def from_dict(cls, data):
        state = cls()
        state.characters = data["characters"]
        state.current_scene = data["current_scene"]
        state.inventory = data["inventory"]
        state.visited_nodes = set(data["visited_nodes"])
        state.theme = data.get("theme", "")  
        return state

def generate_story_arc(theme):
    """Generate a high-level story arc for the given theme"""
    prompt = f"""
    Generate a rich story arc for an interactive narrative based on the {theme} theme.
    Include the major stages of the narrative journey, from introduction to conclusion.
    Structure it similarly to a classic hero's journey with challenges, setbacks, and growth.
    
    Your response should include:
    - An initial hook or inciting incident that draws players in
    - Major plot points that would form the backbone of the story
    - Important character development moments
    - At least two potential branching narrative paths 
    - Several key decision points where the story could meaningfully diverge
    - Both successes and setbacks the player might experience
    - Multiple possible endings based on player choices
    - Setting-specific details that incorporate the {theme} theme throughout
    
    Format your response as a clear outline with numbered sections and bullet points.
    Focus on creating a compelling narrative framework that will engage players.
    """
    
    try:
        response = client.models.generate_content(
            contents=[prompt],
            model="gemini-2.0-flash",
        )
        
        if not response.text:
            raise Exception("Empty response from API")
            
        return response.text
    except Exception as e:
        print(f"\nError generating story arc: {e}")
        return f"Basic adventure with a {theme} setting featuring a hero who must overcome challenges and make critical choices."

def generate_story_tree(theme, story_arc, depth=3, choices_per_node=4):
    """Generate a story tree with the specified depth and number of choices per node"""
    # Define the root prompt
    root_prompt = f"""
    Create a story node for an interactive narrative game set in the world of {theme}.
    Use the following story arc as a guide:
    {story_arc}
    
    This should be the introduction to our story, establishing the setting, main character, and initial situation.
    Don't add any meta-text about JSON - just provide the valid JSON object directly.
    
    EXTREMELY IMPORTANT: For each choice, create a clear ACTION that the PLAYER can take - something they DO, not what they see.
    Each choice MUST:
    1. Start with a strong action verb (e.g., "Climb the...", "Confront the...", "Sabotage the...")
    2. Be written in 2nd person perspective ("you")
    3. Include 1-2 sentences that describe WHAT the player does, not what happens next
    4. Focus on the player's agency and decision-making
    
    BAD CHOICE EXAMPLES (DO NOT USE THESE FORMATS):
    - "The corridor leads to a control room" (describes scene, not action)
    - "A guard approaches from the shadows" (describes event, not player action)
    - "The area seems dangerous" (observation, not action)
    
    GOOD CHOICE EXAMPLES (USE THESE FORMATS):
    - "Sneak past the guards using the ventilation shaft, hoping your stealth training pays off."
    - "Confront the imperial officer directly, demanding answers about the rebel base location."
    - "Hack into the security terminal to disable the alarm systems before proceeding further."
    
    Return a valid JSON object with this structure:
    {{
        "story": "rich descriptive text that introduces the story",
        "is_ending": false,
        "choices": [
            {{
                "text": "Action the player takes (1-2 sentences starting with a verb)",
                "consequences": "brief description of immediate results"
            }},
            {{
                "text": "Different action the player takes (1-2 sentences starting with a verb)",
                "consequences": "brief description of immediate results"
            }}
            ... additional choices as needed ...
        ]
    }}
    """
    
    # Generate the root node first
    print(f"Generating root node for {theme} story...")
    root_data = generate_story_node(root_prompt, is_root=True)
    if not root_data:
        print("Failed to generate root node!")
        return None
    
    # Create the story graph
    story_graph = {"nodes": {}, "edges": []}
    
    # Add root node
    root_id = "node_0"
    story_graph["nodes"][root_id] = {
        "story": root_data.get("story", f"You begin your {theme} adventure!"),
        "is_end": False,
        "dialogue": ""
    }
    
    # Process each child node up to the specified depth
    nodes_to_process = []
    
    # Add initial choices from the root
    root_choices = root_data.get("choices", [])
    
    # Make sure we have exactly choices_per_node choices
    if len(root_choices) < choices_per_node:
        print(f"Root node has fewer than {choices_per_node} choices. Adding generic choices...")
        # Add generic choices to reach choices_per_node
        action_verbs = ["Investigate", "Scout", "Approach", "Examine", "Search", "Challenge", "Confront", "Infiltrate"]
        objects = ["mysterious door", "nearby structure", "strange artifact", "shadowy figure", "central area", "control panel", "hidden passage"]
        methods = ["cautiously", "boldly", "stealthily", "carefully", "quickly", "methodically", "decisively", "tactically"]
        
        while len(root_choices) < choices_per_node:
            choice_idx = len(root_choices)
            verb = action_verbs[choice_idx % len(action_verbs)]
            obj = objects[(choice_idx + 2) % len(objects)]
            method = methods[(choice_idx + 4) % len(methods)]
            
            root_choices.append({
                "text": f"{verb} the {obj} {method}, looking for any clues or advantages you can find.",
                "consequences": f"You take action, staying alert to any potential dangers."
            })
    elif len(root_choices) > choices_per_node:
        print(f"Root node has more than {choices_per_node} choices. Truncating...")
        root_choices = root_choices[:choices_per_node]
    
    # Validate that choices are action-oriented
    for i, choice in enumerate(root_choices):
        choice_text = choice["text"]
        # Ensure choice starts with a verb
        first_word = choice_text.split()[0].lower()
        action_verbs = ["search", "investigate", "approach", "examine", "open", "enter", "take", "grab", "talk", "speak", 
                        "fight", "attack", "run", "flee", "hide", "sneak", "climb", "jump", "use", "activate", "deactivate", 
                        "hack", "break", "repair", "craft", "create", "destroy", "help", "save", "rescue", "abandon", 
                        "follow", "lead", "explore", "scout", "observe", "analyze", "study", "question", "interrogate"]
        
        if not any(first_word == verb or first_word.startswith(verb) for verb in action_verbs):
            # Fix the choice to be action-oriented
            action_verb = action_verbs[i % len(action_verbs)]
            if "the" in choice_text or "a " in choice_text:
                # Try to extract an object from the existing text
                parts = choice_text.split()
                for j, word in enumerate(parts):
                    if word.lower() in ["the", "a", "an"] and j < len(parts) - 1:
                        object_word = parts[j:j+2]
                        choice["text"] = f"{action_verb.capitalize()} {' '.join(object_word)} to learn more about what's happening."
                        break
                else:
                    choice["text"] = f"{action_verb.capitalize()} the area to discover what opportunities lie ahead."
            else:
                choice["text"] = f"{action_verb.capitalize()} the surrounding area to gather more information."
    
    for i, choice in enumerate(root_choices):
        choice_id = f"node_0_{i+1}"
        story_graph["nodes"][choice_id] = {
            "story": choice["text"],
            "is_end": False,
            "dialogue": choice.get("consequences", "")
        }
        story_graph["edges"].append({"from": root_id, "to": choice_id})
        
        if depth > 1:  # Only add to processing queue if depth > 1
            nodes_to_process.append((choice_id, 1))  # Depth starts at 1
    
    # BFS traversal to generate the full tree
    total_nodes = 1 + len(root_choices)  # Root + initial choices
    print(f"Generated {total_nodes} nodes so far")
    
    while nodes_to_process:
        current_id, current_depth = nodes_to_process.pop(0)
        
        print(f"Processing node {current_id} at depth {current_depth}")
        
        if current_depth >= depth:
            # Mark as an ending node if we've reached max depth
            story_graph["nodes"][current_id]["is_end"] = True
            print(f"Node {current_id} marked as ending (at max depth {depth})")
            continue
            
        # Generate children for this node
        node_prompt = f"""
        Create a continuation of our {theme} interactive story.
        
        Previous scene: {story_graph["nodes"][current_id]["story"]}
        Narrative arc: {story_arc}
        
        EXTREMELY IMPORTANT: For each choice, create a clear ACTION that the PLAYER can take - something they DO, not what they see.
        Each choice MUST:
        1. Start with a strong action verb (e.g., "Climb the...", "Confront the...", "Sabotage the...")
        2. Be written in 2nd person perspective ("you")
        3. Include 1-2 sentences that describe WHAT the player does, not what happens next
        4. Focus on the player's agency and decision-making
        
        BAD CHOICE EXAMPLES (DO NOT USE THESE FORMATS):
        - "The corridor leads to a control room" (describes scene, not action)
        - "A guard approaches from the shadows" (describes event, not player action)
        - "The area seems dangerous" (observation, not action)
        
        GOOD CHOICE EXAMPLES (USE THESE FORMATS):
        - "Sneak past the guards using the ventilation shaft, hoping your stealth training pays off."
        - "Confront the imperial officer directly, demanding answers about the rebel base location."
        - "Hack into the security terminal to disable the alarm systems before proceeding further."
        
        The AI assistant should provide EXACTLY {choices_per_node} action choices, each representing something the player ACTIVELY DOES.
                
        Return a valid JSON object with exactly {choices_per_node} choices:
        {{
            "story": "rich descriptive text that continues from the previous node",
            "is_ending": {"true" if current_depth >= depth-1 else "false"},
            "choices": [
                {{
                    "text": "Action the player takes (1-2 sentences starting with a verb)",
                    "consequences": "brief description of immediate results"
                }},
                // EXACTLY {choices_per_node-1} MORE CHOICES HERE, ALL ACTION-ORIENTED
            ]
        }}
        """
    
        child_data = generate_story_node(node_prompt)
        if not child_data:
            print(f"Failed to generate children for node {current_id}. Using fallback.")
            action_verbs = ["Investigate", "Scout", "Approach", "Examine", "Search", "Challenge", "Confront", "Infiltrate"]
            objects = ["mysterious door", "nearby structure", "strange artifact", "shadowy figure", "central area", "control panel", "hidden passage"]
            methods = ["cautiously", "boldly", "stealthily", "carefully", "quickly", "methodically", "decisively", "tactically"]
            
            child_data = {
                "story": "The story continues as you consider your next move.",
                "is_ending": current_depth >= depth-1,
                "choices": [
                    {
                        "text": f"{action_verbs[i % len(action_verbs)]} the {objects[(i+2) % len(objects)]} {methods[(i+4) % len(methods)]}, looking for any advantages you can gain.",
                        "consequences": f"You take decisive action, ready for whatever comes next."
                    }
                    for i in range(choices_per_node)
                ]
            }
        
        # Process choices for this node
        child_choices = child_data.get("choices", [])
        
        # Ensure we have the right number of choices
        if len(child_choices) < choices_per_node:
            # Add generic choices to reach choices_per_node
            print(f"Node {current_id}: Adding generic choices ({len(child_choices)} → {choices_per_node})")
            action_verbs = ["Investigate", "Scout", "Approach", "Examine", "Search", "Challenge", "Confront", "Infiltrate"]
            objects = ["mysterious door", "nearby structure", "strange artifact", "shadowy figure", "central area", "control panel", "hidden passage"]
            methods = ["cautiously", "boldly", "stealthily", "carefully", "quickly", "methodically", "decisively", "tactically"]
            
            while len(child_choices) < choices_per_node:
                choice_idx = len(child_choices)
                verb = action_verbs[choice_idx % len(action_verbs)]
                obj = objects[(choice_idx + 2) % len(objects)]
                method = methods[(choice_idx + 4) % len(methods)]
                
                child_choices.append({
                    "text": f"{verb} the {obj} {method}, looking for any clues or advantages you can find.",
                    "consequences": f"You take action, staying alert to any potential dangers."
                })
            print(f"Node {current_id}: Now has {len(child_choices)} choices")
        elif len(child_choices) > choices_per_node:
            print(f"Node {current_id}: Truncating choices ({len(child_choices)} → {choices_per_node})")
            child_choices = child_choices[:choices_per_node]
            
        # Double-check we have exactly choices_per_node choices
        if len(child_choices) != choices_per_node and not (current_depth >= depth-1):
            print(f"WARNING: Node {current_id} still has {len(child_choices)} choices (expected {choices_per_node})")
            # Force exactly choices_per_node choices
            while len(child_choices) < choices_per_node:
                choice_idx = len(child_choices)
                verb = action_verbs[choice_idx % len(action_verbs)]
                obj = objects[(choice_idx + 2) % len(objects)]
                method = methods[(choice_idx + 4) % len(methods)]
                
                child_choices.append({
                    "text": f"{verb} the {obj} {method}, looking for any advantages you can gain.",
                    "consequences": f"You take decisive action, ready for whatever comes next."
                })
            child_choices = child_choices[:choices_per_node]
        
        # Validate that choices are action-oriented
        for i, choice in enumerate(child_choices):
            choice_text = choice["text"]
            # Ensure choice starts with a verb
            first_word = choice_text.split()[0].lower()
            action_verbs = ["search", "investigate", "approach", "examine", "open", "enter", "take", "grab", "talk", "speak", 
                            "fight", "attack", "run", "flee", "hide", "sneak", "climb", "jump", "use", "activate", "deactivate", 
                            "hack", "break", "repair", "craft", "create", "destroy", "help", "save", "rescue", "abandon", 
                            "follow", "lead", "explore", "scout", "observe", "analyze", "study", "question", "interrogate"]
            
            if not any(first_word == verb or first_word.startswith(verb) for verb in action_verbs):
                # Fix the choice to be action-oriented
                action_verb = action_verbs[i % len(action_verbs)]
                if "the" in choice_text or "a " in choice_text:
                    # Try to extract an object from the existing text
                    parts = choice_text.split()
                    for j, word in enumerate(parts):
                        if word.lower() in ["the", "a", "an"] and j < len(parts) - 1:
                            object_word = parts[j:j+2]
                            choice["text"] = f"{action_verb.capitalize()} {' '.join(object_word)} to learn more about what's happening."
                            break
                    else:
                        choice["text"] = f"{action_verb.capitalize()} the area to discover what opportunities lie ahead."
                else:
                    choice["text"] = f"{action_verb.capitalize()} the surrounding area to gather more information."
        
        # Update the story text for current node if we have a better one
        if child_data.get("story"):
            story_graph["nodes"][current_id]["story"] = child_data["story"]
            
        # Add children
        for i, choice in enumerate(child_choices):
            # Create child node ID that preserves path information (appending to parent ID)
            choice_id = f"{current_id}_{i+1}"
            
            # Determine if this should be an ending node based on depth
            is_ending = current_depth >= depth-1
            if is_ending:
                print(f"Node {choice_id} will be an ending (depth {current_depth+1} >= max_depth-1 {depth-1})")
            
            story_graph["nodes"][choice_id] = {
                "story": choice["text"],
                "is_end": is_ending,
                "dialogue": choice.get("consequences", "")
            }
            story_graph["edges"].append({"from": current_id, "to": choice_id})
            
            # Add to total node count
            total_nodes += 1
            
            if not is_ending:  # Only process non-ending nodes
                nodes_to_process.append((choice_id, current_depth + 1))
    
    print(f"Story tree generation complete with {len(story_graph['nodes'])} nodes and {len(story_graph['edges'])} edges")
    
    # Verify all nodes at depth are marked as endings
    for node_id, node_data in story_graph["nodes"].items():
        node_depth = len(node_id.split('_')) - 1
        if node_depth >= depth:
            if not node_data["is_end"]:
                print(f"Correcting node {node_id} at depth {node_depth} to be an ending")
                node_data["is_end"] = True
        elif node_depth < depth and node_data["is_end"]:
            # Only correct if this node has children
            has_children = False
            for edge in story_graph["edges"]:
                if edge["from"] == node_id:
                    has_children = True
                    break
            
            if has_children:
                print(f"Correcting node {node_id} at depth {node_depth} to NOT be an ending")
                node_data["is_end"] = False
    
    return story_graph

def generate_story_node(prompt, is_root=False):
    """Generate a story node with rich content based on current context"""
    try:
        response = client.models.generate_content(
            contents=[prompt],
            model="gemini-2.0-flash",
        )
        
        if not response.text:
            print("Error: Empty response from API")
            return None
            
        raw_text = response.text.strip()
        
        if raw_text.startswith("```"):
            lines = raw_text.split('\n')
            if lines[0].startswith("```") and lines[-1].startswith("```"):
                raw_text = '\n'.join(lines[1:-1])
            elif lines[0].startswith("```"):
                raw_text = '\n'.join(lines[1:])
        
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        
        # Try to extract the JSON portion
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}') + 1
        if start_idx < 0 or end_idx <= 0:
            print(f"JSON boundaries not found in: {raw_text[:100]}...")
            return None
            
        json_text = raw_text[start_idx:end_idx]
        
        # Try to clean and parse the JSON to ensure it's valid
        cleaned_json = clean_and_parse_json(json_text)
        if cleaned_json is None:
            print("Failed to parse node JSON")
            return None
            
        print("Node generated successfully")
        return cleaned_json
    except Exception as e:
        print(f"Error generating story node: {e}")
        print(traceback.format_exc())
        return None

def return_story_arc(theme):
    """Wrapper function to get story arc"""
    return generate_story_arc(theme)

def return_story_tree(theme, depth=3, choices_per_node=4):
    """
    Generate and save a story tree for the given theme
    Returns the path to the saved JSON file
    """
    story_arc = generate_story_arc(theme)
    story_graph = generate_story_tree(theme, story_arc, depth, choices_per_node)
    
    # Create scene states and character data
    for node_id, node_data in story_graph["nodes"].items():
        story_text = node_data["story"].lower()
        
        # Generate location based on story content and theme
        location = "unknown"
        if "castle" in story_text or "fortress" in story_text or "tower" in story_text:
            location = "Ancient Castle"
        elif "forest" in story_text or "woods" in story_text or "trees" in story_text:
            location = "Mysterious Forest"
        elif "cave" in story_text or "cavern" in story_text or "underground" in story_text:
            location = "Deep Caverns"
        elif "city" in story_text or "town" in story_text or "urban" in story_text:
            location = "City District"
        elif "ship" in story_text or "spacecraft" in story_text or "space" in story_text:
            location = "Starship Deck"
        elif "lab" in story_text or "laboratory" in story_text or "facility" in story_text:
            location = "Research Facility"
        elif "temple" in story_text or "shrine" in story_text or "sacred" in story_text:
            location = "Ancient Temple"
        elif "mountain" in story_text or "hill" in story_text or "peak" in story_text:
            location = "Mountain Pass"
        elif "desert" in story_text or "sand" in story_text or "dune" in story_text:
            location = "Vast Desert"
        elif "ocean" in story_text or "sea" in story_text or "beach" in story_text:
            location = "Coastal Shore"
        elif "village" in story_text or "settlement" in story_text or "hamlet" in story_text:
            location = "Small Village"
        
        # Theme-specific locations as fallback
        if location == "unknown":
            if "star wars" in theme.lower() or "space" in theme.lower() or "sci-fi" in theme.lower():
                locations = ["Rebel Base", "Imperial Station", "Space Outpost", "Alien Planet", "Derelict Ship"]
                location = locations[hash(node_id) % len(locations)]
            elif "fantasy" in theme.lower() or "medieval" in theme.lower() or "magic" in theme.lower():
                locations = ["Enchanted Grove", "Dragon's Lair", "Wizard's Tower", "Royal Castle", "Dwarven Mines"]
                location = locations[hash(node_id) % len(locations)]
            elif "cyberpunk" in theme.lower() or "future" in theme.lower() or "tech" in theme.lower():
                locations = ["Neon District", "Corporate HQ", "Underground Bunker", "Virtual Reality", "Hacker's Den"]
                location = locations[hash(node_id) % len(locations)]
            elif "horror" in theme.lower() or "scary" in theme.lower() or "spooky" in theme.lower():
                locations = ["Abandoned Mansion", "Foggy Graveyard", "Cursed Forest", "Decrepit Hospital", "Dark Cellar"]
                location = locations[hash(node_id) % len(locations)]
            elif "western" in theme.lower() or "wild west" in theme.lower():
                locations = ["Dusty Saloon", "Desert Canyon", "Sheriff's Office", "Ghost Town", "Train Station"]
                location = locations[hash(node_id) % len(locations)]
            elif "detective" in theme.lower() or "mystery" in theme.lower() or "noir" in theme.lower():
                locations = ["Crime Scene", "Detective's Office", "Shady Alley", "Upscale Club", "Abandoned Warehouse"]
                location = locations[hash(node_id) % len(locations)]
            elif "superhero" in theme.lower() or "avengers" in theme.lower() or "hero" in theme.lower():
                locations = ["City Rooftop", "Secret Hideout", "Villain's Lair", "Downtown Battlefield", "Research Lab"]
                location = locations[hash(node_id) % len(locations)]
            else:
                # Generic interesting locations if theme doesn't match any category
                locations = ["Crystal Caves", "Ancient Ruins", "Hidden Valley", "Forgotten Sanctuary", "Misty Lake"]
                location = locations[hash(node_id) % len(locations)]
        
        # Time of day based on story content
        time_of_day = "day"
        if "night" in story_text or "dark" in story_text or "shadow" in story_text:
            time_of_day = "night"
        elif "evening" in story_text or "sunset" in story_text or "dusk" in story_text:
            time_of_day = "evening"
        elif "dawn" in story_text or "sunrise" in story_text or "morning" in story_text:
            time_of_day = "dawn"
        elif "noon" in story_text or "midday" in story_text:
            time_of_day = "noon"
        else:
            # Varied times of day if not specified in text
            times = ["dawn", "morning", "noon", "afternoon", "evening", "dusk", "twilight", "night", "midnight"]
            time_of_day = times[hash(node_id) % len(times)]
        
        # Weather based on story content and mood
        weather = "clear"
        if "rain" in story_text or "storm" in story_text or "thunder" in story_text:
            weather = "stormy"
        elif "snow" in story_text or "ice" in story_text or "frost" in story_text or "winter" in story_text:
            weather = "snowy"
        elif "fog" in story_text or "mist" in story_text or "haze" in story_text:
            weather = "foggy"
        elif "cloud" in story_text or "overcast" in story_text:
            weather = "cloudy"
        elif "sun" in story_text or "sunny" in story_text or "bright" in story_text:
            weather = "sunny"
        elif "wind" in story_text or "breeze" in story_text or "gust" in story_text:
            weather = "windy"
        else:
            # Weather based on node depth and story progression
            node_depth = len(node_id.split('_')) - 1
            weathers = ["clear", "partly cloudy", "foggy", "light rain", "stormy", "windy", "hazy"]
            weather = weathers[(hash(node_id) + node_depth) % len(weathers)]
        
        # Ambient mood based on story content
        ambient = "mysterious"
        if any(word in story_text for word in ["danger", "threat", "attack", "fight", "battle"]):
            ambient = "tense"
        elif any(word in story_text for word in ["discover", "find", "reveal", "secret", "hidden"]):
            ambient = "mysterious"
        elif any(word in story_text for word in ["ruin", "ancient", "old", "dust", "decay"]):
            ambient = "abandoned"
        elif any(word in story_text for word in ["beautiful", "stunning", "impressive", "breathtaking"]):
            ambient = "magnificent"
        elif any(word in story_text for word in ["scary", "terrifying", "horror", "fear", "dread"]):
            ambient = "eerie"
        elif any(word in story_text for word in ["sacred", "holy", "divine", "religious", "spiritual"]):
            ambient = "reverent"
        elif any(word in story_text for word in ["busy", "crowd", "people", "populated", "active"]):
            ambient = "bustling"
        elif any(word in story_text for word in ["quiet", "silent", "still", "peaceful", "calm"]):
            ambient = "tranquil"
        elif any(word in story_text for word in ["royal", "noble", "wealth", "rich", "luxury"]):
            ambient = "opulent"
        elif any(word in story_text for word in ["alien", "strange", "unfamiliar", "bizarre", "weird"]):
            ambient = "otherworldly"
        else:
            # Varied ambient moods based on node
            ambients = ["tense", "mysterious", "serene", "chaotic", "magical", "foreboding", 
                        "peaceful", "ominous", "enchanted", "desolate", "vibrant", "haunting"]
            ambient = ambients[hash(node_id) % len(ambients)]
        
        # Add scene state to node data
        node_data["scene_state"] = {
            "location": location,
            "time_of_day": time_of_day,
            "weather": weather,
            "ambient": ambient
        }
        
        # Add placeholder character data
        node_data["characters"] = {
            "player": {
                "health": 100,
                "mood": "determined",
                "status_effects": [],
                "experience": 10,
                "inventory": []
            }
        }
        
        # Add other characters based on the theme and story content
        story_text = node_data["story"].lower()
        node_depth = len(node_id.split('_')) - 1

        # Check if the story mentions specific character types
        has_enemy = any(word in story_text for word in ["enemy", "villain", "foe", "opponent", "adversary", "antagonist"])
        has_ally = any(word in story_text for word in ["ally", "friend", "companion", "partner", "helper", "supporter"])
        has_neutral = any(word in story_text for word in ["stranger", "merchant", "traveler", "native", "inhabitant", "civilian"])

        # Character generation based on theme
        possible_characters = []
        
        # Common character types based on theme
        if "star wars" in theme.lower() or "sci-fi" in theme.lower() or "space" in theme.lower():
            possible_characters = [
                {"name": "Imperial Officer", "type": "enemy", "mood": "hostile", "description": "A stern officer in a gray uniform"},
                {"name": "Rebel Spy", "type": "ally", "mood": "cautious", "description": "A nervous individual with vital information"},
                {"name": "Jedi Knight", "type": "ally", "mood": "calm", "description": "A robed figure with a lightsaber at their belt"},
                {"name": "Bounty Hunter", "type": "neutral", "mood": "calculating", "description": "A heavily armed mercenary watching your movements"},
                {"name": "Smuggler", "type": "neutral", "mood": "shifty", "description": "A rugged spacer looking for a deal"},
                {"name": "Droid", "type": "neutral", "mood": "helpful", "description": "A mechanical assistant beeping occasionally"}
            ]
        elif "fantasy" in theme.lower() or "medieval" in theme.lower() or "magic" in theme.lower():
            possible_characters = [
                {"name": "Knight", "type": "ally", "mood": "honorable", "description": "A warrior in shining armor"},
                {"name": "Wizard", "type": "neutral", "mood": "mysterious", "description": "A robed figure with a staff"},
                {"name": "Goblin", "type": "enemy", "mood": "aggressive", "description": "A small, green creature with sharp teeth"},
                {"name": "Merchant", "type": "neutral", "mood": "greedy", "description": "A well-dressed trader with valuable goods"},
                {"name": "Elf Scout", "type": "ally", "mood": "alert", "description": "A graceful archer watching from nearby"},
                {"name": "Dragon", "type": "enemy", "mood": "imposing", "description": "A massive scaled beast eyeing you carefully"}
            ]
        elif "cyberpunk" in theme.lower() or "future" in theme.lower() or "tech" in theme.lower():
            possible_characters = [
                {"name": "Hacker", "type": "ally", "mood": "paranoid", "description": "A nervy individual surrounded by screens"},
                {"name": "Corporate Agent", "type": "enemy", "mood": "cold", "description": "A suit-wearing professional with hidden weapons"},
                {"name": "Street Doc", "type": "neutral", "mood": "practical", "description": "A back-alley surgeon with cybernetic arms"},
                {"name": "Fixer", "type": "neutral", "mood": "businesslike", "description": "A well-connected middleman with many favors owed"},
                {"name": "Rogue AI", "type": "enemy", "mood": "calculating", "description": "A digital entity speaking through nearby screens"},
                {"name": "Mercenary", "type": "enemy", "mood": "threatening", "description": "A heavily augmented soldier for hire"}
            ]
        elif "horror" in theme.lower() or "scary" in theme.lower():
            possible_characters = [
                {"name": "Mysterious Stranger", "type": "neutral", "mood": "unsettling", "description": "A pale figure watching from the shadows"},
                {"name": "Cultist", "type": "enemy", "mood": "fanatic", "description": "A robed zealot muttering strange phrases"},
                {"name": "Survivor", "type": "ally", "mood": "terrified", "description": "A traumatized individual with vital information"},
                {"name": "Paranormal Investigator", "type": "ally", "mood": "curious", "description": "A scholarly figure with strange equipment"},
                {"name": "Possessed Victim", "type": "enemy", "mood": "erratic", "description": "A person with unnatural movements and blank eyes"},
                {"name": "Ancient Entity", "type": "enemy", "mood": "malevolent", "description": "A presence that defies natural laws"}
            ]
        elif "detective" in theme.lower() or "noir" in theme.lower() or "mystery" in theme.lower():
            possible_characters = [
                {"name": "Inspector", "type": "neutral", "mood": "suspicious", "description": "A sharp-eyed officer of the law"},
                {"name": "Informant", "type": "ally", "mood": "nervous", "description": "A jumpy character with street knowledge"},
                {"name": "Witness", "type": "neutral", "mood": "hesitant", "description": "Someone who saw something important"},
                {"name": "Suspect", "type": "neutral", "mood": "defensive", "description": "A person of interest with something to hide"},
                {"name": "Femme Fatale", "type": "neutral", "mood": "seductive", "description": "A mysterious woman with hidden motives"},
                {"name": "Criminal", "type": "enemy", "mood": "dangerous", "description": "A hardened lawbreaker watching your every move"}
            ]
        elif "western" in theme.lower() or "cowboy" in theme.lower():
            possible_characters = [
                {"name": "Sheriff", "type": "neutral", "mood": "stern", "description": "The law in these parts, wearing a silver star"},
                {"name": "Outlaw", "type": "enemy", "mood": "dangerous", "description": "A rough-looking gunslinger with a bounty on their head"},
                {"name": "Bartender", "type": "neutral", "mood": "friendly", "description": "A keeper of secrets and server of drinks"},
                {"name": "Native Scout", "type": "ally", "mood": "watchful", "description": "A skilled tracker familiar with the territory"},
                {"name": "Gambler", "type": "neutral", "mood": "calculating", "description": "A well-dressed card player with a poker face"},
                {"name": "Rancher", "type": "ally", "mood": "straightforward", "description": "A hardworking landowner with local influence"}
            ]
        else:
            # Generic characters for any theme
            possible_characters = [
                {"name": "Guardian", "type": "ally", "mood": "protective", "description": "A watchful protector"},
                {"name": "Sage", "type": "ally", "mood": "wise", "description": "A source of ancient knowledge"},
                {"name": "Adversary", "type": "enemy", "mood": "threatening", "description": "Someone who stands in your way"},
                {"name": "Guide", "type": "ally", "mood": "helpful", "description": "A knowledgeable local"},
                {"name": "Trickster", "type": "neutral", "mood": "mischievous", "description": "A cunning individual with unclear motives"},
                {"name": "Innocent", "type": "neutral", "mood": "frightened", "description": "Someone caught in events beyond their control"}
            ]

        # Add character specifics based on story text
        for word in ["guard", "soldier", "warrior", "fighter"]:
            if word in story_text:
                possible_characters.append({
                    "name": "Guard", 
                    "type": "neutral" if "friendly" in story_text else "enemy", 
                    "mood": "alert", 
                    "description": "An armored sentinel watching for trouble"
                })
                break

        for word in ["king", "queen", "prince", "princess", "ruler", "lord", "noble"]:
            if word in story_text:
                possible_characters.append({
                    "name": "Noble", 
                    "type": "neutral", 
                    "mood": "commanding", 
                    "description": "A person of high status and authority"
                })
                break

        for word in ["monster", "beast", "creature", "abomination"]:
            if word in story_text:
                possible_characters.append({
                    "name": "Monster", 
                    "type": "enemy", 
                    "mood": "hostile", 
                    "description": "A frightening creature with ill intent"
                })
                break

        for word in ["merchant", "trader", "vendor", "shopkeeper"]:
            if word in story_text:
                possible_characters.append({
                    "name": "Merchant", 
                    "type": "neutral", 
                    "mood": "businesslike", 
                    "description": "A seller of goods and information"
                })
                break

        # Select characters to include in this node based on story context
        characters_to_include = []

        # Always include specific character types if mentioned
        if has_enemy:
            enemies = [c for c in possible_characters if c["type"] == "enemy"]
            if enemies:
                characters_to_include.append(enemies[hash(node_id) % len(enemies)])

        if has_ally:
            allies = [c for c in possible_characters if c["type"] == "ally"]
            if allies:
                characters_to_include.append(allies[hash(node_id + "ally") % len(allies)])

        if has_neutral:
            neutrals = [c for c in possible_characters if c["type"] == "neutral"]
            if neutrals:
                characters_to_include.append(neutrals[hash(node_id + "neutral") % len(neutrals)])

        # If we still need more characters, add some based on node depth
        if len(characters_to_include) < min(node_depth + 1, 3):
            remaining = [c for c in possible_characters if c not in characters_to_include]
            if remaining:
                # Add up to 2 more characters for deeper nodes
                additional_count = min(min(node_depth + 1, 3) - len(characters_to_include), 2)
                for i in range(additional_count):
                    if remaining:
                        char_idx = hash(f"{node_id}_{i}") % len(remaining)
                        characters_to_include.append(remaining[char_idx])
                        remaining.pop(char_idx)

        # Add the selected characters to the node
        for character in characters_to_include:
            char_name = character["name"]
            
            # Add some variety with adjectives based on theme
            if hash(f"{node_id}_{char_name}") % 5 == 0:  # 20% chance to add adjective
                adjectives = {
                    "enemy": ["Menacing", "Dangerous", "Hostile", "Threatening", "Sinister"],
                    "ally": ["Loyal", "Trustworthy", "Dependable", "Helpful", "Brave"],
                    "neutral": ["Mysterious", "Cautious", "Reserved", "Curious", "Watchful"]
                }
                adj_list = adjectives[character["type"]]
                adj = adj_list[hash(f"{node_id}_{char_name}_adj") % len(adj_list)]
                char_name = f"{adj} {char_name}"
            
            # Add the character
            node_data["characters"][char_name] = {
                "health": 100 - (20 if character["type"] == "enemy" else 0),  # Enemies sometimes injured
                "mood": character["mood"],
                "status_effects": [],
                "description": character["description"],
                "type": character["type"],
                "relationships": {
                    "player": "hostile" if character["type"] == "enemy" else 
                             "friendly" if character["type"] == "ally" else "neutral"
                }
            }
        
        # Add potential status changes based on node type and content
        node_depth = len(node_id.split('_')) - 1
        story_text = node_data["story"].lower()

        # Determine if this choice involves risks or rewards
        is_risky = any(word in story_text for word in ["danger", "fight", "attack", "threat", "battle", "defend", "risk"])
        is_reward = any(word in story_text for word in ["treasure", "reward", "discover", "find", "chest", "prize", "valuable"])
        is_learning = any(word in story_text for word in ["learn", "knowledge", "understand", "wisdom", "skill", "master"])

        # Define potential outcomes based on choice content (more depth = more extreme outcomes)
        node_data["outcome"] = {
            "health_change": 0,
            "experience_change": 0,
            "inventory_changes": []
        }

        # Health changes - can lose or gain health based on choice
        if is_risky:
            # More depth = higher risk
            risk_factor = min(10 + (node_depth * 5), 30)  # Max 30% health loss
            node_data["outcome"]["health_change"] = -risk_factor
        elif "heal" in story_text or "rest" in story_text or "recover" in story_text:
            # Health recovery options
            heal_amount = min(10 + (node_depth * 3), 25)  # Max 25% health gain
            node_data["outcome"]["health_change"] = heal_amount

        # Experience changes - gain experience from various activities
        if is_learning:
            # Direct learning provides most experience
            exp_gain = 5 + (node_depth * 3)
            node_data["outcome"]["experience_change"] = exp_gain
        elif is_risky or is_reward:
            # Taking risks or finding rewards also gives experience
            exp_gain = 3 + (node_depth * 2)
            node_data["outcome"]["experience_change"] = exp_gain
        else:
            # Some minimal experience for any choice
            node_data["outcome"]["experience_change"] = 1 + node_depth

        # Inventory changes
        if "find" in story_text or "discover" in story_text or "obtain" in story_text or "take" in story_text:
            # Potential item additions based on theme and story content
            possible_items = []
            
            if "sword" in story_text or "blade" in story_text or "weapon" in story_text:
                possible_items = ["Ancient Sword", "Mysterious Blade", "Enchanted Dagger"]
            elif "potion" in story_text or "elixir" in story_text or "vial" in story_text:
                possible_items = ["Healing Potion", "Strength Elixir", "Magic Vial"]
            elif "key" in story_text or "lockpick" in story_text:
                possible_items = ["Rusty Key", "Golden Key", "Master Lockpick"]
            elif "map" in story_text or "scroll" in story_text or "book" in story_text:
                possible_items = ["Ancient Map", "Mysterious Scroll", "Forgotten Tome"]
            elif "gem" in story_text or "crystal" in story_text or "jewel" in story_text:
                possible_items = ["Glowing Crystal", "Precious Gem", "Magical Jewel"]
            elif "food" in story_text or "ration" in story_text or "fruit" in story_text:
                possible_items = ["Rations", "Exotic Fruit", "Magical Herb"]
            elif "tech" in story_text or "device" in story_text or "gadget" in story_text:
                possible_items = ["Strange Device", "Alien Tech", "Advanced Gadget"]
            
            # Theme-specific items as fallback
            if not possible_items:
                if "star wars" in theme.lower() or "space" in theme.lower() or "sci-fi" in theme.lower():
                    possible_items = ["Blaster", "Datapad", "Shield Generator", "Medpac", "Droid Part"]
                elif "fantasy" in theme.lower() or "medieval" in theme.lower() or "magic" in theme.lower():
                    possible_items = ["Magic Scroll", "Healing Herbs", "Silver Coin", "Enchanted Ring", "Old Map"]
                elif "cyberpunk" in theme.lower() or "future" in theme.lower() or "tech" in theme.lower():
                    possible_items = ["Neural Chip", "Hacking Tool", "Cybernetic Implant", "Stealth Module", "VR Interface"]
                elif "horror" in theme.lower() or "scary" in theme.lower() or "spooky" in theme.lower():
                    possible_items = ["Strange Amulet", "Mysterious Note", "Rusty Key", "Old Photograph", "Ritual Component"]
                else:
                    # Generic useful items
                    possible_items = ["Useful Tool", "Mysterious Artifact", "Valuable Trinket", "Hidden Message", "Special Component"]
            
            # Add an item to the inventory changes if the depth is right and we have possible items
            if node_depth > 0 and possible_items and (is_reward or (hash(node_id) % 3 == 0)):
                item = possible_items[hash(node_id) % len(possible_items)]
                node_data["outcome"]["inventory_changes"].append({"add": item})
    
    # Create the full save data structure
    save_data = {
        "story_state": {
            "characters": {
                "player": {
                    "health": 100,
                    "experience": 10,
                    "mood": "determined",
                    "status_effects": [],
                    "inventory": []
                }
            },
            "current_scene": {},
            "inventory": [],
            "visited_nodes": ["node_0"],
            "theme": theme,
            "max_depth": depth
        },
        "graph": story_graph
    }
    
    # Save to a file
    filename = f"{theme.lower().replace(' ', '_')}_story.json"
    with open(filename, 'w') as f:
        json.dump(save_data, f, indent=2)
        
    print(f"Story tree saved to {filename}")
    return filename

if __name__ == "__main__":
    print("Welcome to the Predetermined Story Generator!")
    print("=" * 50)
    
    theme = input("\nWhat kind of story would you like to generate?\n(e.g., Star Wars, Lord of the Rings, Dracula, Cyberpunk): ")
    return_story_tree(theme)