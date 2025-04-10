from google import genai
from Graph_Classes.Structure import Node, Graph
import json
import os

GOOGLE_API_KEY = "" 
client = genai.Client(api_key=GOOGLE_API_KEY)

class StoryState:
    def __init__(self):
        self.characters = {}
        self.current_scene = {}
        self.inventory = []
        self.visited_nodes = set()

    def to_dict(self):
        return {
            "characters": self.characters,
            "current_scene": self.current_scene,
            "inventory": self.inventory,
            "visited_nodes": list(self.visited_nodes)
        }

    @classmethod
    def from_dict(cls, data):
        state = cls()
        state.characters = data["characters"]
        state.current_scene = data["current_scene"]
        state.inventory = data["inventory"]
        state.visited_nodes = set(data["visited_nodes"])
        return state

def generate_story_node(context, story_state):
    """Generate a story node with rich content based on current context"""
    prompt = f"""
    Based on this story context and state:
    Context: {context}
    Current Scene: {json.dumps(story_state.current_scene)}
    Characters: {json.dumps(story_state.characters)}
    Inventory: {story_state.inventory}
    Previous Locations: {list(story_state.visited_nodes)}

    Generate a story continuation that includes:
    1. Rich scene description
    2. Character states and interactions
    3. Exactly 4 distinct choice paths
    4. Consequences for each choice
    5. Whether this could be an ending

    Return ONLY valid JSON in this exact format:
    {{
        "story": "detailed scene description",
        "scene_state": {{
            "location": "specific location",
            "time_of_day": "time period",
            "weather": "conditions",
            "ambient": "mood"
        }},
        "characters": {{
            "player": {{
                "health": number,
                "mood": "state",
                "status_effects": [],
                "relationships": {{}}
            }},
            "other_characters": {{
                "health": number,
                "mood": "state",
                "status_effects": [],
                "relationships": {{}}
            }}
        }},
        "choices": [
            {{
                "text": "choice description",
                "consequences": {{
                    "health_change": number,
                    "item_changes": ["add_item", "remove_item"]
                }},
                "can_backtrack": boolean
            }}
        ],
        "is_ending": boolean
    }}
    """

    try:
        response = client.models.generate_content(
            contents=[prompt],
            model="gemini-2.0-flash",
        )

        if not response.text:
            raise Exception("Empty response from API")

        json_text = response.text.strip()
        start_idx = json_text.find('{')
        end_idx = json_text.rfind('}') + 1
        if start_idx < 0 or end_idx <= 0:
            raise Exception("Invalid JSON format")

        json_text = json_text[start_idx:end_idx]
        story_data = json.loads(json_text)

        required_fields = ["story", "scene_state", "characters", "choices"]
        if not all(field in story_data for field in required_fields):
            raise Exception("Missing required fields")

        if not story_data.get("is_ending") and len(story_data["choices"]) != 4:
            raise Exception("Invalid number of choices")

        print("\nGenerated new story segment successfully!")
        return story_data

    except Exception as e:
        print(f"\nError generating story: {e}")
        raise

def generate_initial_story():
    """Generate the starting point of the story"""
    prompt = """
    Create an engaging opening scene for a fantasy adventure with:
    1. Rich initial scene description
    2. Initial character setup (player and other characters)
    3. Clear starting location
    4. Four distinct paths to begin the adventure
    
    Return as valid JSON in this format:
    {
        "story": "detailed opening scene description",
        "scene_state": {
            "location": "starting location name",
            "time_of_day": "time period",
            "weather": "conditions",
            "ambient": "mood"
        },
        "characters": {
            "player": {
                "health": 100,
                "mood": "initial state",
                "status_effects": [],
                "relationships": {}
            },
            "other_characters": {
                "name": "character name",
                "health": number,
                "mood": "state",
                "relationships": {"player": "initial relationship"}
            }
        },
        "choices": [
            {
                "text": "choice description",
                "consequences": {
                    "health_change": number,
                    "item_changes": ["add_item", "remove_item"]
                },
                "can_backtrack": boolean
            }
        ],
        "is_ending": false
    }
    """
    
    try:
        response = client.models.generate_content(
            contents=[prompt],
            model="gemini-2.0-flash",
        )
        
        # Get raw response and clean it
        raw_text = response.text.strip()

        
        # Remove markdown code block if present
        if raw_text.startswith("```"):
            lines = raw_text.split('\n')
            # Remove first and last lines if they're markdown markers
            if lines[0].startswith("```") and lines[-1].startswith("```"):
                raw_text = '\n'.join(lines[1:-1])
            # Remove just the first line if it's a markdown marker
            elif lines[0].startswith("```"):
                raw_text = '\n'.join(lines[1:])
                
        # Clean up any remaining markdown markers
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        
        # Parse JSON
        story_data = json.loads(raw_text)
        print("Story data parsed successfully")
        
        # Validate required fields
        required_fields = ["story", "scene_state", "characters", "choices"]
        if not all(field in story_data for field in required_fields):
            raise Exception("Missing required fields in initial story")
            
        if len(story_data["choices"]) != 4:
            raise Exception("Initial story must have exactly 4 choices")
            
        return story_data
        
    except Exception as e:
        print(f"\nError generating initial story: {e}")
        raise

def save_game_state(graph, story_state, filepath="game_save.json"):
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

def load_game_state(filepath="game_save.json"):
    """Load game state from file or create initial state if empty"""
    try:
        # Check if file exists and is empty
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            print("\nCreating new game state...")
            
            # Generate initial story
            initial_data = generate_initial_story()
            print("test")
            if not initial_data:
                raise Exception("Failed to generate initial story")
            
            # Create new graph and state
            graph = Graph()
            story_state = StoryState()
            
            # Create start node
            start_node = Node(initial_data["story"], initial_data["is_ending"])
            start_node.scene_state = initial_data["scene_state"]
            start_node.characters = initial_data["characters"]
            graph.add_node(start_node)
            
            # Update story state
            story_state.current_scene = initial_data["scene_state"]
            story_state.characters = initial_data["characters"]
            
            # Generate initial choices
            for choice in initial_data["choices"]:
                choice_node = Node(choice["text"], False)
                choice_node.scene_state = initial_data["scene_state"]
                choice_node.characters = initial_data["characters"]
                choice_node.consequences = choice["consequences"]
                choice_node.backtrack = choice.get("can_backtrack", False)
                graph.add_node(choice_node)
                graph.add_edge(start_node, choice_node)
            
            # Save initial state
            save_game_state(graph, story_state, filepath)
            return graph, story_state
            
        # Load existing save file
        with open(filepath, 'r') as f:
            try:
                save_data = json.load(f)
            except json.JSONDecodeError:
                print("\nCorrupted save file. Creating new game...")
                os.remove(filepath)
                return load_game_state(filepath)
            
        # Create graph and state from save data
        graph = Graph()
        story_state = StoryState.from_dict(save_data["story_state"])
        
        # Load nodes and edges
        for node_id, node_data in save_data["graph"]["nodes"].items():
            node = Node(node_data["story"], node_data["is_end"])
            node.scene_state = node_data["scene_state"]
            node.characters = node_data["characters"]
            graph.add_node(node)
        
        for edge in save_data["graph"]["edges"]:
            from_node = graph.get_node_with_id(edge["from"])
            to_node = graph.get_node_with_id(edge["to"])
            if from_node and to_node:
                graph.add_edge(from_node, to_node)
                if edge.get("backtrack"):
                    to_node.backtrack = True
        
        return graph, story_state
        
    except Exception as e:
        print(f"\nError loading/creating save: {e}")
        raise