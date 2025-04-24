import time
import json
import os
from storygen import StoryState, generate_initial_story, generate_story_node, save_game_state, load_game_state
from Graph_Classes.Structure import Node, Graph
from Graph_Classes.Interact import Player

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

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

def print_box(text, width=70, padding=1):
    """Print text in a decorative box"""
    horizontal = "+" + "-" * width + "+"
    empty = "|" + " " * width + "|"
    
    print(horizontal)
    for _ in range(padding):
        print(empty)
    
    for line in wrap_text(text, width-2).split('\n'):
        print(f"| {line:<{width-2}} |")
    
    for _ in range(padding):
        print(empty)
    print(horizontal)

def print_state(title, data, indent=2):
    """Print state information in a formatted way"""
    print(f"\n{'='*20} {title} {'='*20}")
    
    if title == "CHARACTERS PRESENT":
        for char_name, char_data in data.items():
            if char_name == "player":
                continue  
            
            if char_name == "other_characters":
                for npc_name, npc_data in char_data.items():
                    print(f"\n► {npc_name.upper()}")
                    if isinstance(npc_data, dict):
                        health = npc_data.get('health', 0)
                        health_bar = '♥' * (health // 10) + '░' * ((100 - health) // 10)
                        print(f"  Health: [{health_bar}] {health}/100")
                        
                        mood = npc_data.get('mood', 'unknown')
                        mood_emoji = {
                            'angry': '😠', 'happy': '😊', 'sad': '😢', 
                            'afraid': '😨', 'determined': '😤', 'sleeping': '😴',
                            'neutral': '😐', 'aggressive': '😠', 'friendly': '🙂',
                            'fearful': '😨', 'panicked': '😰', 'suspicious': '🤨'
                        }.get(mood.lower(), '❓')
                        print(f"  Mood: {mood_emoji} {mood}")
                    
                        if npc_data.get('status_effects'):
                            effects = ', '.join(npc_data['status_effects'])
                            print(f"  Status Effects: ✨ {effects}")
                        
                        if npc_data.get('relationships'):
                            print("  Relationships:")
                            for target, relation in npc_data['relationships'].items():
                                print(f"   • {target}: {relation}")
            else:
                print(f"\n► {char_name.upper()}")
    
    elif title == "CURRENT SCENE":
        print(f"\n🌍 Location: {data.get('location', 'Unknown')}")
        print(f"🕒 Time: {data.get('time_of_day', 'Unknown')}")
        print(f"🌤️  Weather: {data.get('weather', 'Unknown')}")
        print(f"💫 Ambient: {data.get('ambient', 'Unknown')}")
    
    print("\n" + "=" * (42 + len(title)))



def main():
    clear_screen()
    print("Welcome to Netflix's AI-Generated CYOA!")
    print("=" * 50)
    
    player_name = input("\nEnter your name: ")
    story_theme = input("\nWhat kind of story would you like to experience?\n(e.g., Star Wars, Lord of the Rings, Dracula, your own movie idea): ")
    death_reason = None
    
    try:
        graph, story_state = load_game_state(theme=story_theme)
        if not graph:
            graph = Graph()
            story_state = StoryState()
            print(f"\nGenerating your unique {story_theme} adventure...")
            
            initial_data = generate_initial_story(story_theme)
            if not initial_data:
                raise Exception("Failed to generate initial story")
            
            start_node = Node(initial_data["story"], initial_data["is_ending"], initial_data.get("dialogue", ""))
            start_node.scene_state = initial_data["scene_state"]
            start_node.characters = initial_data["characters"]
            graph.add_node(start_node)
            
            story_state.current_scene = initial_data["scene_state"]
            story_state.characters = initial_data["characters"]
            
            for choice in initial_data["choices"]:
                choice_node = Node(choice["text"], False)
                choice_node.scene_state = initial_data["scene_state"]
                choice_node.characters = initial_data["characters"]
                choice_node.consequences = choice["consequences"]
                choice_node.backtrack = choice.get("can_backtrack", False)
                graph.add_node(choice_node)
                graph.add_edge(start_node, choice_node)
            
            save_game_state(graph, story_state)
        else:
            start_node = next(iter(graph.adjacency_list))
        
        player = Player(player_name, start_node)
        while not player.is_dead and not player.current_node.is_end:
            clear_screen()
            print_box(player.current_node.story)
            if player.current_node.dialogue:
                print_box(player.current_node.dialogue)
            print_state("CURRENT SCENE", player.current_node.scene_state)
            print_state("CHARACTERS PRESENT", player.current_node.characters)

            print("\n🎮 YOUR STATUS 🎮")
            print(f"╔{'═'*50}╗")
            print(f"║ {player.name:<48} ║")
            print(f"║ Health: [{'♥' * (player.health // 10)}{'░' * ((100 - player.health) // 10)}] {player.health:>3}/100 ║")
            print(f"║ Experience: [{'✦' * (player.experience // 10)}{'░' * ((100 - player.experience) // 10)}] {player.experience:>3} ║")
            if player.inventory:
                print(f"║ 🎒 Inventory:                                          ║")
                for item in player.inventory:
                    print(f"║  • {item:<46} ║")
            else:
                print(f"║ 🎒 Inventory: Empty                                    ║")
            print(f"╚{'═'*50}╝")
            
            choices = list(graph.get_children(player.current_node))
            if not choices and not player.current_node.is_end:
                print("\nGenerating new story paths...")
                try:
                    story_context = {
                        "previous_scene": player.current_node.story,
                        "current_location": player.current_node.scene_state['location'],
                        "time_of_day": player.current_node.scene_state['time_of_day'],
                        "weather": player.current_node.scene_state['weather'],
                        "player_status": {
                            "health": player.health,
                            "inventory": player.inventory
                        },
                        "characters": player.current_node.characters,
                        "recent_events": [node.story for node in player.traversed_nodes[-3:]]
                    }
                    
                    choice_data = generate_story_node(story_context, story_state)
                    
                    for choice in choice_data["choices"]:
                        new_node = Node(choice["text"], choice_data.get("is_ending", False), choice.get("dialogue", ""))
                        new_node.scene_state = choice_data["scene_state"]
                        new_node.characters = choice_data["characters"]
                        new_node.consequences = choice["consequences"]
                        new_node.backtrack = choice.get("can_backtrack", False)
                        graph.add_node(new_node)
                        graph.add_edge(player.current_node, new_node)
                    
                    choices = list(graph.get_children(player.current_node))
                except Exception as e:
                    print(f"\nError in choice generation: {e}")
                    break
            
            if choices:
                print("\n🎲 AVAILABLE CHOICES 🎲")
                print(f"╔{'═'*68}╗")
                for i, choice in enumerate(choices, 1):
                    print(f"║ {i}. {wrap_text(choice.story, 64):<64} ║")
                    if hasattr(choice, 'consequences'):
                        consequences = choice.consequences
                        if consequences.get('health_change'):
                            health_change = consequences['health_change']
                            health_symbol = '❤️ +' if health_change > 0 else '💔 '
                            # print(f"║    {health_symbol}{health_change:<61} ║")
                        if consequences.get('item_changes'):
                            for item in consequences['item_changes']:
                                if item.startswith('add_'):
                                    continue
                                    # print(f"║    📦 Get: {item[4:]:<57} ║")
                                elif item.startswith('remove_'):
                                    continue
                                    # print(f"║    ❌ Lose: {item[7:]:<56} ║")
                    if getattr(choice, 'backtrack', False):
                        continue
                        # print(f"║    🔙 Can backtrack{' '*52} ║")
                    print(f"║{'-'*68}║")
                print(f"╚{'═'*68}╝")
        
                while True:
                    try:
                        choice = int(input(f"\nEnter your choice (1-{len(choices)}): "))
                        if 1 <= choice <= len(choices):
                            chosen_node = choices[choice - 1]
                            if hasattr(chosen_node, 'consequences'):
                                health_change = chosen_node.consequences.get('health_change', 0)
                                if health_change < 0:
                                    print(f"\nYou took {abs(health_change)} damage!")
                                player.health += health_change
                                if player.health <= 0:
                                    player.is_dead = True
                                    player.health = 0
                                    death_reason = chosen_node.story
                                    break

                                for item in chosen_node.consequences.get('item_changes', []):
                                    if item.startswith('add_'):
                                        player.inventory.append(item[4:])
                                        print(f"\nYou obtained: {item[4:]}")
                                    elif item.startswith('remove_'):
                                        if item[7:] in player.inventory:
                                            player.inventory.remove(item[7:])
                                            print(f"\nYou lost: {item[7:]}")
                            
                            player.move(graph, chosen_node)
                            story_state.current_scene = chosen_node.scene_state
                            story_state.characters = chosen_node.characters
                            story_state.visited_nodes.add(chosen_node.id)
                            break
                        else:
                            print(f"Please enter a number between 1 and {len(choices)}")
                    except ValueError:
                        print("Please enter a valid number.")
                
                save_game_state(graph, story_state)
            else:
                print("\nYou've reached the end of this path!")
                break
            
            time.sleep(1)
    
        clear_screen()
        print("\nGame Over!")
        print("=" * 50)
        if player.is_dead:
            print("\nYou have perished in your adventure!")
            print(f"Cause of death: {death_reason}")
            print(f"Final Health: {player.health}")
        elif player.current_node.is_end:
            print("\nCongratulations! You've reached an ending!")
        
        print(f"\nFinal Status:")
        print(f"Health: {player.health}")
        print(f"Experience: {player.experience}")
        print(f"Final Inventory: {', '.join(player.inventory) if player.inventory else 'Empty'}")
            
    except Exception as e:
        print(f"\nError: {e}")
        print("Game initialization failed.")
        return

if __name__ == "__main__":
    main()