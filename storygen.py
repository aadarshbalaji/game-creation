from google import genai
from Graph_Classes.Structure import Node, Graph
import json
import os

GOOGLE_API_KEY = "AIzaSyAOw2K58MLs6bDLIIgLoUOP1JEfKnk26zA" 
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

def generate_story_node(context, story_state, arc_data=None, current_stage_info=None):
    """Generate a story node with rich content based on current context, guided by the story arc."""
    
    # --- Build Arc Context --- 
    arc_context_prompt = ""
    if arc_data and current_stage_info:
        stage_index = current_stage_info.get("stage_index", 0)
        stage_progression = current_stage_info.get("progression", "Unknown")
        
        if 0 <= stage_index < len(arc_data.get('arc', [])):
            stage_data = arc_data['arc'][stage_index]
            arc_context_prompt = f"""
            Story Arc Context:
            - Current Stage: {stage_data.get('stage', 'Unknown')} ({stage_progression})
            - Stage Goal: {stage_data.get('description', 'Unknown')}
            - Key Plot Points for this stage: {', '.join(stage_data.get('key_plot_points', []))}
            - Overall Goal: {arc_data.get('golden_path', 'Complete the adventure')}
            """
        else:
             arc_context_prompt = "Story Arc Context: Stage information is unavailable."
    else:
        arc_context_prompt = "Story Arc Context: No arc data provided."
    # --- End Arc Context ---
    
    prompt = f"""
    Based on this detailed story context:
    Previous Scene: {context['previous_scene']}
    Current Location: {context['current_location']}
    Time of Day: {context['time_of_day']}
    Weather: {context['weather']}
    Story Theme: {story_state.theme}  
    
    {arc_context_prompt}
    
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
        "story": "detailed scene description maintaining the theme and aligning with the story arc stage",
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
                "dialogue": "Provide three to five full sentences of spoken dialogue in the format `[Name]: “…”`. One line per speaker, using `[You]:` for the player and existing names or roles for others. If dialogue isn’t natural, supply a two to four sentences of inner reflection starting with `You think:`, `You realize:`, or `Your mind races`",
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