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
    Be sure to keep the characters/names the same as in the original theme.
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
        else:
            # Mark as ending
            story_graph["nodes"][current_id]["is_end"] = True
            
            # Add potential ending outcome
            if hash(current_id) % 3 == 0:
                story_graph["nodes"][current_id]["outcome"] = {
                    "health_change": -20,  # Bad ending: lose health
                    "experience_change": 10,
                    "inventory_changes": []
                }
            elif hash(current_id) % 3 == 1:
                story_graph["nodes"][current_id]["outcome"] = {
                    "health_change": 20,  # Good ending: gain health and a special item
                    "experience_change": 30,
                    "inventory_changes": [{"add": f"Special {theme} artifact"}]
                }
            else:
                story_graph["nodes"][current_id]["outcome"] = {
                    "health_change": 0,  # Neutral ending
                    "experience_change": 20,
                    "inventory_changes": []
                }
    
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
    """Generate a full story tree based on the given theme, with proper graph structure"""
    
    # Generate the story arc
    story_arc = return_story_arc(theme)
    
    # Generate the story tree
    story_graph = {"nodes": {}, "edges": []}
    
    # Define a StoryState to track global game state
    story_state = StoryState()
    story_state.theme = theme
    
    # Process the root node (introduction)
    root_data = generate_story_node(f"""
    Create an introduction for an interactive narrative game set in the world of {theme}.Be sure to keep the characters/names the same as in the original theme.
    You should be sticking to the story arc provided as much as possible, but feel free to deviate if you must:
    Here is the story arc:
    {story_arc}
    This should be the introduction to our story, establishing the setting, main character, and initial situation.
    
    Just provide a single JSON object containing:
    {{
        "story": "rich descriptive text for the introduction scene",
        "choices": [
            {{"text": "action player takes 1", "consequences": "immediate result"}},
            {{"text": "action player takes 2", "consequences": "immediate result"}}
        ]
    }}
    """, is_root=True)
    
    if not root_data:
        root_data = {
            "story": f"You begin your adventure in the world of {theme}. The path ahead is uncertain, but destiny awaits.",
            "choices": [
                {"text": "Explore the immediate area carefully, looking for clues.", "consequences": "You discover signs of recent activity."},
                {"text": "Move forward quickly, eager to begin your journey.", "consequences": "You press onward, leaving the safety of familiar surroundings."}
            ]
        }
    
    # Create story graph structure
    queue = []
    visited = set()
    
    # Create root node
    root_id = "node_0"
    root_story = root_data.get("story", f"You begin your {theme} adventure!")
    root_choices = root_data.get("choices", [])
    
    # Make sure we have exactly choices_per_node choices for root
    while len(root_choices) < choices_per_node:
        # Add generic choices to fill up to requested number
        idx = len(root_choices)
        choices = [
            {"text": "Explore the surrounding area carefully, searching for anything useful.", "consequences": "You find signs of recent activity."},
            {"text": "Proceed cautiously, keeping alert for any danger.", "consequences": "You move forward with careful steps."},
            {"text": "Take a moment to gather your thoughts and plan your next move.", "consequences": "You consider your options carefully."},
            {"text": "Look for any hidden paths or secret areas nearby.", "consequences": "You search for less obvious routes."}
        ]
        root_choices.append(choices[idx % len(choices)])
    
    # Trim to exactly choices_per_node
    root_choices = root_choices[:choices_per_node]
    
    # Add root node to story graph
    story_graph["nodes"][root_id] = {
        "story": root_story,
        "is_end": False,
        "dialogue": ""
    }
    
    # Process root node - add scene state, characters, etc.
    enrich_story_node(story_graph["nodes"][root_id], root_id, theme)
    
    # Add root node's children to the queue
    for i, choice in enumerate(root_choices):
        child_id = f"{root_id}_{i+1}"
        child_story = choice.get("text", "You continue your journey.")
        child_consequence = choice.get("consequences", "")
        
        # Add edge connecting root to this child
        story_graph["edges"].append({
            "from": root_id,
            "to": child_id,
            "action": child_story
        })
        
        # Create child node with basic info
        story_graph["nodes"][child_id] = {
            "story": child_story,
            "is_end": False,
            "dialogue": child_consequence
        }
        
        # Add child to queue for further processing
        queue.append((child_id, 1))  # (node_id, depth)
    
    # Track visited nodes
    visited.add(root_id)
    
    # BFS to generate the rest of the tree
    while queue and len(visited) < 150: # Increased safety limit slightly
        node_id, current_depth = queue.pop(0)

        # Skip if we've visited this node (check visited size for safety limit)
        if node_id in visited:
            continue

        # Mark as visited
        visited.add(node_id)

        # Get current node data
        current_node = story_graph["nodes"][node_id]

        # Enrich the node if needed (e.g., add scene state, characters)
        if "scene_state" not in current_node:
            enrich_story_node(current_node, node_id, theme)

        # Determine narrative stage based on depth
        stage_threshold_1 = depth / 3
        stage_threshold_2 = 2 * depth / 3
        narrative_stage = ""
        if current_depth < stage_threshold_1:
            narrative_stage = "Introduction"
        elif current_depth < stage_threshold_2:
            narrative_stage = "Middle"
        else: # current_depth >= stage_threshold_2
            narrative_stage = "Conclusion"
        print(f"Processing node {node_id} (Depth {current_depth}/{depth}, Stage: {narrative_stage})")

        # Check if this node's children will be the final endings
        is_final_choice_layer = (current_depth == depth - 1)

        if not is_final_choice_layer:
            # --- Generate Normal Child Nodes with Choices ---
            child_prompt = f"""
            This is the '{narrative_stage}' phase of a {theme} interactive story.
            Overall Story Arc Guidance: {story_arc}
            Current situation: {current_node['story']}

            Generate {choices_per_node} distinct, action-oriented choices for the player, appropriate for the '{narrative_stage}' stage.
            Each choice must start with a verb and describe what the player DOES.

            Return a valid JSON object:
            {{
                "choices": [
                    {{
                        "text": "Player action 1 (verb first, fits '{narrative_stage}')",
                        "consequences": "Immediate result (fits '{narrative_stage}')"
                    }},
                    ... {choices_per_node - 1} more choices ...
                ]
            }}
            """
            child_data = generate_story_node(child_prompt)

            # Default options if generation fails
            if not child_data or "choices" not in child_data:
                child_data = {
                    "choices": [
                        {"text": f"Action {i+1}: Explore the {narrative_stage.lower()} stage options.", "consequences": f"You proceed during the {narrative_stage.lower()} phase."}
                        for i in range(choices_per_node)
                    ]
                }

            # Ensure correct number of choices
            choices = child_data.get("choices", [])
            while len(choices) < choices_per_node:
                idx = len(choices)
                default_choices = [
                    {"text": f"Investigate further during the {narrative_stage}.", "consequences": "You delve deeper."},
                    {"text": f"Confront the challenge of the {narrative_stage}.", "consequences": "You face the situation."},
                    {"text": f"Seek allies during the {narrative_stage}.", "consequences": "You look for help."},
                    {"text": f"Analyze the {narrative_stage} situation.", "consequences": "You assess your options."}
                ]
                choices.append(default_choices[idx % len(default_choices)])
            choices = choices[:choices_per_node]

            # Create child nodes and add them to the graph/queue
            for i, choice in enumerate(choices):
                child_id = f"{node_id}_{i+1}"
                child_story = choice.get("text", f"Continue ({narrative_stage})")
                child_consequence = choice.get("consequences", "")

                # Add edge
                story_graph["edges"].append({
                    "from": node_id,
                    "to": child_id,
                    "action": child_story
                })

                # Create child node
                story_graph["nodes"][child_id] = {
                    "story": child_story, # Story here is the ACTION taken
                    "is_end": False,      # Will be marked True later if it's the final depth
                    "dialogue": child_consequence
                }
                enrich_story_node(story_graph["nodes"][child_id], child_id, theme) # Enrich new node

                # Add to queue if not exceeding depth
                if current_depth + 1 < depth:
                    queue.append((child_id, current_depth + 1))
                else:
                     # This child node IS the ending because it's at max depth
                     story_graph["nodes"][child_id]["is_end"] = True
                     # Optionally generate a concluding story *for this node* instead of using action text
                     # For now, we'll handle specific ending text generation in the 'else' block below
                     story_graph["nodes"][child_id]["outcome"] = generate_ending_outcome(child_id, theme)


        else: # current_depth == depth - 1: Generate Endings, not Choices
            # --- Generate Ending Nodes ---
            ending_prompt = f"""
            This branch of the {theme} story ({narrative_stage} stage) is reaching its conclusion.
            Overall Story Arc Guidance: {story_arc}
            Current situation leading to the end: {current_node['story']}

            Generate {choices_per_node} distinct narrative endings for this path. Each ending should be a short concluding paragraph (2-4 sentences).

            Return a valid JSON object:
            {{
                "endings": [
                    {{"text": "Narrative conclusion for ending 1."}},
                    {{"text": "Narrative conclusion for ending 2."}},
                    ... up to {choices_per_node} endings ...
                ]
            }}
            """
            ending_data = generate_story_node(ending_prompt)

            # Default endings if generation fails
            if not ending_data or "endings" not in ending_data:
                ending_data = {"endings": [{"text": f"Conclusion {i+1}: The journey ends here, shaped by your choices during the {narrative_stage}."} for i in range(choices_per_node)]}

            endings = ending_data.get("endings", [])
            # Ensure correct number of endings
            while len(endings) < choices_per_node:
                 endings.append({"text": f"Conclusion {len(endings)+1}: An alternate end to the {theme} tale."})
            endings = endings[:choices_per_node]

            # Create child nodes which ARE the endings
            for i, ending in enumerate(endings):
                child_id = f"{node_id}_{i+1}"
                # The story IS the ending text
                child_story = ending.get("text", "The adventure concludes.")

                # Add edge representing the choice leading TO this specific end
                story_graph["edges"].append({
                    "from": node_id,
                    "to": child_id,
                    "action": f"Pursue Ending Path {i+1}" # The action is choosing this ending branch
                })

                # Create the final ending node
                story_graph["nodes"][child_id] = {
                    "story": child_story, # Story is the conclusion text
                    "is_end": True,       # This node IS an end
                    "dialogue": "",       # Endings don't usually have consequence dialogue
                    "outcome": generate_ending_outcome(child_id, theme) # Add outcome stats
                }
                enrich_story_node(story_graph["nodes"][child_id], child_id, theme) # Add final scene state etc.
                visited.add(child_id) # Mark ending node as visited, won't be processed further

    # Final pass to ensure all nodes at max depth are marked as end nodes
    # (This acts as a safeguard)
    for node_id, node_data in story_graph["nodes"].items():
        node_depth_check = len(node_id.split('_')) - 1 # Recalculate depth from ID
        if node_depth_check >= depth:
            if not node_data.get("is_end", False):
                 print(f"Safeguard: Marking node {node_id} at depth {node_depth_check} as ending.")
                 node_data["is_end"] = True
                 if "outcome" not in node_data: # Add outcome if missing
                      node_data["outcome"] = generate_ending_outcome(node_id, theme)

    # Ensure all nodes have characters and scene state (might be redundant but safe)
    for node_id, node_data in story_graph["nodes"].items():
        # Generate scene state if missing
        if "scene_state" not in node_data:
            enrich_story_node(node_data, node_id, theme)
        # Generate dialogue if appropriate (avoid for endings?)
        if not node_data.get("is_end", False) and not node_data.get("dialogue"):
             dialogue = generate_scene_dialogue(node_data, theme)
             if dialogue:
                 node_data["dialogue"] = dialogue

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

def generate_scene_dialogue(node_data, theme):
    """Generate dialogue between player and characters in the scene that's highly specific to the current context"""
    story_text = node_data["story"].lower()
    characters = node_data.get("characters", {})
    
    # Filter out any non-dictionary character entries
    valid_characters = {name: data for name, data in characters.items() 
                       if isinstance(data, dict)}
    
    # Only generate dialogue if there are other characters
    other_characters = [name for name in valid_characters if name.lower() != "player"]
    if not other_characters:
        return ""
    
    # Extract key elements from the story text to make dialogue more relevant
    location = node_data.get("scene_state", {}).get("location", "this place")
    
    # Extract key nouns and concepts from the story
    nouns = []
    important_objects = ["sword", "key", "door", "map", "artifact", "treasure", "weapon", "book", 
                        "device", "machine", "creature", "monster", "ship", "vehicle", "potion", 
                        "scroll", "computer", "terminal", "gold", "jewel", "crystal", "orb"]
    
    for word in story_text.split():
        # Remove punctuation
        clean_word = word.strip(".,!?;:()'\"")
        if clean_word in important_objects:
            nouns.append(clean_word)
    
    # Use only the most relevant single object
    key_object = nouns[0] if nouns else None
    
    # Extract primary action/activity in the scene
    actions = []
    action_verbs = {
        "searching": ["search", "look", "seek", "hunt", "explore"],
        "fighting": ["fight", "battle", "combat", "attack", "defend", "struggle"],
        "escaping": ["escape", "flee", "run", "evade", "avoid"],
        "investigating": ["investigate", "examine", "inspect", "study", "analyze"],
        "meeting": ["meet", "encounter", "find", "discover"],
        "travelling": ["travel", "journey", "trek", "voyage", "expedition"],
        "hiding": ["hide", "conceal", "stealth", "sneak"],
        "negotiating": ["negotiate", "bargain", "deal", "trade", "barter"]
    }
    
    for action_type, verbs in action_verbs.items():
        if any(verb in story_text for verb in verbs):
            actions.append(action_type)
    
    # Get primary action
    primary_action = actions[0] if actions else "exploring"
    
    # Select just ONE character for dialogue - makes conversations more focused
    # Prioritize characters that match the primary action context
    potential_speakers = []
    
    if primary_action == "fighting":
        # Prefer enemies for fighting scenes
        enemies = [name for name, data in valid_characters.items() 
                  if name.lower() != "player" and data.get("type") == "enemy"]
        if enemies:
            potential_speakers = enemies
    elif primary_action in ["negotiating", "meeting"]:
        # Prefer neutrals for negotiation scenes
        neutrals = [name for name, data in valid_characters.items() 
                   if name.lower() != "player" and data.get("type") == "neutral"]
        if neutrals:
            potential_speakers = neutrals
    elif primary_action in ["investigating", "searching", "travelling"]:
        # Prefer allies for cooperative actions
        allies = [name for name, data in valid_characters.items() 
                 if name.lower() != "player" and data.get("type") == "ally"]
        if allies:
            potential_speakers = allies
    
    # If nothing matched, use any available character
    if not potential_speakers:
        potential_speakers = other_characters
    
    # Select just one character for more focused dialogue
    char_name = potential_speakers[0]
    char_data = valid_characters[char_name]
    char_type = char_data.get("type", "neutral")
    char_mood = char_data.get("mood", "neutral")
    char_desc = char_data.get("description", "")
    
    # Generate dialogue based on scene context
    dialogue_lines = []
    
    # Create dialogue that specifically references scene elements
    if primary_action == "searching" or primary_action == "investigating":
        if key_object:
            player_opener = f"I'm looking for {key_object}. Have you seen anything like that around here?"
        else:
            player_opener = f"What can you tell me about {location}? I'm trying to find something important."
            
        if char_type == "ally":
            response = f"I've been in {location} for a while now. The {node_data['scene_state'].get('ambient')} atmosphere makes it difficult to search properly, but I'll help you look."
        elif char_type == "enemy":
            response = f"You think I'd tell you where to find anything valuable in {location}? You're even more foolish than you look."
        else:
            response = f"Many come to {location} searching. Few find what they're looking for, especially in this {node_data['scene_state'].get('weather')} weather."
        
        player_followup = "I appreciate any information you can share. Time is running short."
        
    elif primary_action == "fighting":
        player_opener = "Before this gets violent, is there anything you can tell me that might change my mind?"
        
        if char_type == "enemy":
            response = f"Words won't save you now. This {location} will become your tomb."
        elif char_type == "ally":
            response = f"Stay close! These enemies know {location} better than we do. Watch for movement in the {node_data['scene_state'].get('ambient')} shadows."
        else:
            response = f"I'm staying out of this conflict. Fighting in {location} during {node_data['scene_state'].get('time_of_day')} is a fool's errand."
        
        player_followup = "Then I'll do what I must."
    
    elif primary_action == "escaping":
        player_opener = f"What's the quickest way out of {location}? We need to move fast."
        
        if char_type == "ally":
            response = f"Follow me! I know a hidden path through {location}. We need to hurry before the {node_data['scene_state'].get('weather')} worsens."
        elif char_type == "enemy":
            response = f"There's no escape from {location}. The exits are all watched, and my associates are waiting."
        else:
            response = f"I've survived in {location} by knowing when to leave. Head toward the {node_data['scene_state'].get('ambient')} section and don't look back."
        
        player_followup = "Let's not waste any more time then."
    
    elif primary_action == "negotiating":
        if key_object:
            player_opener = f"I'm interested in acquiring {key_object}. What would you want in exchange?"
        else:
            player_opener = f"I think we can help each other. What are your terms?"
        
        if char_type == "neutral":
            response = f"My knowledge of {location} is valuable, especially during {node_data['scene_state'].get('time_of_day')}. Make it worth my while, and we have a deal."
        elif char_type == "enemy":
            response = f"You have nothing I want except your interference in {location} to end. Leave now, that's my only offer."
        else:
            response = f"No need for payment between allies. What we find in {location}, we share. That's how we survive the {node_data['scene_state'].get('weather')}."
        
        player_followup = "I can work with those terms. Let's proceed."
    
    else:  # Default/exploration dialogue
        # Extract unique scene elements to make default dialogue more specific
        unique_feature = ""
        if "ancient" in story_text:
            unique_feature = "ancient ruins"
        elif "dark" in story_text:
            unique_feature = "darkness"
        elif "light" in story_text:
            unique_feature = "strange light"
        elif "sound" in story_text or "noise" in story_text:
            unique_feature = "unusual sounds"
        else:
            # Use ambient or weather as fallback
            unique_feature = node_data['scene_state'].get('ambient') or node_data['scene_state'].get('weather')
        
        player_opener = f"What can you tell me about the {unique_feature} in {location}? It seems unusual."
        
        if char_type == "ally":
            response = f"I've been tracking it for days. The {unique_feature} appeared when the {node_data['scene_state'].get('time_of_day')} first changed so abruptly."
        elif char_type == "enemy":
            response = f"You ask too many questions. The {unique_feature} is none of your concern. Leave {location} while you still can."
        else:
            response = f"The {unique_feature} has been here since before my time. Some say it's a sign of what's coming to {location}. I just avoid it when the {node_data['scene_state'].get('weather')} gets bad."
        
        player_followup = "Interesting. I'll keep that in mind as I continue."
    
    # Build the final dialogue
    dialogue_lines.append(f"[You]: {player_opener}")
    dialogue_lines.append(f"[{char_name}]: {response}")
    dialogue_lines.append(f"[You]: {player_followup}")
    
    # Format the final dialogue
    return "\n".join(dialogue_lines)

def generate_special_ability(theme, experience_level, existing_abilities=None):
    """Generate a special ability for the player based on theme and progress"""
    if existing_abilities is None:
        existing_abilities = []
    
    # Define ability tiers based on experience level
    tier = 1
    if experience_level >= 100:
        tier = 4  # Master abilities
    elif experience_level >= 60:
        tier = 3  # Advanced abilities
    elif experience_level >= 30:
        tier = 2  # Intermediate abilities
    
    # Define thematic abilities
    theme_abilities = {
        "star wars": {
            1: [
                {"name": "Force Sense", "description": "Detect hidden objects or dangers nearby", "effect": "detection"},
                {"name": "Basic Blaster Training", "description": "Improved accuracy with ranged weapons", "effect": "combat"}
            ],
            2: [
                {"name": "Force Push", "description": "Push enemies away or move objects", "effect": "manipulation"},
                {"name": "Pilot Training", "description": "Better control in vehicle encounters", "effect": "skill"}
            ],
            3: [
                {"name": "Jedi Mind Trick", "description": "Influence weak-minded characters", "effect": "persuasion"},
                {"name": "Saber Deflection", "description": "Deflect blaster shots", "effect": "defense"}
            ],
            4: [
                {"name": "Force Mastery", "description": "Powerful control over the Force", "effect": "special"},
                {"name": "One with the Force", "description": "Connect deeply with the Force to reveal paths", "effect": "insight"}
            ]
        },
        "fantasy": {
            1: [
                {"name": "Minor Healing", "description": "Heal small wounds", "effect": "healing"},
                {"name": "Detect Magic", "description": "Sense magical auras and enchantments", "effect": "detection"}
            ],
            2: [
                {"name": "Elemental Touch", "description": "Imbue attacks with elemental power", "effect": "combat"},
                {"name": "Beast Speech", "description": "Communicate with animals", "effect": "communication"}
            ],
            3: [
                {"name": "Arcane Shield", "description": "Create a magical barrier against harm", "effect": "defense"},
                {"name": "Enchant Weapon", "description": "Temporarily enhance weapons or tools", "effect": "enhancement"}
            ],
            4: [
                {"name": "Mystical Transformation", "description": "Briefly transform into a powerful creature", "effect": "transformation"},
                {"name": "Ancient Words", "description": "Speak words of power with dramatic effects", "effect": "control"}
            ]
        },
        "cyberpunk": {
            1: [
                {"name": "Neural Interface", "description": "Basic connection to electronic systems", "effect": "tech"},
                {"name": "Reflex Booster", "description": "Slightly enhanced reaction time", "effect": "speed"}
            ],
            2: [
                {"name": "Subdermal Armor", "description": "Damage resistance from implanted armor", "effect": "defense"},
                {"name": "Enhanced Vision", "description": "See in darkness or analyze structures", "effect": "perception"}
            ],
            3: [
                {"name": "System Infiltrator", "description": "Bypass security systems more easily", "effect": "hacking"},
                {"name": "Nano-Healing", "description": "Nanobots repair damage to your body", "effect": "healing"}
            ],
            4: [
                {"name": "Full Conversion", "description": "Major cybernetic enhancements to all systems", "effect": "enhancement"},
                {"name": "Ghost Protocol", "description": "Temporarily become invisible to tech and cameras", "effect": "stealth"}
            ]
        },
        "horror": {
            1: [
                {"name": "Sixth Sense", "description": "Brief warnings before danger", "effect": "warning"},
                {"name": "Steady Nerves", "description": "Resist fear effects", "effect": "resistance"}
            ],
            2: [
                {"name": "Dark Sight", "description": "See clearly in darkness", "effect": "perception"},
                {"name": "Blood Memory", "description": "Extract memories from blood traces", "effect": "insight"}
            ],
            3: [
                {"name": "Warding Sign", "description": "Create temporary protective barriers", "effect": "protection"},
                {"name": "Voice of the Dead", "description": "Briefly communicate with the deceased", "effect": "communication"}
            ],
            4: [
                {"name": "Eldritch Pact", "description": "Call upon otherworldly power at great cost", "effect": "power"},
                {"name": "Reality Anchor", "description": "Stabilize reality against supernatural warping", "effect": "control"}
            ]
        },
        "detective": {
            1: [
                {"name": "Keen Eye", "description": "Notice small details others miss", "effect": "observation"},
                {"name": "Street Contacts", "description": "Access to information from the streets", "effect": "information"}
            ],
            2: [
                {"name": "Deductive Reasoning", "description": "Connect clues more effectively", "effect": "deduction"},
                {"name": "Disguise Artist", "description": "Blend in and assume different identities", "effect": "stealth"}
            ],
            3: [
                {"name": "Interrogation Expert", "description": "Extract information more effectively", "effect": "persuasion"},
                {"name": "Photographic Memory", "description": "Remember details with perfect clarity", "effect": "memory"}
            ],
            4: [
                {"name": "Master Sleuth", "description": "Solve even the most complex mysteries", "effect": "insight"},
                {"name": "Criminal Psychology", "description": "Predict actions of suspects with uncanny accuracy", "effect": "prediction"}
            ]
        },
        "western": {
            1: [
                {"name": "Quick Draw", "description": "Fast reactions in combat situations", "effect": "speed"},
                {"name": "Wilderness Survival", "description": "Navigate and survive harsh conditions", "effect": "survival"}
            ],
            2: [
                {"name": "Dead Eye", "description": "Improved accuracy with firearms", "effect": "precision"},
                {"name": "Horse Whisperer", "description": "Special bond with horses and other mounts", "effect": "animal"}
            ],
            3: [
                {"name": "Lawbringer", "description": "Impose order and command respect", "effect": "authority"},
                {"name": "Native Medicine", "description": "Healing techniques from indigenous knowledge", "effect": "healing"}
            ],
            4: [
                {"name": "Legend of the West", "description": "Your reputation precedes you, opening many doors", "effect": "reputation"},
                {"name": "True Grit", "description": "Continue fighting effectively even when badly wounded", "effect": "endurance"}
            ]
        }
    }
    
    # Generic abilities that work with any theme
    generic_abilities = {
        1: [
            {"name": "Quick Reflexes", "description": "React faster to sudden dangers", "effect": "speed"},
            {"name": "Keen Senses", "description": "Notice details others might miss", "effect": "perception"}
        ],
        2: [
            {"name": "Rapid Recovery", "description": "Heal faster from injuries", "effect": "healing"},
            {"name": "Weapon Expertise", "description": "Greater skill with weapons", "effect": "combat"}
        ],
        3: [
            {"name": "Iron Will", "description": "Resist mental influences and fear", "effect": "resistance"},
            {"name": "Strategic Mind", "description": "Better planning and tactical awareness", "effect": "strategy"}
        ],
        4: [
            {"name": "Hero's Resolve", "description": "Perform extraordinary feats when all seems lost", "effect": "special"},
            {"name": "Legendary Skill", "description": "Master of your chosen path", "effect": "mastery"}
        ]
    }
    
    # Determine which ability lists to use
    ability_lists = [generic_abilities]  # Always include generic abilities
    
    # Add theme-specific abilities if applicable
    for theme_key, abilities in theme_abilities.items():
        if theme_key in theme.lower():
            ability_lists.append(abilities)
            break
    
    # Collect all abilities at or below the current tier
    available_abilities = []
    for ability_list in ability_lists:
        for t in range(1, tier + 1):
            if t in ability_list:
                available_abilities.extend(ability_list[t])
    
    # Filter out abilities the player already has
    available_abilities = [ability for ability in available_abilities 
                          if ability["name"] not in existing_abilities]
    
    # If no new abilities available, return None
    if not available_abilities:
        return None
    
    # Select a random ability
    import random
    new_ability = random.choice(available_abilities)
    
    return new_ability

def enrich_story_node(node_data, node_id, theme):
    """Add scene state and characters to a story node"""
    # Extract information from the story text
    story_text = node_data["story"].lower()
    
    # Generate a scene state with location, time of day, weather, and ambient mood
    # Locations based on theme and story content
    location = "unknown"
    
    # Determine location based on theme and content
    if "castle" in story_text or "palace" in story_text or "fortress" in story_text:
        location = "Castle"
    elif "forest" in story_text or "woods" in story_text or "tree" in story_text:
        location = "Forest"
    elif "mountain" in story_text or "peak" in story_text or "cliff" in story_text:
        location = "Mountains"
    elif "ship" in story_text or "boat" in story_text or "sea" in story_text or "ocean" in story_text:
        location = "Ship"
    elif "cave" in story_text or "cavern" in story_text or "underground" in story_text:
        location = "Cave"
    elif "city" in story_text or "town" in story_text or "village" in story_text:
        location = "Settlement"
    elif "temple" in story_text or "shrine" in story_text or "altar" in story_text:
        location = "Temple"
    elif "desert" in story_text or "sand" in story_text or "dune" in story_text:
        location = "Desert"
    elif "jungle" in story_text or "tropical" in story_text:
        location = "Jungle"
    elif "lab" in story_text or "laboratory" in story_text or "facility" in story_text:
        location = "Laboratory"
    else:
        # If no specific location in text, use theme-based locations
        if "star wars" in theme.lower() or "sci-fi" in theme.lower() or "space" in theme.lower():
            locations = ["Starship Bridge", "Alien Planet", "Space Station", "Imperial Base", "Cantina"]
            location = locations[hash(node_id) % len(locations)]
        elif "fantasy" in theme.lower() or "medieval" in theme.lower() or "magic" in theme.lower():
            locations = ["Ancient Castle", "Enchanted Forest", "Wizard's Tower", "Dragon's Lair", "Dwarven Mines"]
            location = locations[hash(node_id) % len(locations)]
        elif "cyberpunk" in theme.lower() or "future" in theme.lower() or "tech" in theme.lower():
            locations = ["Neon District", "Corporate Tower", "Hacker's Den", "Black Market", "Virtual Reality"]
            location = locations[hash(node_id) % len(locations)]
        elif "horror" in theme.lower() or "scary" in theme.lower():
            locations = ["Abandoned Mansion", "Foggy Cemetery", "Dark Basement", "Cursed Village", "Forgotten Asylum"]
            location = locations[hash(node_id) % len(locations)]
        elif "western" in theme.lower() or "cowboy" in theme.lower():
            locations = ["Dusty Saloon", "Sheriff's Office", "Desert Canyon", "Train Station", "Gold Mine"]
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
                
    # Extract time of day and weather
    time_of_day = "day"
    weather = "clear"
    if "night" in story_text:
        time_of_day = "night"
    if "rain" in story_text or "storm" in story_text:
        weather = "rainy"
    elif "snow" in story_text:
        weather = "snowy"
    elif "wind" in story_text or "breeze" in story_text:
        weather = "windy"
    
    # Extract ambient mood
    ambient = "calm"
    if "dark" in story_text:
        ambient = "dark"
    elif "noisy" in story_text or "busy" in story_text:
        ambient = "busy"
    elif "quiet" in story_text:
        ambient = "quiet"
    
    # Add scene state to node data
    node_data["scene_state"] = {
        "location": location,
        "time_of_day": time_of_day,
        "weather": weather,
        "ambient": ambient
    }
    
    # Ensure we have a valid characters dictionary
    if "characters" not in node_data or not isinstance(node_data["characters"], dict):
        node_data["characters"] = {}
    
    # Clean up any invalid character entries
    characters = {name: data for name, data in node_data["characters"].items() 
                 if isinstance(data, dict)}
    
    # If there are no characters or only the player, add theme-appropriate characters
    if len(characters) <= 1 and (not characters or "player" in characters):
        # Generate additional characters based on theme and scene
        node_depth = len(node_id.split('_')) - 1
        
        # Check if the story mentions specific character types
        has_enemy = any(word in story_text for word in ["enemy", "villain", "foe", "opponent", "adversary", "antagonist"])
        has_ally = any(word in story_text for word in ["ally", "friend", "companion", "partner", "helper", "supporter"])
        has_neutral = any(word in story_text for word in ["stranger", "merchant", "traveler", "native", "inhabitant", "civilian"])
        
        # Add theme-appropriate characters
        if "star wars" in theme.lower() or "sci-fi" in theme.lower() or "space" in theme.lower():
            if has_enemy or hash(node_id) % 3 == 0:
                characters["Imperial Officer"] = {
                    "type": "enemy",
                    "mood": "hostile",
                    "description": "A stern officer in a gray uniform",
                    "health": 80
                }
            if has_ally or hash(node_id) % 3 == 1:
                characters["Rebel Scout"] = {
                    "type": "ally",
                    "mood": "cautious",
                    "description": "A dedicated fighter for the rebellion",
                    "health": 70
                }
            if has_neutral or hash(node_id) % 3 == 2:
                characters["Cantina Patron"] = {
                    "type": "neutral",
                    "mood": "indifferent",
                    "description": "A mysterious individual nursing a drink",
                    "health": 60
                }
        elif "fantasy" in theme.lower() or "medieval" in theme.lower() or "magic" in theme.lower():
            if has_enemy or hash(node_id) % 3 == 0:
                characters["Dark Sorcerer"] = {
                    "type": "enemy",
                    "mood": "menacing",
                    "description": "A robed figure with glowing eyes",
                    "health": 75
                }
            if has_ally or hash(node_id) % 3 == 1:
                characters["Elven Scout"] = {
                    "type": "ally",
                    "mood": "friendly",
                    "description": "A graceful elf with keen eyes",
                    "health": 65
                }
            if has_neutral or hash(node_id) % 3 == 2:
                characters["Village Elder"] = {
                    "type": "neutral",
                    "mood": "wise",
                    "description": "An aged local with vast knowledge",
                    "health": 40
                }
        elif "cyberpunk" in theme.lower():
            if has_enemy or hash(node_id) % 3 == 0:
                characters["Corporate Enforcer"] = {
                    "type": "enemy",
                    "mood": "threatening",
                    "description": "A heavily augmented security operative",
                    "health": 90
                }
            if has_ally or hash(node_id) % 3 == 1:
                characters["Rogue Netrunner"] = {
                    "type": "ally",
                    "mood": "paranoid",
                    "description": "A skilled hacker with chrome implants",
                    "health": 60
                }
            if has_neutral or hash(node_id) % 3 == 2:
                characters["Street Vendor"] = {
                    "type": "neutral",
                    "mood": "suspicious",
                    "description": "A local selling various wares",
                    "health": 50
                }
        # Add other theme-specific characters as needed
    
    # Update the node's characters
    node_data["characters"] = characters

def generate_ending_outcome(node_id, theme):
    """Generates a basic outcome dictionary for an ending node."""
    outcome_hash = hash(node_id)
    if outcome_hash % 4 == 0: # Bad ending
        return {"health_change": -30, "experience_change": 5, "inventory_changes": []}
    elif outcome_hash % 4 == 1: # Good ending
         return {"health_change": 25, "experience_change": 40, "inventory_changes": [{"add": f"Memento of the {theme} Conclusion"}]}
    elif outcome_hash % 4 == 2: # Neutral ending
         return {"health_change": 0, "experience_change": 20, "inventory_changes": []}
    else: # Mixed ending
         return {"health_change": -10, "experience_change": 25, "inventory_changes": [{"add": f"Scrap of {theme} Lore"}]}

if __name__ == "__main__":
    print("Welcome to the Predetermined Story Generator!")
    print("=" * 50)
    
    theme = input("\nWhat kind of story would you like to generate?\n(e.g., Star Wars, Lord of the Rings, Dracula, Cyberpunk): ")
    return_story_tree(theme)