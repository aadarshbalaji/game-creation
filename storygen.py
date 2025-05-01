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

def generate_story_node(context, story_state):
    """Generate a story node with rich content based on current context"""
    prompt = f"""
    Based on this detailed story context:
    Previous Scene: {context['previous_scene']}
    Current Location: {context['current_location']}
    Time of Day: {context['time_of_day']}
    Weather: {context['weather']}
    Story Theme: {story_state.theme}  
    
    Player Status:
    - Health: {context['player_status']['health']}
    - Inventory: {', '.join(context['player_status']['inventory'])}
    - Recent Actions: {', '.join(context['recent_events'])}
    
    Characters Present: {json.dumps(context['characters'], indent=2)}

    Generate a vivid story continuation that fits the {story_state.theme} theme and includes:
    1. Rich, detailed description of what happens next
    2. Character reactions and development
    3. Environmental changes and atmosphere
    4. Four distinct choice paths that maintain story consistency
    5. Meaningful consequences for each choice
    6. For each choice, include three to five full sentences of spoken dialogue that reveal new plot or character information tied to that choice’s outcome.
        - Dialogue lines must use brackets **only** around speaker tags—`[You]: “…”`, `[Arin]: “…”`, `[Crowd]: “…”`
            - When the player speaks, use `[You]:`.
            - Other speakers must be existing character names or sensible generic roles (e.g., `[Crowd]:`).
            - Place each speaker’s line on its own line.
                ```
                [You]: “I’ve never seen ruins so alive with magic. Every shadow flickers with intent. I must stay vigilant.”
                [Arin]: “These stones whisper of an ancient pact. We tread on promises older than kingdoms. Be wary of their echoes.”
                ```
        - If spoken dialogue doesn’t fit naturally, supply a three-sentence inner reflection without brackets, beginning with one of:
                - `You think: `
                - `You realize: `
                - `Your mind races: `
                - `You thought`
        - Ensure the entire block directly advances the plot, reveals a clue, or deepens a character’s motivation in connection with the choice’s consequences.
    
    Keep the style and elements consistent with {story_state.theme} setting.

    Return ONLY valid JSON in this exact format:
    {{
        "story": "detailed scene description maintaining the theme",
        "scene_state": {{
            "location": "specific location fitting the theme",
            "time_of_day": "time period",
            "weather": "conditions",
            "ambient": "thematic mood"
        }},
        "characters": {{
            "player": {{
                "health": number,
                "mood": "state fitting the scene",
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
                "text": "choice description fitting the theme",
                "dialogue": "Provide three to five full sentences of spoken dialogue in the format `[Name]: “…”`. One line per speaker, using `[You]:` for the player and existing names or roles for others. If dialogue isn’t natural, supply a two to four sentences of inner reflection starting with `You think:`, `You realize:`, or `Your mind races as`",
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
        raw_text = response.text.strip()
        
        if raw_text.startswith("```"):
            lines = raw_text.split('\n')
            if lines[0].startswith("```") and lines[-1].startswith("```"):
                raw_text = '\n'.join(lines[1:-1])
            elif lines[0].startswith("```"):
                raw_text = '\n'.join(lines[1:])
        
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}') + 1
        if start_idx < 0 or end_idx <= 0:
            raise Exception("Invalid JSON format")

        json_text = raw_text[start_idx:end_idx]
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

def generate_initial_story(ip):

    """Generate the starting point of the story"""
    prompt = f"""
    Create an engaging opening scene for a {ip} story with:
    1. Rich initial scene description that fits the {ip} theme
    2. Initial character setup including the player and characters relevant to {ip}
    3. Clear starting location that matches the {ip} setting
    4. Four distinct paths to begin the adventure in the {ip} world
    
    For example, if this is a Dracula story, include gothic elements, vampires, and Victorian era details.
    If this is a sci-fi story, include futuristic elements, technology, and space-related details.
    
    Return as valid JSON in this format:
    {{
        "story": "detailed opening scene description fitting the {ip} theme",
        "scene_state": {{
            "location": "thematic location name",
            "time_of_day": "time period",
            "weather": "atmospheric conditions",
            "ambient": "mood fitting the theme"
        }},
        "characters": {{
            "player": {{
                "health": 100,
                "mood": "initial state",
                "status_effects": [],
                "relationships": {{}}
            }},
            "other_characters": {{
                "name": "character fitting the {ip} theme",
                "health": number,
                "mood": "thematic state",
                "relationships": {{"player": "initial relationship"}}
            }}
        }},
        "choices": [
            {{
                "text": "choice description fitting the theme",
                "dialogue": "brief character dialogue or character monologue to reveal information about the result of this choice",
                "consequences": {{
                    "health_change": number,
                    "item_changes": ["add_item", "remove_item"]
                }},
                "can_backtrack": boolean
            }}
        ],
        "is_ending": false
    }}
    
    Make sure all elements (story, characters, choices, items) fit the {ip} theme and setting.
    """
    
    try:
        response = client.models.generate_content(
            contents=[prompt],
            model="gemini-2.0-flash",
        )
        
        raw_text = response.text.strip()

        if raw_text.startswith("```"):
            lines = raw_text.split('\n')
            if lines[0].startswith("```") and lines[-1].startswith("```"):
                raw_text = '\n'.join(lines[1:-1])
            elif lines[0].startswith("```"):
                raw_text = '\n'.join(lines[1:])
                
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        story_data = json.loads(raw_text)
        print("Story data parsed successfully")
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
            "dialogue": node.dialogue,
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

def load_game_state(filepath="game_save.json", theme=None):
    """Load game state from file or create initial state if empty"""
    try:
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            print("\nCreating new game state...")
            
            if not theme:
                raise Exception("Theme required for new game")
            
            initial_data = generate_initial_story(theme)
            if not initial_data:
                raise Exception("Failed to generate initial story")
        
            graph = Graph()
            story_state = StoryState()
            
            start_node = Node(initial_data["story"], initial_data["is_ending"])
            start_node.scene_state = initial_data["scene_state"]
            start_node.characters = initial_data["characters"]
            graph.add_node(start_node)
            
            story_state.current_scene = initial_data["scene_state"]
            story_state.characters = initial_data["characters"]
            story_state.theme = theme  
            
            for choice in initial_data["choices"]:
                choice_node = Node(choice["text"], False, choice.get("dialogue", ""))
                choice_node.scene_state = initial_data["scene_state"]
                choice_node.characters = initial_data["characters"]
                choice_node.consequences = choice["consequences"]
                choice_node.backtrack = choice.get("can_backtrack", False)
                graph.add_node(choice_node)
                graph.add_edge(start_node, choice_node)
            
            save_game_state(graph, story_state, filepath)
            return graph, story_state
            
        with open(filepath, 'r') as f:
            try:
                save_data = json.load(f)
            except json.JSONDecodeError:
                print("\nCorrupted save file. Creating new game...")
                os.remove(filepath)
                return load_game_state(filepath)
            
        graph = Graph()
        story_state = StoryState.from_dict(save_data["story_state"])

        for node_id, node_data in save_data["graph"]["nodes"].items():
            node = Node(node_data["story"], node_data["is_end"], node_data.get("dialogue", ""))
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