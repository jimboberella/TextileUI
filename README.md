# TextileUI

A modern web interface for the [Fabric](https://github.com/danielmiessler/fabric) tool, providing a polished desktop experience for running AI patterns, managing presets, and exporting results.

## Features

- **Pattern Browsing** — Browse, search, and favorite patterns from your Fabric configuration
- **Multi-Source Input** — Enter text directly, load from file paths, URLs, or YouTube videos
- **Model Selection** — Choose from available models, set temperature, top-p, and other parameters
- **Pattern Variables** — Dynamic variable inputs based on selected pattern
- **Presets** — Save and quickly apply commonly-used configuration combinations
- **Favorites** — Mark patterns as favorites for quick access
- **Output Export** — Copy to clipboard, save to file, or save directly to Obsidian vaults
- **Modern UI** — Clean dark theme with Inter typography and SVG icons

## Project Structure

```
fabric-web/
├── app.py                 # Flask backend server
├── config/
│   └── settings.json      # User settings (favorites, presets, vault paths)
└── templates/
    └── index.html         # Frontend interface
```

## Prerequisites

- Python 3.8+
- [Fabric](https://github.com/danielmiessler/fabric) CLI tool installed and configured
- Flask (installed via requirements)

## Installation

1. Clone or navigate to the project directory:
   ```bash
   cd fabric-web
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Launch the server:
   ```bash
   python app.py
   ```

4. Open your browser to `http://localhost:5050`

## Usage

### Running a Pattern

1. Select a pattern from the sidebar
2. Enter your input (text, file path, URL, or YouTube link)
3. Optionally adjust model, temperature, and other settings
4. Fill in any pattern-specific variables
5. Click **Run Pattern**

### Saving Presets

Presets let you save a combination of pattern + model + parameters for quick reuse:

1. Select a pattern and configure your settings
2. Click the **+** button in the Presets section
3. Name your preset and click **Save**
4. Click a preset name to apply its settings

### Managing Favorites

- Click the star icon next to any pattern to mark it as a favorite
- Switch to the **Favorites** view to see only favorited patterns

### Exporting Output

After running a pattern, you can:

- **Copy** — Copy the output to your clipboard
- **File** — Save the output to a file on your filesystem
- **Obsidian** — Save the output as a markdown note in your Obsidian vault

### Obsidian Integration

The first time you save to Obsidian, enter your vault path. Subsequent saves remember your last-used vault and folder location.

## Configuration

Settings are stored in `config/settings.json` and include:

| Key | Description |
|-----|-------------|
| `default_model` | Default model to use when none selected |
| `default_temperature` | Default temperature (0–2) |
| `default_topp` | Default top-p value (0–1) |
| `default_presence_penalty` | Default presence penalty |
| `default_frequency_penalty` | Default frequency penalty |
| `favorites` | Array of favorited pattern names |
| `presets` | Array of saved preset objects |
| `obsidian_vault_path` | Default Obsidian vault location |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main interface |
| GET | `/api/patterns` | List all patterns |
| GET | `/api/patterns/<name>/info` | Get pattern details and variables |
| GET | `/api/patterns/<name>/summary` | Get pattern summary |
| GET | `/api/models` | List available models |
| GET | `/api/contexts` | List available contexts |
| GET | `/api/favorites` | Get favorited patterns |
| POST | `/api/favorites` | Update favorites |
| GET | `/api/presets` | Get saved presets |
| POST | `/api/presets` | Save a preset |
| DELETE | `/api/presets/<id>` | Delete a preset |
| POST | `/api/run` | Run a pattern |
| POST | `/api/read-file` | Read file contents |
| POST | `/api/save-file` | Save output to file |
| POST | `/api/save-obsidian` | Save to Obsidian vault |
| GET | `/api/obsidian-config` | Get Obsidian config |
| POST | `/api/obsidian-config` | Update Obsidian config |

## Customization

The interface uses CSS custom properties (variables) for theming. Edit the `:root` block in `templates/index.html` to customize colors:

```css
:root {
  --bg: #0d1117;       /* Main background */
  --bg2: #161b22;      /* Panel backgrounds */
  --bg3: #21262d;      /* Interactive elements */
  --border: #30363d;   /* Border color */
  --text: #e6edf3;     /* Primary text */
  --text2: #8b949e;    /* Secondary text */
  --accent: #58a6ff;   /* Accent / action color */
  --green: #3fb950;    /* Success / positive */
  --red: #f85149;      /* Error / danger */
  --orange: #d29922;   /* Warning / favorites */
}
```

## License

MIT
