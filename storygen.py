import json
import os

class StoryState:
    """Class to track the state of the story"""
    def __init__(self, theme="adventure", max_depth=3):
        self.visited_nodes = []
        self.current_scene = ""
        self.characters = {}
        self.theme = theme
        self.max_depth = max_depth

    def to_dict(self):
        """Convert state to dictionary for saving"""
        return {
            "visited_nodes": self.visited_nodes,
            "current_scene": self.current_scene,
            "characters": self.characters,
            "theme": self.theme,
            "max_depth": self.max_depth
        }

    @classmethod
    def from_dict(cls, data):
        """Create state from dictionary"""
        state = cls()
        state.visited_nodes = data.get("visited_nodes", [])
        state.current_scene = data.get("current_scene", "")
        state.characters = data.get("characters", {})
        state.theme = data.get("theme", "adventure")
        state.max_depth = data.get("max_depth", 3)
        return state

def enrich_scene(story_state):
    """Generate a reaction to the current scene"""
    # This is a simple version that just returns a generic reaction
    # In a more complex implementation, this would call an AI model
    
    scene_text = story_state.current_scene
    
    # Simple reactions based on scene content
    if "danger" in scene_text.lower() or "threat" in scene_text.lower():
        return "You feel a sense of unease as you assess the situation, looking for potential exits and advantages."
    
    if "discover" in scene_text.lower() or "find" in scene_text.lower():
        return "You examine your discovery carefully, looking for any clues or useful information."
    
    if "person" in scene_text.lower() or "character" in scene_text.lower() or "people" in scene_text.lower():
        return "You attempt to read their intentions, staying alert for any sign of hostility or deception."
    
    # Default reaction
    return "You take a moment to process what you're seeing, considering your next move carefully."