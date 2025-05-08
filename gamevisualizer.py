import json, textwrap, networkx as nx, plotly.graph_objects as go
from collections import defaultdict
from collections import defaultdict
from IPython.display import display

def wrap_text(txt, width=40):
    return "<br>".join(textwrap.wrap(txt, width))

def load_story_json(path):
    with open(path, 'r') as f:
        return json.load(f)
    

def build_story_graph(story_dict):
    """
    Returns:  G (DiGraph), node_attrs {id: {...}}, root
    """
    nodes = story_dict["graph"]
    G          = nx.DiGraph()
    node_attrs = {}

    visited_set = set()
    if "story_state" in story_dict and "visited_nodes" in story_dict["story_state"]:
        visited_set |= {str(n) for n in story_dict["story_state"]["visited_nodes"]}

    for nid, data in nodes.items():
        G.add_node(nid)
        data["__visited"] = data.get("visited", False) or (nid in visited_set)
        node_attrs[nid] = data
        for child in data.get("children", []):
            G.add_edge(nid, child)

    root = "node_0"  
    return G, node_attrs, root


def bfs_layout(G, root="node_0"):
    levels = defaultdict(list)
    for node in nx.bfs_tree(G, root):
        lvl = nx.shortest_path_length(G, root, node)
        levels[lvl].append(node)

    pos = {}
    for lvl, nodes in levels.items():
        for i, n in enumerate(sorted(nodes)):
            y = i - (len(nodes)-1)/2       
            pos[n] = (lvl, y)
    return pos

def natural_key(s):
    # 'node_0_12_3' → ['node_',0,'_',12,'_',3] so numeric parts sort correctly
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]

def flat_tree_layout(G, root="node_0", x_gap=2.0, y_gap=1.4):
    """Return {node: (x,y)} with:
       • x = depth * x_gap
       • y = centred siblings; if a node has one child, child keeps same y
    """
    levels = defaultdict(list)
    for n in nx.bfs_tree(G, root):
        levels[nx.shortest_path_length(G, root, n)].append(n)

    pos = {}
    for depth in sorted(levels):
        level_nodes = sorted(levels[depth], key=natural_key)
        mid = (len(level_nodes) - 1) / 2
        for idx, n in enumerate(level_nodes):
            # inherit y if this edge is part of a chain
            parent = next(iter(G.predecessors(n)), None)
            if parent and len(list(G.successors(parent))) == 1:
                y = pos[parent][1]
            else:
                y = (idx - mid) * y_gap
            pos[n] = (depth * x_gap, y)
    return pos


def format_hover(node):
    """Return a multi-line HTML hover string for a scene node."""
    data = node.copy()                       # shallow copy
    ss   = data.get("scene_state", {})
    chars = data.get("characters", {})
    out   = data.get("outcome", {})

    # header line
    lines = [f"<b>{ss.get('location','Unknown')}</b> "
             f"({ss.get('time_of_day','?')}, {ss.get('weather','?')})"]

    # end-scene tag
    if data.get("is_end"):
        lines.append("<span style='color:#CC0000'><b>END NODE</b></span>")

    # short story preview
    story_preview = wrap_text(data.get("story", ""), width=40)
    lines.append(f"<i>{story_preview}</i>")

    # characters
    if chars:
        lines.append("<b>Characters:</b>")
        for cname, cinfo in chars.items():
            role = cinfo.get("type","")
            mood = cinfo.get("mood","")
            hp   = cinfo.get("health", "?")
            lines.append(f"• {cname} ({role}, {mood}, HP {hp})")

    # outcome
    if out:
        delta = []
        if out.get("health_change"):     delta.append(f"HP {out['health_change']:+}")
        if out.get("experience_change"): delta.append(f"XP {out['experience_change']:+}")
        inv = out.get("inventory_changes", [])
        if inv: delta.append(f"Inv ±{len(inv)}")
        if delta:
            lines.append("<b>Outcome:</b> " + ", ".join(delta))

    return "<br>".join(lines)

def story_fig(G, node_data, pos, highlight=None, title="Interactive Story"):
    highlight = set(str(h) for h in (highlight or []))

    # ---- squares (scenes) ----
    sx, sy, stxt, shover, scol = [], [], [], [], []
    for nid, (x,y) in pos.items():
        sx.append(x);  sy.append(y)
        stxt.append(f"ID: {nid.split('_')[-1]}")
        shover.append(format_hover(node_data[nid]))     # ← new rich hover text

        if nid in highlight:                 colour = "#FF9966"   # orange
        elif node_data[nid].get("__visited"): colour = "#32CD32"   # lime
        else:                                colour = "#A0CBE8"   # blue
        scol.append(colour)

    scene_trace = go.Scatter(
        x=sx, y=sy, mode="markers+text",
        marker=dict(symbol="square", size=22, color=scol),
        text=stxt, textposition="top center",
        hovertext=shover, hoverinfo="text",
        name="Scenes"
    )

    # ---- circles (choice mid-points) ----
    cx, cy, chover = [], [], []
    for u,v in G.edges:
        (x0,y0), (x1,y1) = pos[u], pos[v]
        cx.append((x0+x1)/2);  cy.append((y0+y1)/2)
        chover.append(f"{u} → {v}")

    choice_trace = go.Scatter(
        x=cx, y=cy, mode="markers",
        marker=dict(symbol="circle", size=15, color="#FFDAC1"),
        hovertext=chover, hoverinfo="text",
        name="Choices"
    )

    # ---- arrows ----
    arrows = []
    for u,v in G.edges:
        x0,y0 = pos[u];  x1,y1 = pos[v]
        arrows.append(dict(
            x=x1, y=y1, ax=x0, ay=y0,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowwidth=1,
            arrowsize=1, arrowcolor="black", opacity=.5
        ))

    # ---- figure ----
    fig = go.Figure([scene_trace, choice_trace])
    # legend swatch for visited
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers",
        marker=dict(symbol="square", size=18, color="#32CD32"),
        showlegend=True, name="Visited"
    ))
    fig.update_layout(
        title=title, annotations=arrows,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        hovermode="closest", plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=40,r=40,t=60,b=40)
    )
    fig.update_traces(cliponaxis=False)
    return fig


def visualize_story(story_data, theme):
    """Visualize the story graph with Plotly."""
    G, attrs, root = build_story_graph(story_data)

    attrs[root]['__visited'] = True
    highlight = [root]

    pos_lr = flat_tree_layout(G, root)
    pos = {node: (y, -x) for node, (x, y) in pos_lr.items()}

    fig = story_fig(
        G,
        attrs,
        pos,
        highlight=highlight,
        title=theme
    )
    fig.update_layout(
        width=800,
        height=1000,
        margin=dict(l=50, r=50, t=50, b=50),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
    )
    fig.show()


