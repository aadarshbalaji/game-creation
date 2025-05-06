import re
import json
import traceback

def clean_and_parse_json(raw_text):
    """
    Robustly clean and parse JSON from AI text responses.
    This handles various formats and common JSON errors.
    """
    # Keep a copy of the original text for debugging
    original_text = raw_text
    
    try:
        # 1. Remove code blocks
        raw_text = raw_text.strip()
        raw_text = re.sub(r"^```[a-zA-Z]*", "", raw_text)
        raw_text = raw_text.replace("```", "")
        
        # 2. Find JSON boundaries
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        
        if start == -1 or end == -1:
            print(f"[AI RAW RESPONSE]: {repr(original_text)}")
            
            # Fallback: Try to construct valid JSON
            return {
                "story": "You continue your journey, cautiously observing your surroundings.",
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
                            "name": "Guide",
                            "description": "A helpful character",
                            "relationship": "neutral"
                        }
                    ]
                },
                "choices": [
                    {
                        "text": "Continue cautiously forward",
                        "dialogue": "You press on, determined to see what lies ahead.",
                        "consequences": {"health_change": 0, "item_changes": []}
                    },
                    {
                        "text": "Take a different approach",
                        "dialogue": "You decide to try something new, hoping for a better outcome.",
                        "consequences": {"health_change": 0, "item_changes": []}
                    },
                    {
                        "text": "Try something unexpected",
                        "dialogue": "You act on impulse, surprising even yourself.",
                        "consequences": {"health_change": 0, "item_changes": []}
                    },
                    {
                        "text": "Pause and reflect",
                        "dialogue": "You take a moment to consider your options.",
                        "consequences": {"health_change": 0, "item_changes": []}
                    }
                ]
            }
        
        # Extract JSON string
        json_str = raw_text[start:end+1]
        
        # 3. Fix common JSON syntax errors
        # Remove trailing commas
        json_str = re.sub(r",\s*([}}\]])", r"\1", json_str)
        
        # Fix unquoted property names
        json_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_str)
        
        # Fix single quotes to double quotes (carefully)
        in_string = False
        result = []
        for i, char in enumerate(json_str):
            if char == '"':
                # Check if this quote is escaped
                if i > 0 and json_str[i-1] == '\\':
                    # Count backslashes before this quote
                    backslash_count = 0
                    j = i - 1
                    while j >= 0 and json_str[j] == '\\':
                        backslash_count += 1
                        j -= 1
                    # If odd number of backslashes, the quote is escaped
                    if backslash_count % 2 == 1:
                        result.append(char)
                        continue
                in_string = not in_string
            elif char == "'" and not in_string:
                result.append('"')
                continue
            result.append(char)
        json_str = ''.join(result)
        
        # 4. Parse JSON
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as initial_error:
            print(f"[INITIAL JSON ERROR]: {initial_error}")
            print(f"[CLEANED JSON]: {json_str}")
            
            # Final attempt: use a more forgiving JSON parser or reconstruct a valid JSON
            # Here, we'll just provide a fallback
            return {
                "story": "As your adventure continues, you find yourself facing new challenges.",
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
                            "name": "Guide",
                            "description": "A helpful character",
                            "relationship": "neutral"
                        }
                    ]
                },
                "choices": [
                    {
                        "text": "Continue cautiously forward",
                        "dialogue": "You press on, determined to see what lies ahead.",
                        "consequences": {"health_change": 0, "item_changes": []}
                    },
                    {
                        "text": "Take a different approach",
                        "dialogue": "You decide to try something new, hoping for a better outcome.",
                        "consequences": {"health_change": 0, "item_changes": []}
                    },
                    {
                        "text": "Try something unexpected",
                        "dialogue": "You act on impulse, surprising even yourself.",
                        "consequences": {"health_change": 0, "item_changes": []}
                    },
                    {
                        "text": "Pause and reflect",
                        "dialogue": "You take a moment to consider your options.",
                        "consequences": {"health_change": 0, "item_changes": []}
                    }
                ]
            }
    except Exception as e:
        print(f"[FATAL JSON PARSING ERROR]: {e}")
        print(traceback.format_exc())
        # Last resort fallback
        return {
            "story": "Your journey continues despite unexpected circumstances.",
            "scene_state": {
                "location": "unknown",
                "time_of_day": "unknown",
                "weather": "unknown",
                "ambient": "mysterious"
            },
            "characters": {
                "player": {
                    "health": 100,
                    "mood": "determined",
                    "status_effects": []
                },
                "others": []
            },
            "choices": [
                {
                    "text": "Continue forward",
                    "dialogue": "You must press on.",
                    "consequences": {"health_change": 0, "item_changes": []}
                },
                {
                    "text": "Take a different path",
                    "dialogue": "Perhaps another way will be better.",
                    "consequences": {"health_change": 0, "item_changes": []}
                },
                {
                    "text": "Look for help",
                    "dialogue": "You need assistance to proceed.",
                    "consequences": {"health_change": 0, "item_changes": []}
                },
                {
                    "text": "Rest and recover",
                    "dialogue": "A moment to gather your strength.",
                    "consequences": {"health_change": 0, "item_changes": []}
                }
            ]
        } 