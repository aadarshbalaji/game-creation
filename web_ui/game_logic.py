import time
import json
import os
import textwrap
from webarc import return_story_tree, generate_scene_dialogue, generate_special_ability

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

def get_scene_context_html(node_data, player_name, player_stats):
    """Generate HTML for scene context instead of printing"""
    scene = node_data.get("scene_state", {})
    characters = node_data.get("characters", {})

    # Get scene data with fallbacks
    location = scene.get("location", "Crystal Caves")
    if location == "unknown":
        location = "Crystal Caves"
        
    time_of_day = scene.get("time_of_day", "Twilight")
    if time_of_day == "day":
        time_of_day = "Twilight"
        
    weather = scene.get("weather", "Foggy")
    if weather == "clear":
        weather = "Foggy"
        
    ambient = scene.get("ambient", "Flickering lights")
    if ambient == "mysterious":
        ambient = "Flickering lights"

    html = f"""
    <div class="scene-info">
        <p><strong>🌍 Location:</strong> {location}</p>
        <p><strong>🕒 Time:</strong> {time_of_day}</p>
        <p><strong>🌤️ Weather:</strong> {weather}</p>
        <p><strong>🐾 Ambient:</strong> {ambient}</p>
    """

    # Display characters present in the scene (except player)
    other_characters = {name: data for name, data in characters.items() if name.lower() != "player"}
    
    if other_characters:
        html += '<div class="characters-section">'
        
        # Group characters by type
        character_groups = {
            "ally": [],
            "enemy": [],
            "neutral": []
        }
        
        for char_name, char_data in other_characters.items():
            char_type = char_data.get("type", "neutral")
            character_groups[char_type].append((char_name, char_data))
        
        type_icons = {
            "ally": "🤝",
            "enemy": "⚔️",
            "neutral": "❓"
        }
        
        for char_type in ["ally", "neutral", "enemy"]:
            chars_of_type = character_groups[char_type]
            if chars_of_type:
                html += f'<div class="character-group {char_type}">'
                html += f'<h4>{type_icons[char_type]} {char_type.upper()} CHARACTERS</h4>'
                
                for char_name, char_data in chars_of_type:
                    html += f'<div class="character-card">'
                    html += f'<h5>{char_name.upper()}</h5>'
                    
                    if "description" in char_data:
                        html += f'<p>{char_data["description"]}</p>'
                    
                    health = char_data.get("health", 100)
                    health_percent = health
                    health_class = "health-bar"
                    if char_type == "enemy":
                        health_class += " enemy"
                    
                    html += f'''
                    <p>Health: 
                        <div class="health-bar-container">
                            <div class="{health_class}" style="width: {health_percent}%"></div>
                        </div>
                        {health}/100
                    </p>
                    '''
                    
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
                    
                    html += f'<p>Mood: {mood_emoji} {mood}</p>'
                    
                    relationship = char_data.get("relationships", {}).get("player", "neutral")
                    rel_emoji = {
                        "hostile": "⚔️", "friendly": "🤝", "neutral": "🤲",
                        "suspicious": "🔍", "trusting": "🛡️"
                    }.get(relationship.lower(), "🤲")
                    
                    html += f'<p>Feels {rel_emoji} {relationship} toward you</p>'
                    html += '</div>'  # Close character-card
                html += '</div>'  # Close character-group
    else:
        html += '<p>No other characters present</p>'

    # Player status
    html += f'''
    <div class="player-info">
        <h4>YOUR STATUS</h4>
        <p><strong>{player_name}</strong></p>
        <p>Health: 
            <div class="health-bar-container">
                <div class="health-bar" style="width: {player_stats["health"]}%"></div>
            </div>
            {player_stats["health"]}/100
        </p>
        <p>Experience: {player_stats["experience"]}</p>
        <p>🎒 Inventory: {", ".join(player_stats["inventory"]) if player_stats["inventory"] else "Empty"}</p>
    '''

    # Display abilities if the player has any
    if player_stats.get("abilities"):
        html += '<div class="abilities-section">'
        html += '<h4>YOUR ABILITIES</h4>'
        for ability in player_stats["abilities"]:
            ability_name = ability.get("name", "Unknown Ability")
            ability_desc = ability.get("description", "No description available")
            html += f'<div class="ability-card">'
            html += f'<p>✨ {ability_name}: {ability_desc}</p>'
            html += '</div>'
        html += '</div>'

    html += '</div></div>'  # Close player-info and scene-info
    return html

def get_story_html(story_text):
    """Generate HTML for story text"""
    return f'<div class="game-box">{story_text}</div>'

def get_dialogue_html(dialogue_text):
    """Generate HTML for dialogue"""
    if not dialogue_text:
        return ""
        
    dialogue_lines = dialogue_text.strip().split("\n")
    html = '<div class="dialogue-box">'
    
    for line in dialogue_lines:
        if "[" in line and "]:" in line:
            speaker_end = line.find("]:")
            speaker = line[:speaker_end+1]
            text = line[speaker_end+2:].strip()
            
            speaker_class = "player-speaker" if speaker == "[You]" else "speaker"
            html += f'''
            <div class="dialogue-line">
                <span class="{speaker_class}">{speaker}</span>: {text}
            </div>
            '''
        else:
            html += f'<div class="dialogue-line">{line}</div>'
            
    html += '</div>'
    return html

def get_consequence_html(consequence_text):
    """Generate HTML for consequence text"""
    if not consequence_text:
        return ""
        
    if isinstance(consequence_text, dict):
        for key, value in consequence_text.items():
            if isinstance(value, str) and value:
                return f'<div class="game-box">{value}</div>'
        return '<div class="game-box">You see the results of your actions unfold.</div>'
    else:
        return f'<div class="game-box">{consequence_text}</div>'

def get_ability_notification_html(ability):
    """Generate HTML for ability notification"""
    ability_name = ability.get("name", "Unknown Ability")
    ability_desc = ability.get("description", "No description available")
    
    return f'''
    <div class="notification-box ability-unlocked">
        <h4>✨✨✨ NEW ABILITY UNLOCKED ✨✨✨</h4>
        <p><strong>{ability_name}</strong></p>
        <p>{ability_desc}</p>
    </div>
    '''

def get_health_notification_html(old_health, new_health):
    """Generate HTML for health change notification"""
    if new_health > old_health:
        return f'''
        <div class="notification-box health-gain">
            <h4>💓 HEALTH UPDATE 💓</h4>
            <p>You gained {new_health - old_health} health points.</p>
        </div>
        '''
    else:
        return f'''
        <div class="notification-box health-update">
            <h4>💓 HEALTH UPDATE 💓</h4>
            <p>You lost {old_health - new_health} health points.</p>
        </div>
        '''

def get_experience_notification_html(exp_gained):
    """Generate HTML for experience gain notification"""
    return f'''
    <div class="notification-box experience-gain">
        <h4>✨ EXPERIENCE GAINED ✨</h4>
        <p>You gained {exp_gained} experience points.</p>
    </div>
    '''

def get_item_notification_html(items):
    """Generate HTML for item acquisition notification"""
    return f'''
    <div class="notification-box item-acquired">
        <h4>🎒 ITEMS ACQUIRED 🎒</h4>
        <p>You found: {", ".join(items)}</p>
    </div>
    '''

def enrich_node_with_dialogue(node, theme):
    """Add dialogue to a node if it doesn't already have it"""
    if "dialogue" in node and node["dialogue"]:
        return
    
    dialogue = generate_scene_dialogue(node, theme)
    if dialogue:
        node["dialogue"] = dialogue

def load_game(theme, depth=3, choices_per_node=2):
    """Generate and load a new story tree"""
    # Clean up old story files first
    for f in os.listdir():
        if f.endswith('_story.json'):
            try:
                os.remove(f)
            except:
                pass
                
    # Generate a new story tree
    filename = return_story_tree(theme, depth, choices_per_node)
    
    try:
        with open(filename, 'r') as f:
            save_data = json.load(f)
            
        graph_data = save_data.get("graph", {})
        
        nodes = {}
        for node_id, node_data in graph_data["nodes"].items():
            dialogue = node_data.get("dialogue", "")
            consequence = ""
            
            if node_id != "node_0" and isinstance(dialogue, dict):
                consequence = dialogue
                dialogue = ""
            elif node_id != "node_0" and not dialogue:
                consequence = node_data.get("dialogue", "")
            
            # Store both the full story and the current story text
            nodes[node_id] = {
                "story": node_data["story"],  # This is the full story text
                "full_story": node_data["story"],  # Keep a copy of the full story
                "is_end": node_data.get("is_end", False),
                "dialogue": dialogue,
                "consequence_dialogue": consequence,
                "scene_state": node_data.get("scene_state", {}),
                "characters": node_data.get("characters", {}),
                "outcome": node_data.get("outcome", {
                    "health_change": 0,
                    "experience_change": 0,
                    "inventory_changes": []
                }),
                "children": [],
                "child_actions": []
            }
        
        edge_count = 0
        for edge in graph_data["edges"]:
            from_id = edge["from"]
            to_id = edge["to"]
            if from_id in nodes:
                if to_id not in nodes[from_id]["children"]:
                    nodes[from_id]["children"].append(to_id)
                    edge_count += 1
                    
                    if len(nodes[from_id]["child_actions"]) < len(nodes[from_id]["children"]):
                        if "action" in edge and edge["action"]:
                            action = edge["action"]
                        else:
                            action = generate_action_choice(nodes[to_id]["story"], theme)
                        
                        nodes[from_id]["child_actions"].append(action)
        
        # Validate that all nodes with children have matching child_actions
        for node_id, node_data in nodes.items():
            if len(node_data["children"]) != len(node_data["child_actions"]):
                while len(node_data["child_actions"]) < len(node_data["children"]):
                    child_id = node_data["children"][len(node_data["child_actions"])]
                    action = generate_action_choice(nodes[child_id]["story"], theme)
                    node_data["child_actions"].append(action)
                
        return nodes, "node_0", depth
    except Exception as e:
        print(f"Error loading game: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def generate_action_choice(scene_text, theme):
    """Generate a concise action-oriented choice from scene description"""
    # List of action verbs by category
    exploration_verbs = ["Investigate", "Explore", "Search", "Examine", "Scout"]
    movement_verbs = ["Enter", "Climb", "Sneak", "Run", "Jump", "Navigate", "Descend"]
    interaction_verbs = ["Talk to", "Question", "Confront", "Persuade", "Negotiate with"]
    combat_verbs = ["Attack", "Ambush", "Fight", "Defend against", "Charge"]
    stealth_verbs = ["Hide from", "Avoid", "Evade", "Bypass", "Slip past"]
    tech_verbs = ["Hack", "Activate", "Disable", "Repair", "Override"]
    
    scene_lower = scene_text.lower()
    first_word = scene_text.split()[0].lower()
    action_verbs = ["search", "investigate", "approach", "examine", "open", "enter", "take", "grab", "talk", "speak", 
                   "fight", "attack", "run", "flee", "hide", "sneak", "climb", "jump", "use", "activate", "disable", 
                   "hack", "break", "repair", "explore"]
    
    if any(first_word == verb or first_word.startswith(verb) for verb in action_verbs) and len(scene_text.split()) < 20:
        sentences = scene_text.split('.')
        if len(sentences) > 2:
            return sentences[0].strip() + '.'
        return scene_text
        
    if any(word in scene_lower for word in ["door", "entrance", "exit", "passage", "path", "corridor"]):
        verb = movement_verbs[hash(scene_text) % len(movement_verbs)]
        for target in ["doorway", "passage", "corridor", "entrance", "tunnel", "opening"]:
            if target in scene_lower:
                return f"{verb} the {target} to see what lies beyond."
        return f"{verb} the area cautiously, ready for whatever awaits."
        
    elif any(word in scene_lower for word in ["person", "figure", "alien", "creature", "officer", "guard", "character"]):
        verb = interaction_verbs[hash(scene_text) % len(interaction_verbs)]
        for target in ["figure", "person", "officer", "alien", "guard", "creature", "individual"]:
            if target in scene_lower:
                return f"{verb} the {target} to learn more about the situation."
        return f"{verb} the mysterious figure to gain valuable information."
        
    elif any(word in scene_lower for word in ["terminal", "computer", "console", "device", "technology", "system"]):
        verb = tech_verbs[hash(scene_text) % len(tech_verbs)]
        for target in ["terminal", "console", "system", "device", "computer", "machine", "panel"]:
            if target in scene_lower:
                return f"{verb} the {target} to access its data or functions."
        return f"{verb} the technology to gain an advantage."
        
    elif any(word in scene_lower for word in ["enemy", "threat", "weapon", "danger", "attack", "fight"]):
        verb = combat_verbs[hash(scene_text) % len(combat_verbs)]
        for target in ["enemy", "guard", "creature", "attacker", "threat", "opponent"]:
            if target in scene_lower:
                return f"{verb} the {target} using your available resources."
        return f"{verb} the immediate threat before it's too late."
        
    elif any(word in scene_lower for word in ["hide", "stealth", "quiet", "silent", "undetected", "sneak"]):
        verb = stealth_verbs[hash(scene_text) % len(stealth_verbs)]
        for target in ["guard", "patrol", "camera", "sensor", "security", "threat"]:
            if target in scene_lower:
                return f"{verb} the {target} without being detected."
        return f"{verb} any potential dangers as you proceed carefully."
    
    else:
        verb = exploration_verbs[hash(scene_text) % len(exploration_verbs)]
        for target in ["area", "room", "building", "structure", "wreckage", "ruins", "debris"]:
            if target in scene_lower:
                return f"{verb} the {target} to discover what secrets it holds."
        
        if "star wars" in theme.lower() or "space" in theme.lower():
            return f"{verb} the area for signs of Imperial activity or technology."
        elif "fantasy" in theme.lower() or "magic" in theme.lower():
            return f"{verb} the surroundings for magical artifacts or hidden passages."
        elif "cyberpunk" in theme.lower() or "tech" in theme.lower():
            return f"{verb} the location for valuable data or technological advantages."
        else:
            return f"{verb} the surroundings for clues or useful items."
