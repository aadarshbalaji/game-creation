import json
import re

def clean_and_parse_json(text):
    """
    Clean up and parse JSON from potentially messy AI output
    Returns parsed JSON or None if parsing fails
    """
    try:
        # First try direct parsing
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Clean up obvious issues
    cleaned = text
    
    # Remove any markdown code block markers
    cleaned = cleaned.replace('```json', '').replace('```', '')
    
    # Extract just the JSON portion between first { and last }
    try:
        start_idx = cleaned.find('{')
        end_idx = cleaned.rfind('}') + 1
        if start_idx >= 0 and end_idx > 0:
            cleaned = cleaned[start_idx:end_idx]
    except:
        pass
    
    # Fix missing quotes around keys
    cleaned = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', cleaned)
    
    # Fix single quotes to double quotes (but not within already-valid strings)
    # This is tricky because we need to track if we're within a string
    in_string = False
    escape_next = False
    result = []
    
    for char in cleaned:
        if escape_next:
            result.append(char)
            escape_next = False
            continue
            
        if char == '\\':
            result.append(char)
            escape_next = True
            continue
            
        if char == '"':
            in_string = not in_string
            
        if char == "'" and not in_string:
            char = '"'
            
        result.append(char)
    
    cleaned = ''.join(result)
    
    # Fix trailing commas before closing brackets
    cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
    
    # Fix missing quotes around string values
    cleaned = re.sub(r':\s*([a-zA-Z][a-zA-Z0-9_]*)\s*([,}])', r': "\1"\2', cleaned)
    
    # Final attempt to parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Last attempted clean version: {cleaned[:100]}...")
        return None 