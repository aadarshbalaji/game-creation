import json
import re

def clean_text(text, max_words=25):
    words = re.findall(r'\w+', text)
    return ' '.join(words[:max_words]) + ('...' if len(words) > max_words else '')

def escape_mermaid(text):
    return text.replace('"', "'").replace("\n", " ").replace("<", "").replace(">", "")

def json_to_mermaid(filename, output_file="story_graph.mmd"):
    with open(filename, 'r') as f:
        data = json.load(f)

    nodes = data["graph"]["nodes"]
    edges = data["graph"]["edges"]

    id_to_short = {}
    id_to_label = {}
    class_map = {}

    for i, (node_id, node_data) in enumerate(nodes.items()):
        short_id = f"n{i}"
        story_path = node_data.get("story_path", "Unknown")
        act_key = story_path.split("-")[0].strip().lower()

        story = clean_text(node_data.get("story", ""))
        location = node_data["scene_state"].get("location", "Unknown")
        time = node_data["scene_state"].get("time_of_day", "Unknown")
        mood = node_data["characters"]["player"].get("mood", "Unknown")

        label = f"{story_path} | {story} | {location}, {time} | Mood: {mood}"
        escaped_label = escape_mermaid(label)

        id_to_short[node_id] = short_id
        id_to_label[short_id] = escaped_label
        class_map[short_id] = act_key

    mermaid_lines = ["graph TD"]

    # Add node definitions
    for short_id, label in id_to_label.items():
        mermaid_lines.append(f'    {short_id}["{label}"]')

    # Add edges
    for edge in edges:
        from_id = id_to_short[edge["from"]]
        to_id = id_to_short[edge["to"]]
        arrow = "-->" if not edge.get("backtrack", False) else "-.->"
        mermaid_lines.append(f"    {from_id} {arrow} {to_id}")

    # Add class assignments
    for short_id, cls in class_map.items():
        mermaid_lines.append(f"    class {short_id} {cls}")

    # Add class definitions
    mermaid_lines += [
        "    classDef beginning fill:#ffe4b5,stroke:#333,stroke-width:2px;",
        "    classDef middle fill:#add8e6,stroke:#333,stroke-width:2px;",
        "    classDef late fill:#ffcccb,stroke:#333,stroke-width:2px;",
        "    classDef conclusion fill:#c0f5c1,stroke:#333,stroke-width:2px;",
        "    classDef unknown fill:#eeeeee,stroke:#777,stroke-width:1px;"
    ]

    # Write to file
    with open(output_file, "w") as f:
        f.write("\n".join(mermaid_lines))
    print(f"✅ Mermaid diagram exported to: {output_file}")

# Run it
if __name__ == "__main__":
    json_to_mermaid("star_wars_3_story.json")
