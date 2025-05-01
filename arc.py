from google import genai
import json
import os
import time
import hashlib
from Graph_Classes.Structure import Node, Graph

GOOGLE_API_KEY = ""
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
    """Generate a general story arc structure for the given theme"""
    
    prompt = f"""
    Create a detailed story arc for an interactive narrative in the {theme} universe/setting.
    The story should follow the classic hero's journey structure with 8 distinct phases:
    
    1. The Ordinary World: Establish the protagonist and their normal life
    2. The Call to Adventure: Introduce the inciting incident
    3. Crossing the Threshold: Protagonist enters the world of adventure
    4. Tests, Allies, and Enemies: Protagonist faces challenges and meets key characters
    5. The Approach: Preparation for the major challenge
    6. The Ordeal: The main conflict or challenge
    7. The Reward: Protagonist achieves something valuable
    8. Return and Resolution: The conclusion and return to a new normal
    
    For each stage, provide:
    - A brief description of what happens
    - Main characters involved
    - Key plot points
    - Potential branching paths (different choices that could occur)
    - Thematic elements specific to {theme}
    
    Make all elements consistent with the {theme} setting and style.
    
    Return ONLY valid JSON in this exact format:
    {{
        "theme": "{theme}",
        "golden_path": "the ideal/optimal storyline that will serve as the golden path for the generated story in 5-8 sentences"
        "arc": [
            {{
                "stage": "The Ordinary World",
                "description": "detailed description of this stage",
                "characters": ["character1", "character2"],
                "key_plot_points": ["plot point 1", "plot point 2"],
                "potential_branches": ["decision point 1", "decision point 2"],
                "thematic_elements": ["element1", "element2"]
            }},
            ... (repeat for all 8 stages)
        ]
    }}
    """
    
    try:
        response = client.models.generate_content(
            contents=[prompt],
            model="gemini-2.0-flash",
        )
        
        raw_text = response.text.strip()
        
        # Clean up response to extract valid JSON
        if raw_text.startswith("```"):
            lines = raw_text.split('\n')
            if lines[0].startswith("```") and lines[-1].startswith("```"):
                raw_text = '\n'.join(lines[1:-1])
            elif lines[0].startswith("```"):
                raw_text = '\n'.join(lines[1:])
                
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        
        # Find JSON boundaries
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}') + 1
        if start_idx < 0 or end_idx <= 0:
            raise Exception("Invalid JSON format")
            
        json_text = raw_text[start_idx:end_idx]
        arc_data = json.loads(json_text)
        
        print(f"Successfully generated story arc for {theme}")
        return arc_data
        
    except Exception as e:
        print(f"Error generating story arc: {e}")
        raise

def generate_story_tree(arc_data, max_depth=8):
    """Generate a complete story tree based on the story arc"""
    
    # Initialize graph structure
    graph = Graph()
    story_state = StoryState()
    story_state.theme = arc_data["theme"]
    
    # Generate root node (level 0)
    root_prompt = f"""
    Create the opening scene for a {arc_data['theme']} adventure based on this story context:
    
    Stage: {arc_data['arc'][0]['stage']}
    Description: {arc_data['arc'][0]['description']}
    Characters: {', '.join(arc_data['arc'][0]['characters'])}
    Key Plot Points: {', '.join(arc_data['arc'][0]['key_plot_points'])}
    Thematic Elements: {', '.join(arc_data['arc'][0]['thematic_elements'])}
    
    Create a rich, detailed opening scene that:
    1. Introduces the protagonist
    2. Establishes the setting
    3. Hints at the coming adventure
    4. Sets the tone and atmosphere for {arc_data['theme']}
    
    Do not include choices. Focus on crafting a compelling introduction scene only.
    
    Return ONLY valid JSON in this format:
    {{
        "story": "detailed opening scene description",
        "scene_state": {{
            "location": "specific location",
            "time_of_day": "time period",
            "weather": "conditions",
            "ambient": "mood"
        }},
        "characters": {{
            "player": {{
                "health": 100,
                "mood": "initial state",
                "status_effects": []
            }},
            "others": [
                {{
                    "name": "character name",
                    "description": "brief description",
                    "relationship": "relationship to player"
                }}
            ]
        }}
    }}
    """
    
    try:
        response = client.models.generate_content(
            contents=[root_prompt],
            model="gemini-2.0-flash",
        )
        
        raw_text = clean_response(response.text)
        root_data = json.loads(raw_text)
        
        # Create the root node
        root_node = Node(root_data["story"])
        root_node.scene_state = root_data["scene_state"]
        root_node.characters = root_data["characters"]
        graph.add_node(root_node)
        
        # Track nodes by level and position for organized generation
        nodes_by_level = {0: {0: root_node}}
        
        # Generate all levels of the tree (depth 8, binary choices)
        for level in range(1, max_depth):
            nodes_by_level[level] = {}
            parent_level = level - 1
            
            # For each node in the previous level
            for parent_pos, parent_node in nodes_by_level[parent_level].items():
                # Calculate current stage in the story arc
                current_stage = min(level, 7)  # Stage index (0-7)
                
                # Generate two choices for this parent
                for choice_idx in range(2):
                    # Generate node content based on the current stage and previous choice
                    node_data = generate_story_node(
                        arc_data, 
                        current_stage,
                        parent_level,
                        choice_idx,
                        parent_node
                    )
                    
                    # Create choice node
                    child_node = Node(node_data["story"], node_data.get("is_ending", False))
                    child_node.scene_state = node_data["scene_state"]
                    child_node.characters = node_data["characters"]
                    
                    # Add consequences data
                    if "choices" in node_data and len(node_data["choices"]) > choice_idx:
                        child_node.consequences = node_data["choices"][choice_idx]["consequences"]
                    
                    # Allow backtracking for first choices
                    child_node.backtrack = (choice_idx == 0)
                    
                    # Add to graph
                    graph.add_node(child_node)
                    graph.add_edge(parent_node, child_node)
                    
                    # Store in level tracking dictionary
                    child_pos = parent_pos * 2 + choice_idx
                    nodes_by_level[level][child_pos] = child_node
                
                # Print progress
                progress = sum(len(nodes) for _, nodes in nodes_by_level.items()) / (2**8 - 1) * 100
                print(f"Progress: {progress:.1f}% complete - Generated level {level}")
            
            # Avoid rate limiting
            time.sleep(0.2)
    
        return graph, story_state
        
    except Exception as e:
        print(f"Error generating story tree: {e}")
        raise

def generate_story_node(arc_data, current_stage, parent_level, choice_variant, parent_node):
    """Generate a story node based on the current stage in the arc"""
    
    # Determine if this is a transition between major story stages
    stage_data = arc_data["arc"][current_stage]
    
    # Extract previous state information
    previous_location = parent_node.scene_state.get("location", "unknown")
    previous_characters = []
    if parent_node.characters.get("others"):
        previous_characters = [char.get("name") for char in parent_node.characters.get("others", [])]
    
    # Build a context-aware prompt
    context_description = f"""
    Previous scene: {parent_node.story}
    Previous location: {previous_location}
    Story stage: {stage_data['stage']}
    Stage description: {stage_data['description']}
    Characters in this stage: {', '.join(stage_data['characters'])}
    Key plot points: {', '.join(stage_data['key_plot_points'])}
    """
    
    # Add branch-specific context
    branch_choice = stage_data['potential_branches'][min(choice_variant, len(stage_data['potential_branches'])-1)]
    context_description += f"\nThe story follows this branch: {branch_choice}"
    
    # Generate the node content
    prompt = f"""
    Create the next scene in a {arc_data['theme']} story with these details:
    
    {context_description}
    
    This scene must:
    1. Advance the plot according to the current stage: {stage_data['stage']}
    2. Incorporate the thematic elements: {', '.join(stage_data['thematic_elements'])}
    3. Present exactly 2 meaningful choices that could lead to different outcomes
    4. Maintain consistency with the {arc_data['theme']} setting and tone
    5. Reference previous characters and locations when appropriate
    
    Return ONLY valid JSON in this format:
    {{
        "story": "detailed scene description that advances the plot",
        "scene_state": {{
            "location": "specific location fitting the stage",
            "time_of_day": "time period",
            "weather": "conditions",
            "ambient": "mood fitting the scene"
        }},
        "characters": {{
            "player": {{
                "health": number,
                "mood": "state fitting the scene",
                "status_effects": []
            }},
            "others": [
                {{
                    "name": "character name",
                    "description": "brief description",
                    "relationship": "relationship to player"
                }}
            ]
        }},
        "choices": [
            {{
                "text": "first choice description",
                "consequences": {{
                    "health_change": number,
                    "item_changes": ["add_item", "remove_item"]
                }}
            }},
            {{
                "text": "second choice description",
                "consequences": {{
                    "health_change": number,
                    "item_changes": ["add_item", "remove_item"]
                }}
            }}
        ],
        "is_ending": false
    }}
      
    For the final stage (Return and Resolution), set "is_ending" to true and make the choices represent different conclusions to the story.
    """
    
    try:
        response = client.models.generate_content(
            contents=[prompt],
            model="gemini-2.0-flash",
        )
        
        raw_text = clean_response(response.text)
        node_data = json.loads(raw_text)
        
        # Force exactly 2 choices
        if "choices" in node_data and len(node_data["choices"]) != 2:
            if len(node_data["choices"]) < 2:
                # Add generic choices if needed
                while len(node_data["choices"]) < 2:
                    node_data["choices"].append({
                        "text": f"Take an alternative path",
                        "consequences": {
                            "health_change": 0,
                            "item_changes": []
                        }
                    })
            else:
                # Keep only the first two choices
                node_data["choices"] = node_data["choices"][:2]
        
        # Set ending flag for the final level
        if current_stage == 7:
            node_data["is_ending"] = True
            
        return node_data
        
    except Exception as e:
        print(f"Error generating story node: {e}")
        # Return a fallback node if generation fails
        return generate_fallback_node(arc_data, current_stage)

def clean_response(raw_text):
    """Clean an API response to extract valid JSON"""
    raw_text = raw_text.strip()
    
    # Handle code blocks
    if raw_text.startswith("```"):
        lines = raw_text.split('\n')
        if lines[0].startswith("```") and lines[-1].startswith("```"):
            raw_text = '\n'.join(lines[1:-1])
        elif lines[0].startswith("```"):
            raw_text = '\n'.join(lines[1:])
    
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()
    
    # Find JSON boundaries
    start_idx = raw_text.find('{')
    end_idx = raw_text.rfind('}') + 1
    if start_idx < 0 or end_idx <= 0:
        raise Exception("Invalid JSON format")
        
    return raw_text[start_idx:end_idx]

def generate_fallback_node(arc_data, current_stage):
    """Generate a fallback node if regular generation fails"""
    stage_data = arc_data["arc"][current_stage]
    
    return {
        "story": f"You continue your adventure in the {arc_data['theme']} world. {stage_data['description']}",
        "scene_state": {
            "location": "unknown location",
            "time_of_day": "day",
            "weather": "clear",
            "ambient": "mysterious"
        },
        "characters": {
            "player": {
                "health": 80,
                "mood": "determined",
                "status_effects": []
            },
            "others": [
                {
                    "name": stage_data["characters"][0] if stage_data["characters"] else "Guide",
                    "description": "A helpful character",
                    "relationship": "neutral"
                }
            ]
        },
        "choices": [
            {
                "text": "Continue cautiously forward",
                "consequences": {
                    "health_change": 0,
                    "item_changes": []
                }
            },
            {
                "text": "Take a different approach",
                "consequences": {
                    "health_change": 0,
                    "item_changes": []
                }
            }
        ],
        "is_ending": (current_stage == 7)
    }

def save_game_state(graph, story_state, filepath="game_save.json"):
    """Save the game state to a file"""
    save_data = {
        "story_state": story_state.to_dict(),
        "graph": {
            "nodes": {},
            "edges": []
        }
    }
    
    for node in graph.adjacency_list:
        save_data["graph"]["nodes"][node.id] = {
            "story": node.story,
            "scene_state": getattr(node, "scene_state", {}),
            "characters": getattr(node, "characters", {}),
            "is_end": node.is_end
        }
        
        for child in graph.get_children(node):
            save_data["graph"]["edges"].append({
                "from": node.id,
                "to": child.id,
                "backtrack": getattr(child, "backtrack", False)
            })
    
    with open(filepath, 'w') as f:
        json.dump(save_data, f, indent=2)
    print(f"Game state saved to {filepath}")

def generate_predetermined_story(theme):
    """Generate a full predetermined story tree for the given theme"""
    output_file = f"{theme.lower().replace(' ', '_')}_story.json"
    
    print(f"\nGenerating story arc for {theme}...")
    arc_data = generate_story_arc(theme)
    with open('arc_data.json', 'w') as file:
        json.dump(arc_data, file, indent=4)
    
    #print(f"\nGenerating complete story tree with depth 8 and 2 choices per node...")
    depth = int(input("Enter the depth of the story tree (default is 8): "))
    print("This may take some time. Progress will be displayed below:")
    graph, story_state = generate_story_tree(arc_data, max_depth=depth)
    
    # Save the complete story tree
    save_game_state(graph, story_state, output_file)
    
    # Count the total number of nodes
    node_count = len(graph.adjacency_list)
    print(f"\nSuccess! Story tree for '{theme}' has been generated.")
    print(f"Total nodes: {node_count}")
    print(f"File saved as: {output_file}")
    
    return graph, story_state

def load_game_state(filepath=None, theme=None):
    """Load game state from file or create initial state with predetermined story"""
    try:
        # If theme is provided but no filepath, look for a themed file
        if theme and not filepath:
            potential_file = f"{theme.lower().replace(' ', '_')}_story.json"
            if os.path.exists(potential_file):
                filepath = potential_file
                
        # If a valid filepath is provided, load the game state
        if filepath and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            print(f"\nLoading game from {filepath}...")
            with open(filepath, 'r') as f:
                try:
                    save_data = json.load(f)
                except json.JSONDecodeError:
                    print("\nCorrupted save file. Creating new game...")
                    if theme:
                        return generate_predetermined_story(theme)
                    else:
                        raise Exception("Cannot create new game without theme")
            
            graph = Graph()
            story_state = StoryState.from_dict(save_data["story_state"])

            # Create all nodes first
            for node_id, node_data in save_data["graph"]["nodes"].items():
                node = Node(node_data["story"], node_data["is_end"])
                node.scene_state = node_data["scene_state"]
                node.characters = node_data["characters"]
                graph.add_node(node)
            
            # Add edges
            for edge in save_data["graph"]["edges"]:
                from_node = graph.get_node_with_id(edge["from"])
                to_node = graph.get_node_with_id(edge["to"])
                if from_node and to_node:
                    graph.add_edge(from_node, to_node)
                    if edge.get("backtrack"):
                        to_node.backtrack = True
            
            return graph, story_state
        
        # If we can't load from a file but have a theme, generate a new story
        elif theme:
            print(f"\nGenerating new {theme} adventure...")
            return generate_predetermined_story(theme)
        
        # No valid file and no theme
        else:
            raise Exception("Either filepath or theme must be provided")
            
    except Exception as e:
        print(f"\nError loading/creating game: {e}")
        raise

if __name__ == "__main__":
    print("Welcome to the Predetermined Story Generator!")
    print("=" * 50)
    
    theme = input("\nWhat kind of story would you like to generate?\n(e.g., Star Wars, Lord of the Rings, Dracula, Cyberpunk): ")
    generate_predetermined_story(theme)