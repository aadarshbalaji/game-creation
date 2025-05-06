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
        # Add placeholder scene state
        node_data["scene_state"] = {
            "location": "unknown",
            "time_of_day": "day",
            "weather": "clear",
            "ambient": "mysterious"
        }
        
        # Add placeholder character data
        node_data["characters"] = {
            "player": {
                "health": 100,
                "mood": "determined",
                "status_effects": []
            }
        }
    
    # Create the full save data structure
    save_data = {
        "story_state": {
            "characters": {},
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