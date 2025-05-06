from flask import Flask, render_template, request, jsonify, session
from flask_session import Session # Import Flask-Session
import os
import sys
from game_logic import (
    load_game, enrich_node_with_dialogue, get_scene_context_html,
    get_story_html, get_dialogue_html, get_consequence_html,
    get_ability_notification_html, get_health_notification_html,
    get_experience_notification_html, get_item_notification_html,
    generate_special_ability
)

# Add the parent directory to the Python path to import game_logic
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

# Configure Flask-Session
app.config["SESSION_PERMANENT"] = False # So sessions expire when browser closes (optional)
app.config["SESSION_TYPE"] = "filesystem" # Use filesystem for session storage
app.config["SECRET_KEY"] = os.urandom(24) # More secure secret key generation

# Initialize the Session extension
Session(app)

@app.route('/')
def index():
    # Clear any existing game state
    session.clear()
    return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data received'}), 400
        
    theme = data.get('theme', 'Fantasy')
    depth = int(data.get('depth', 3))
    choices_per_node = int(data.get('choices_per_node', 2))
    player_name = data.get('player_name', 'Adventurer')
    
    # Load the game
    try:
        nodes, current_node_id, max_depth = load_game(theme, depth, choices_per_node)
    except Exception as e:
        print(f"Error in load_game: {e}") # Log the error
        return jsonify({'error': 'Error loading game logic. Check server logs.'}), 500

    if not nodes or not current_node_id:
        return jsonify({'error': 'Failed to load game data (nodes or current_node_id is missing)'}), 500
    
    # Initialize player stats
    player_stats = {
        "health": 100,
        "experience": 10,
        "inventory": [],
        "abilities": []
    }
    
    # Add a starting ability based on theme
    try:
        starting_ability = generate_special_ability(theme, 10)
        if starting_ability:
            player_stats["abilities"].append(starting_ability)
    except Exception as e:
        print(f"Error generating starting ability: {e}")
        # Continue without starting ability if it fails
        starting_ability = None 
    
    # Store game state in session
    session['nodes'] = nodes
    session['current_node_id'] = current_node_id
    session['player_name'] = player_name
    session['player_stats'] = player_stats
    session['theme'] = theme
    session['choice_path'] = ["Start"]
    
    current_node = nodes.get(current_node_id)
    if not current_node:
        return jsonify({'error': f'Initial node {current_node_id} not found after loading.'}), 500

    # Generate HTML for the initial scene
    scene_html = get_scene_context_html(current_node, player_name, player_stats)
    story_html = get_story_html(current_node["story"])
    dialogue_html = get_dialogue_html(current_node.get("dialogue", ""))
    
    choices_html = '<div class="choices-container">'
    if current_node.get("children") and current_node.get("child_actions"):
        for i, (child_id, action) in enumerate(zip(current_node["children"], current_node["child_actions"])):
            choices_html += f'''
            <button class="choice-btn" data-choice="{i}">
                {action}
            </button>
            '''
    choices_html += '</div>'
    
    initial_notifications = []
    if starting_ability:
        initial_notifications.append(get_ability_notification_html(starting_ability))
    
    return jsonify({
        'player_name': player_name,
        'theme': theme,
        'choice_path': session['choice_path'],
        'scene_html': scene_html,
        'story_html': story_html,
        'dialogue_html': dialogue_html,
        'consequence_html': '', 
        'choices_html': choices_html,
        'notifications': initial_notifications,
        'is_end': current_node.get("is_end", False),
        'player_stats': player_stats
    })

@app.route('/make_choice', methods=['POST'])
def make_choice():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data received for choice'}), 400

    choice_index = int(data.get('choice_index', -1))
    
    nodes = session.get('nodes')
    current_node_id = session.get('current_node_id')
    player_name = session.get('player_name')
    player_stats = session.get('player_stats')
    theme = session.get('theme')
    choice_path = session.get('choice_path')

    if not all([nodes, current_node_id is not None, player_name, player_stats, theme, choice_path]):
        return jsonify({'error': 'Game state not found. Please restart the game.'}), 400
    
    current_node = nodes.get(current_node_id)
    if not current_node:
        return jsonify({'error': f'Current node {current_node_id} not found in game data. Please restart.'}), 400
        
    if not (0 <= choice_index < len(current_node.get("children", []))):
        return jsonify({'error': 'Invalid choice index. Please restart.'}), 400
    
    chosen_action = current_node["child_actions"][choice_index]
    chosen_node_id = current_node["children"][choice_index]
    chosen_node = nodes.get(chosen_node_id)

    if not chosen_node:
        return jsonify({'error': f'Chosen node {chosen_node_id} not found in game data. Please restart.'}), 400

    choice_path.append(chosen_action) 
    session['choice_path'] = choice_path
    
    notifications = []
    outcome = chosen_node.get("outcome", {})
    
    health_change = outcome.get("health_change", 0)
    if health_change != 0:
        old_health = player_stats["health"]
        player_stats["health"] = max(0, min(100, player_stats["health"] + health_change))
        notifications.append(get_health_notification_html(old_health, player_stats["health"]))
    
    experience_gained = outcome.get("experience_change", 0)
    if experience_gained > 0:
        player_stats["experience"] += experience_gained
        notifications.append(get_experience_notification_html(experience_gained))

    items_added = []
    inventory_changes = outcome.get("inventory_changes", [])
    for item_change in inventory_changes:
        if isinstance(item_change, str):
             player_stats["inventory"].append(item_change)
             items_added.append(item_change)
    
    if items_added:
        notifications.append(get_item_notification_html(items_added))
    
    is_game_over_by_health = player_stats["health"] <= 0
    
    session['current_node_id'] = chosen_node_id
    session['player_stats'] = player_stats
    
    is_end_node = chosen_node.get("is_end", False) or is_game_over_by_health
    if is_game_over_by_health and not chosen_node.get("is_end", False):
        chosen_node["story"] = chosen_node.get("story_on_death", "Your journey ends here, succumbing to your fate.")
        chosen_node["dialogue"] = ""
        chosen_node["child_actions"] = []
        chosen_node["children"] = []
    else:
        # Use the full story text for the new node
        chosen_node["story"] = chosen_node.get("full_story", chosen_node["story"])
        
        # Update character emotions and stats based on the outcome
        if "characters" in chosen_node:
            for char_name, char_data in chosen_node["characters"].items():
                if char_name.lower() == "player":
                    # Update player character data
                    char_data["health"] = player_stats["health"]
                    char_data["experience"] = player_stats["experience"]
                    char_data["inventory"] = player_stats["inventory"]
                    # Update player mood based on health
                    if player_stats["health"] < 30:
                        char_data["mood"] = "desperate"
                    elif player_stats["health"] < 50:
                        char_data["mood"] = "worried"
                    elif player_stats["health"] < 70:
                        char_data["mood"] = "cautious"
                    else:
                        char_data["mood"] = "determined"
                elif health_change != 0:
                    # Update other characters' moods based on health changes
                    if health_change > 0:
                        char_data["mood"] = "relieved"
                    else:
                        char_data["mood"] = "aggressive"

    # Generate HTML for the new scene
    scene_html = get_scene_context_html(chosen_node, player_name, player_stats)
    story_html = get_story_html(chosen_node["story"])
    dialogue_html = get_dialogue_html(chosen_node.get("dialogue", ""))
    
    # Get consequence text - either from the node or generate based on health change
    consequence_text = chosen_node.get("consequence_dialogue", "") 
    if not consequence_text and health_change != 0:
        if health_change > 0:
            consequence_text = "You feel your strength returning as your wounds heal."
        else:
            consequence_text = "The pain of your injuries makes it difficult to focus."
    consequence_html = get_consequence_html(consequence_text)
    
    # Generate choices HTML if not at an end node
    choices_html = ""
    if not is_end_node and chosen_node.get("children") and chosen_node.get("child_actions"):
        choices_html = '<div class="choices-container">'
        for i, (child_id, action) in enumerate(zip(chosen_node["children"], chosen_node["child_actions"])):
            choices_html += f'''
            <button class="choice-btn" data-choice="{i}">
                {action}
            </button>
            '''
        choices_html += '</div>'
    
    return jsonify({
        'player_name': player_name,
        'theme': theme,
        'choice_path': choice_path,
        'scene_html': scene_html,
        'story_html': story_html,
        'dialogue_html': dialogue_html,
        'consequence_html': consequence_html,
        'choices_html': choices_html,
        'notifications': notifications,
        'is_end': is_end_node,
        'player_stats': player_stats 
    })

@app.route('/game_over')
def game_over():
    player_name = session.get('player_name')
    player_stats = session.get('player_stats')
    choice_path = session.get('choice_path', ["Start"])
    
    if not all([player_name, player_stats]):
        return jsonify({'error': 'Game state not found for game over screen.'}), 400
    
    return render_template('game_over.html',
                         player_name=player_name,
                         player_stats=player_stats,
                         choice_path=choice_path)

if __name__ == '__main__':
    # Ensure the flask_session directory exists for filesystem sessions
    session_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flask_session')
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    app.config["SESSION_FILE_DIR"] = session_dir # Explicitly set for clarity

    app.run(debug=True) 