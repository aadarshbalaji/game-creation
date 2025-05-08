# Netflix Games Choose Your Own Adventure Game

An interactive text-based adventure game that generates unique stories based on user input themes using Google Gemini. The game creates rich narratives with branching paths, character interactions, and consequences for player choices. Available in both CLI and web interface versions (web version currently in beta).

## Features

- 🎮 **Multiple Interfaces**
  - Command-line interface (CLI) version (Recommended)
  - Web-based interface with Flask (Beta)
  - Rich text formatting and emoji support

- 📖 **Dynamic Story Generation**
  - AI-powered story creation using Google Gemini
  - Unique narratives for each playthrough
  - Branching story paths based on choices
  - Character relationship system
  - Health and inventory management

- 🎯 **Game Elements**
  - Health bars with hearts (♥)
  - Experience points with stars (✦)
  - Character moods with emojis
  - Formatted text boxes
  - Scene information with icons
  - Save/load functionality

## Setup

### Prerequisites
- Python 3.7+
- Google Gemini API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd game-creation
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your Google API key:
   - Create a `keys.env` file in the root directory
   - Add your API key: `GOOGLE_API_KEY=your-api-key-here`

### Running the Game

#### CLI Version (Recommended)
```bash
python3 game_clean.py
```

#### Web Version (Beta)
```bash
cd web_ui
python3 app.py
```
Then open your browser to `http://localhost:5000`

> **Note:** The web version is currently in beta and will have limited functionality compared to the CLI version.

## Project Structure

### Core Components

#### CLI Version
- `game_clean.py` - Main game loop and CLI interface
- `storygen.py` - Story generation using Gemini AI
- `arc.py` - Story arc management and progression
- `Graph_Classes/` - Core game mechanics classes

#### Web Version
- `web_ui/app.py` - Flask web application
- `web_ui/webarc.py` - Web-specific story arc handling
- `web_ui/templates/` - HTML templates
- `web_ui/static/` - CSS, JavaScript, and static assets

## Gameplay

1. Start the game (CLI or web version)
2. Enter your name
3. Choose a story theme (e.g., "Star Wars", "Dracula", "Fantasy")
4. Navigate through the story by selecting choices
5. Manage health and inventory
6. Reach different endings based on choices

## Save System

The game automatically saves progress after each choice. Progress is automatically loaded when returning to a previous session (beta).
