from google import genai
from Graph_Classes.Structure import Node, Graph
import json
import os

from arc import return_story_arc, return_story_tree

GOOGLE_API_KEY = "AIzaSyBQjg0r1vHzO3MNg_8zg18DyCTV8K-cJdE" 
client = genai.Client(api_key=GOOGLE_API_KEY)

class StoryState:
    def __init__(self):
        self.characters = {}
        self.current_scene = {}
        self.inventory = []
        self.visited_nodes = set()
        self.theme = ""
        self.max_depth = None

    def to_dict(self):
        return {
            "characters": self.characters,
            "current_scene": self.current_scene,
            "inventory": self.inventory,
            "visited_nodes": list(self.visited_nodes),
            "theme": self.theme,
            "max_depth": self.max_depth
        }

    @classmethod
    def from_dict(cls, data):
        state = cls()
        state.characters = data["characters"]
        state.current_scene = data["current_scene"]
        state.inventory = data["inventory"]
        state.visited_nodes = set(data["visited_nodes"])
        state.theme = data.get("theme", "")
        state.max_depth = data.get("max_depth", None)
        return state

def generate_story_node(context, story_state, story_arc, story_graph):
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

    Also using the story arc that is passed in and the golden example of a story, try to stay near these elements.
    **Closely follow the structure and spirit of the provided Story Arc and the Golden Example story graph.** Ensure the generated scene logically progresses from the previous one and aligns with the current stage of the overall narrative defined in the arc.
    Story Arc: {story_arc}
    Golden Example: {story_graph}

    **Story Length Guidance (Apply if `current_step_count` is provided and >= 7):**
    - The story has progressed for {context.get('current_step_count', 'several')} steps.
    - **Strongly prioritize steering the narrative towards a satisfying conclusion within the next 2-3 choices (steps).**
    - Evaluate if the *current* state naturally allows for a wrap-up soon. Generate choices that facilitate reaching a conclusion based on the Story Arc's final stages.
    - If the narrative is very close to a resolution (e.g., final confrontation passed, objective achieved/failed), consider setting `"is_ending": true` for this node or the immediate next one.
    - Ensure the conclusion feels earned and not abrupt.

    **Evaluate the Current Narrative Position:**
    - Consider the player's journey so far (recent actions, character states) in relation to the **Story Arc**.
    - **Specifically check if the narrative logically corresponds to the later stages of the arc (e.g., 'The Ordeal', 'The Reward', 'Return and Resolution').**
    - **Only set `"is_ending": true` if the current context genuinely represents a natural narrative conclusion fitting the arc's structure.** Do NOT end the story prematurely unless the player has reached a point of clear victory, defeat, or resolution as defined by the arc.
    - If ending the story, provide a clear `"ending_reason"` that justifies the conclusion based on the events and the arc.

    Generate a **smoothly flowing and coherent** story continuation that fits the {story_state.theme} theme and includes:
    1. Rich, detailed description of what happens next
    2. Character reactions and development
    3. Environmental changes and atmosphere
    4. Four distinct choice paths that maintain story consistency
    5. Meaningful consequences for each choice
    6. For each choice, include a block of at least three full sentences of spoken dialogue (strongly preferred) that reveals new plot or character information tied to that choice's outcome.
        - Dialogue must use the format [Name]: "...\" with the spoken words in quotes.
            - Each speaker gets exactly one line--even if they speak multiple sentences--so don't repeat the tag for the same speaker.
            - When the player speaks, use [You]:.
            - Other speakers must be existing character names or broad generic roles (e.g., [Crowd]:).
            - Each line appears on its own line, for example:
                [You]: "I've never seen ruins so alive with magic. Every shadow flickers with intent. I must stay vigilant."  
                [Arin]: "These stones whisper of an ancient pact. We tread on promises older than kingdoms. Be wary of their echoes."  
        - Inner monologue (only if dialogue truly doesn't fit) must be a single block of three sentences, without quotation marks, beginning with one of:
            You think: 
            You realize: 
            Your mind races as... 
            - To show emotion, wrap feelings in parentheses like (heart pounding), and use *actions* for movement or gestures.
            
        - Ensure the entire block directly advances the plot, reveals a clue, or deepens a character's motivation in connection with the choice's consequences.
    7. **Crucially, evaluate if the story has reached a natural narrative conclusion based on the Story Arc (especially if nearing or within the 'Return and Resolution' stage). If so, ensure "is_ending" is set to true. If not, ensure "is_ending" is false.**
    
    **If "is_ending" is true, also include an "ending_type" field with one of these values: "victory", "defeat", "neutral", "bittersweet", or "tragic" to classify the ending, and an "ending_reason" field with a one-sentence explanation of why the story is concluding.**
    
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
                "dialogue": "Provide at least three full sentences of spoken dialogue in one line per speaker, formatted as `[Name]: "...\"`. Do not repeat the tag for the same speaker across lines. Use `[You]: "...\"` for the player; other lines must use existing character names or sensible generic roles like `[Crowd]: "...\"`. If dialogue doesn't fit, supply a three-sentence inner monologue (no quotes), beginning with "You think: ", "You realize: ", or "Your mind races as..." using (emotions) and *actions* as needed.",
                "consequences": {{
                    "health_change": number,
                    "item_changes": ["add_item", "remove_item"]
                }},
                "can_backtrack": boolean
            }}
        ],
        "is_ending": boolean,
        "ending_type": "victory|defeat|neutral|bittersweet|tragic (only include if is_ending is true)",
        "ending_reason": "One sentence explanation of why the story concludes here (only include if is_ending is true)"
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

def generate_initial_story(theme, story_arc, story_tree):
    """Generate the starting point of the story"""
    prompt = f"""

    **Using the provided Story Arc and the example Story Tree (Golden Example) as guides, create an engaging opening.** Ensure the scene aligns with the initial stage of the Story Arc and reflects the tone and style of the Golden Example.
    Story Arc: {story_arc}
    Golden Example: {story_tree}

    Create an engaging and **thematically consistent** opening scene for a {theme} story with:
    1. Rich initial scene description that fits the {theme} theme
    2. Initial character setup including the player and characters relevant to {theme}
    3. Clear starting location that matches the {theme} setting
    4. Four distinct and **logical starting choices** that seamlessly flow from the opening scene and fit the {theme} world
    
    For example, if this is a Dracula story, include gothic elements, vampires, and Victorian era details.
    If this is a sci-fi story, include futuristic elements, technology, and space-related details.
    
    **Important: The initial scene must NOT be an ending. Ensure `"is_ending"` is always `false` for this initial generation.**

    Return as valid JSON in this format:
    {{
        "story": "detailed opening scene description fitting the {theme} theme",
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
                "name": "character fitting the {theme} theme",
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
        "is_ending": false,
        "ending_type": "victory|defeat|neutral|bittersweet|tragic (only include if is_ending is true)",
        "ending_reason": "One sentence explanation of why the story concludes here (only include if is_ending is true)"
    }}
    
    Make sure all elements (story, characters, choices, items) fit the {theme} theme and setting.
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
        
        # Try to fix common JSON errors
        raw_text = raw_text.replace(",\n}", "\n}")
        raw_text = raw_text.replace(",\n]", "\n]")
        raw_text = raw_text.replace(",,", ",")
        raw_text = raw_text.replace(",}", "}")
        raw_text = raw_text.replace(",]", "]")
        
        # Find JSON boundaries
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}') + 1
        if start_idx < 0 or end_idx <= 0:
            raise Exception("Invalid JSON format in initial story")
            
        json_text = raw_text[start_idx:end_idx]
        
        try:
            story_data = json.loads(json_text)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error in initial story: {e}")
            print("Retrying with fallback approach...")
            # This is a simplified fallback approach
            story_data = {
                "story": f"You find yourself in the world of {theme}, ready to begin your adventure.",
                "scene_state": {
                    "location": f"{theme} starting location",
                    "time_of_day": "morning",
                    "weather": "clear",
                    "ambient": "peaceful"
                },
                "characters": {
                    "player": {
                        "health": 100,
                        "mood": "determined",
                        "status_effects": [],
                        "relationships": {}
                    },
                    "other_characters": {
                        "guide": {
                            "name": "Guide",
                            "health": 100,
                            "mood": "helpful",
                            "relationships": {"player": "neutral"}
                        }
                    }
                },
                "choices": [
                    {
                        "text": f"Explore the {theme} world",
                        "dialogue": "You decide to venture forth and see what awaits.",
                        "consequences": {
                            "health_change": 0,
                            "item_changes": []
                        },
                        "can_backtrack": True
                    },
                    {
                        "text": "Seek guidance",
                        "dialogue": "You decide to find someone who can help you understand this world better.",
                        "consequences": {
                            "health_change": 0,
                            "item_changes": []
                        },
                        "can_backtrack": True
                    },
                    {
                        "text": "Gather supplies",
                        "dialogue": "You decide to prepare yourself before venturing further.",
                        "consequences": {
                            "health_change": 0,
                            "item_changes": ["add_basic_supplies"]
                        },
                        "can_backtrack": True
                    },
                    {
                        "text": "Follow the path ahead",
                        "dialogue": "You decide to follow the most obvious path and see where it leads.",
                        "consequences": {
                            "health_change": 0,
                            "item_changes": []
                        },
                        "can_backtrack": True
                    }
                ],
                "is_ending": False,
                "ending_type": "neutral",
                "ending_reason": "The story has reached its conclusion."
            }
        
        print("Story data parsed successfully")
        
        required_fields = ["story", "scene_state", "characters", "choices"]
        if not all(field in story_data for field in required_fields):
            print("Missing required fields in initial story, using fallback data")
            # Use same fallback approach as above
            # This code would be duplicate of the fallback above
            
        if "choices" not in story_data or len(story_data["choices"]) != 4:
            print("Initial story must have exactly 4 choices, fixing...")
            # Ensure we have exactly 4 choices
            if "choices" not in story_data:
                story_data["choices"] = []
                
            # Add generic choices if needed
            generic_choices = [
                {
                    "text": f"Explore the {theme} world",
                    "dialogue": "You decide to venture forth and see what awaits.",
                    "consequences": {
                        "health_change": 0,
                        "item_changes": []
                    },
                    "can_backtrack": True
                },
                {
                    "text": "Seek guidance",
                    "dialogue": "You decide to find someone who can help you understand this world better.",
                    "consequences": {
                        "health_change": 0,
                        "item_changes": []
                    },
                    "can_backtrack": True
                },
                {
                    "text": "Gather supplies",
                    "dialogue": "You decide to prepare yourself before venturing further.",
                    "consequences": {
                        "health_change": 0,
                        "item_changes": ["add_basic_supplies"]
                    },
                    "can_backtrack": True
                },
                {
                    "text": "Follow the path ahead",
                    "dialogue": "You decide to follow the most obvious path and see where it leads.",
                    "consequences": {
                        "health_change": 0,
                        "item_changes": []
                    },
                    "can_backtrack": True
                }
            ]
            
            # Keep existing choices and add generic ones until we have 4
            existing_choices = story_data["choices"][:min(len(story_data["choices"]), 4)]
            while len(existing_choices) < 4:
                existing_choices.append(generic_choices[len(existing_choices)])
                
            story_data["choices"] = existing_choices
            
        # Make sure is_ending is set
        if "is_ending" not in story_data:
            story_data["is_ending"] = False
            
        return story_data
        
    except Exception as e:
        print(f"\nError generating initial story: {e}")
        print("Generating fallback story data...")
        
        # Return a very basic fallback story
        return {
            "story": f"You find yourself in the world of {theme}, ready to begin your adventure.",
            "scene_state": {
                "location": f"{theme} starting location",
                "time_of_day": "morning",
                "weather": "clear",
                "ambient": "peaceful"
            },
            "characters": {
                "player": {
                    "health": 100,
                    "mood": "determined",
                    "status_effects": [],
                    "relationships": {}
                },
                "other_characters": {
                    "guide": {
                        "name": "Guide",
                        "health": 100,
                        "mood": "helpful",
                        "relationships": {"player": "neutral"}
                    }
                }
            },
            "choices": [
                {
                    "text": f"Explore the {theme} world",
                    "dialogue": "You decide to venture forth and see what awaits.",
                    "consequences": {
                        "health_change": 0,
                        "item_changes": []
                    },
                    "can_backtrack": True
                },
                {
                    "text": "Seek guidance",
                    "dialogue": "You decide to find someone who can help you understand this world better.",
                    "consequences": {
                        "health_change": 0,
                        "item_changes": []
                    },
                    "can_backtrack": True
                },
                {
                    "text": "Gather supplies",
                    "dialogue": "You decide to prepare yourself before venturing further.",
                    "consequences": {
                        "health_change": 0,
                        "item_changes": ["add_basic_supplies"]
                    },
                    "can_backtrack": True
                },
                {
                    "text": "Follow the path ahead",
                    "dialogue": "You decide to follow the most obvious path and see where it leads.",
                    "consequences": {
                        "health_change": 0,
                        "item_changes": []
                    },
                    "can_backtrack": True
                }
            ],
            "is_ending": False,
            "ending_type": "neutral",
            "ending_reason": "The story has reached its conclusion."
        }

def _generate_full_graph(theme, story_arc, story_tree_template, pregen_depth):
    """Generates a story graph up to the specified depth."""
    print(f"\nGenerating story graph up to depth {pregen_depth}...")
    graph = Graph()
    story_state = StoryState()
    story_state.theme = theme
    story_state.max_depth = pregen_depth # Store pregen_depth

    try:
        initial_data = generate_initial_story(theme, story_arc, story_tree_template)
        if not initial_data:
            raise Exception("Failed to generate initial story node")

        start_node = Node(initial_data["story"], initial_data.get("is_ending", False), initial_data.get("dialogue", ""))
        start_node.scene_state = initial_data["scene_state"]
        start_node.characters = initial_data["characters"]
        if initial_data.get("is_ending"):
            start_node.ending_type = initial_data.get("ending_type", "neutral")
            start_node.ending_reason = initial_data.get("ending_reason", "The story concluded at the start.")
        graph.add_node(start_node)

        story_state.current_scene = initial_data["scene_state"]
        story_state.characters = initial_data["characters"]
        story_state.visited_nodes.add(start_node.id) # Add start node as visited

        # Initialize the processing queue with the *initial choices*
        nodes_to_process = []
        if "choices" in initial_data and pregen_depth > 0: # Only process initial choices if pregen_depth allows
            for choice in initial_data["choices"]:
                # Create nodes for initial choices
                choice_node = Node(choice["text"], False, choice.get("dialogue", "")) # Initial choices are not endings
                # Use the scene/character state from the *initial* node for these first choices
                choice_node.scene_state = initial_data["scene_state"]
                choice_node.characters = initial_data["characters"]
                choice_node.consequences = choice.get("consequences", {})
                choice_node.backtrack = choice.get("can_backtrack", False)

                if choice_node.id not in graph.nodes:
                    graph.add_node(choice_node)
                graph.add_edge(start_node, choice_node) # Link start node to this choice

                # Add this initial choice node to the queue for further processing (at depth 1)
                if not choice_node.is_end:
                    nodes_to_process.append((choice_node, 1))
        elif pregen_depth == 0:
             print("\nPre-generation depth is 0. Only the starting node was created.")
        else:
            print("\nWarning: Initial story data did not contain choices. Pre-generation might be incomplete.")

        # nodes_to_process = [(start_node, 0)] # Queue for BFS: (node, depth) <-- Old logic removed
        processed_nodes = 0
        # Keep track of depths being processed for cleaner printing
        current_processing_depth = 0

        while nodes_to_process:
            current_node, current_depth = nodes_to_process.pop(0)
            
            # Print progress only when depth changes
            if current_depth > current_processing_depth:
                print(f"\n  Generating nodes at depth {current_depth}... (Processed nodes so far: {processed_nodes})")
                current_processing_depth = current_depth
            else:
                 # Still print something to show activity within the same depth
                 print(f"  Processing node {current_node.id} at depth {current_depth}...", end='\r')
            
            processed_nodes += 1
            # print(f"  Generating nodes at depth {current_depth}... (Processed: {processed_nodes})", end='\r') <-- Removed redundant print


            # Stop generating if depth limit reached or node is an end node
            # Note: Depth check is now >= pregen_depth because we start processing at depth 1
            if current_depth >= pregen_depth or current_node.is_end:
                continue

            # Check if children already exist (shouldn't happen with this new logic unless graph loaded?)
            existing_children = list(graph.get_children(current_node))
            if not existing_children:
                 # Prepare context for generating next choices
                story_context = {
                    "previous_scene": current_node.story,
                    "current_location": current_node.scene_state.get('location', 'Unknown'),
                    "time_of_day": current_node.scene_state.get('time_of_day', 'Unknown'),
                    "weather": current_node.scene_state.get('weather', 'Unknown'),
                    "player_status": { # Assuming default player status for pre-generation
                        "health": 100,
                        "inventory": [],
                    },
                    "characters": current_node.characters,
                    "recent_events": [current_node.story] # Simplified context for pre-gen
                }

                try:
                    # Generate the next set of choices/nodes
                    choice_data = generate_story_node(story_context, story_state, story_arc, story_tree_template)

                    if not choice_data or not choice_data.get("choices"):
                         print(f"\nWarning: Failed to generate choices for node {current_node.id} at depth {current_depth}. Stopping branch.")
                         continue # Stop generation for this branch if generation fails

                    # Add generated choices as new nodes
                    for choice in choice_data["choices"]:
                        new_node = Node(choice["text"], choice_data.get("is_ending", False), choice.get("dialogue", ""))
                        new_node.scene_state = choice_data["scene_state"]
                        new_node.characters = choice_data["characters"]
                        new_node.consequences = choice["consequences"]
                        new_node.backtrack = choice.get("can_backtrack", False)

                        if choice_data.get("is_ending"):
                            new_node.ending_type = choice_data.get("ending_type", "neutral")
                            new_node.ending_reason = choice_data.get("ending_reason", "The pre-generated story concluded here.")

                        if new_node.id not in graph.nodes: # Avoid adding duplicate nodes
                             graph.add_node(new_node)
                        graph.add_edge(current_node, new_node)

                        # Add to queue for further generation if not an end node
                        if not new_node.is_end:
                            nodes_to_process.append((new_node, current_depth + 1))

                except Exception as e:
                    print(f"\nError generating node content at depth {current_depth} for node {current_node.id}: {e}. Stopping branch.")
                    # Mark node as having failed generation? Or just stop the branch.
                    continue
            else:
                 # If children already exist (only happens for start node initially), add them to queue
                 for child in existing_children:
                      if not child.is_end:
                           nodes_to_process.append((child, current_depth + 1))


        print(f"\nFinished pre-generating graph. Total nodes: {len(graph.nodes)}")
        return graph, story_state

    except Exception as e:
        print(f"\nError during full graph generation: {e}")
        # Fallback: return a minimal graph with just the start node
        if 'start_node' in locals():
             graph = Graph()
             graph.add_node(start_node)
             story_state = StoryState()
             story_state.theme = theme
             story_state.max_depth = pregen_depth
             story_state.current_scene = start_node.scene_state
             story_state.characters = start_node.characters
             story_state.visited_nodes.add(start_node.id)
             print("Warning: Pre-generation failed. Starting with minimal graph.")
             return graph, story_state
        else:
             raise Exception("Fatal error: Could not even generate initial story node for pre-generation.")

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
            "is_end": node.is_end,
            "ending_type": getattr(node, "ending_type", "neutral") if node.is_end else None,
            "ending_reason": getattr(node, "ending_reason", "The story has reached its conclusion.") if node.is_end else None
        }
        
        for child in graph.get_children(node):
            save_data["graph"]["edges"].append({
                "from": node.id,
                "to": child.id,
                "backtrack": getattr(child, "backtrack", False)
            })
    
    with open(filepath, 'w') as f:
        json.dump(save_data, f, indent=2)

def load_game_state(filepath="game_save.json", theme=None, story_arc=None, story_tree=None, max_depth=None):
    """Load game state from file or create initial state with pre-generated graph if empty"""
    try:
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            print("\nSave file not found or empty. Creating new game state...")

            if not theme:
                raise Exception("Theme required for new game")
            if max_depth is None or max_depth <= 0:
                 print("Warning: Valid pre-generation depth not provided for new game, defaulting to 1.")
                 max_depth = 1 # Default pre-generation depth

            # Ensure we have a story arc
            if not story_arc:
                print("No story arc provided, generating one...")
                story_arc = return_story_arc(theme)

            # Ensure we have a story tree template (golden example)
            if not story_tree:
                print("No story tree template provided, generating one...")
                # Note: return_story_tree generates and saves the template, and returns the filename
                story_tree_file = return_story_tree(theme) # We need the content, not just the file path here for the template
                try:
                    with open(story_tree_file, 'r') as f:
                        story_tree = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError, TypeError) as e: # Added TypeError for Nonetype
                    print(f"Error loading story tree template from {story_tree_file}: {e}")
                    print("Continuing without a template story tree.")
                    story_tree = {} # Use an empty dict as fallback

            # Generate the full graph up to max_depth
            graph, story_state = _generate_full_graph(theme, story_arc, story_tree, max_depth)

            # Save the newly generated graph
            save_game_state(graph, story_state, filepath)
            print(f"New game state with pre-generated graph (depth {max_depth}) saved.")
            return graph, story_state

        # Try to load from existing file
        print(f"\nLoading game state from {filepath}...")
        try:
            with open(filepath, 'r') as f:
                save_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"\nCorrupted save file ({e}). Creating new game...")
            os.remove(filepath)
            return load_game_state(filepath, theme, story_arc, story_tree, max_depth) # Pass max_depth on retry
        except Exception as e:
            print(f"\nError reading save file: {e}. Creating new game...")
            os.remove(filepath)
            return load_game_state(filepath, theme, story_arc, story_tree, max_depth) # Pass max_depth on retry

        graph = Graph()
        story_state = StoryState.from_dict(save_data["story_state"])

        for node_id, node_data in save_data["graph"]["nodes"].items():
            node = Node(node_data["story"], node_data["is_end"], node_data.get("dialogue", ""))
            node.scene_state = node_data["scene_state"]
            node.characters = node_data["characters"]
            # Load ending information if this is an end node
            if node_data["is_end"]:
                node.ending_type = node_data.get("ending_type", "neutral")
                node.ending_reason = node_data.get("ending_reason", "The story has reached its conclusion.")
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
        
        # If we have a theme, try one more time with a clean slate
        if theme and os.path.exists(filepath):
            print("Attempting to create a new game from scratch...")
            try:
                os.remove(filepath)
                # Pass max_depth on retry
                return load_game_state(filepath, theme, story_arc, story_tree, max_depth)
            except Exception as e2:
                print(f"Final error: {e2}")
                raise
        else:
            raise