# Plex Plugin for Claude Code

Query your Plex media server to find movies and TV shows based on natural language questions.

## Overview

This plugin enables Claude to answer questions about your Plex media library, such as:

- "I want to watch a romantic movie but only have 100 minutes to spend"
- "Give me award-winning movies with 90%+ user score that I haven't seen"
- "Show me all Tom Cruise movies from the 90s on my Plex server"
- "How many unwatched episodes of Always Sunny do I have?"
- "Give me a British comedy show I haven't watched at all"
- "I have 30 minutes, give me shows with episode length under 30 minutes that I've already started"

## Features

- **Movie Search**: Filter by duration, genre, rating, actors, directors, year, and watch status
- **TV Show Search**: Find shows based on episode count, watch progress, genres, and episode duration
- **Boolean Genre Filtering**: Combine genres with OR, AND, and NOT logic for complex queries
  - OR: Find movies/shows matching any of several genres
  - AND: Find content that must have all specified genres
  - NOT: Exclude unwanted genres from results
  - Example: "(comedy OR action) AND british NOT scifi"
- **Watch Status Tracking**: Uses Plex watch history to recommend unwatched content
- **Fuzzy Genre Matching**: Intelligently matches genre requests to your library
- **Comprehensive Metadata**: Returns detailed information to help Claude make informed recommendations

## Prerequisites

- Python 3.8+
- Access to a Plex Media Server
- Plex authentication token

## Installation

1. Install Python dependencies:

   ```bash
   # Option 1: Install from requirements.txt (recommended)
   pip install -r requirements.txt

   # Option 2: Install directly
   pip install plexapi
   ```

   **For development**: The repository includes uv configuration:

   ```bash
   uv venv
   uv pip install -r requirements.txt
   ```

2. Enable the plugin in Claude Code:

   ```bash
   cc --plugin-dir /path/to/skills/plex
   ```

## Configuration

### Required Settings

Set the following environment variables:

```bash
export PLEX_URL="http://your-plex-server:32400"
export PLEX_TOKEN="your-plex-token"
```

**Getting your Plex token**: Follow the [official Plex guide](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/) to find your authentication token.

### Optional Settings

Additional environment variables you can set:

```bash
# Default libraries to search (comma-separated)
export PLEX_DEFAULT_MOVIE_LIBRARIES="Movies,4K Movies"
export PLEX_DEFAULT_TV_LIBRARIES="TV Shows,Documentaries"

# Default result limits
export PLEX_DEFAULT_LIMIT=20

# Cache expiration (in seconds, default 3600 = 1 hour)
export PLEX_CACHE_EXPIRY=3600
```

**Documentation Pattern**: You may want to document your configuration in a `.claude/plex.local.md` file for reference (the scripts don't read this file, but it's useful for documenting your setup):

```markdown
# Plex Configuration Reference

PLEX_URL=http://192.168.1.100:32400
PLEX_TOKEN=your-token-here
PLEX_DEFAULT_MOVIE_LIBRARIES=Movies,4K Movies
PLEX_DEFAULT_TV_LIBRARIES=TV Shows,Documentaries
```

**Note**: Add `.claude/*.local.md` to your `.gitignore` to keep credentials secure.

### Secure Credential Management (Optional)

For enhanced security, use [1Password CLI](https://developer.1password.com/docs/cli/) to inject credentials without storing them in environment variables:

```bash
# Install 1Password CLI
brew install --cask 1password-cli  # macOS
# or download from https://1password.com/downloads/command-line/

# Store credentials in 1Password (one-time setup)
op item create \
  --category=api-credential \
  --title="Plex Token" \
  --vault=Development \
  url="http://localhost:32400" \
  credential="your-plex-token"

# Run scripts with injected credentials
op run --env-file=- -- ./scripts/plex-genres << EOF
PLEX_URL=op://Development/Plex Token/url
PLEX_TOKEN=op://Development/Plex Token/credential
EOF

# Or use inline references
op run -- env \
  PLEX_URL=$(op read "op://Development/Plex Token/url") \
  PLEX_TOKEN=$(op read "op://Development/Plex Token/credential") \
  ./scripts/plex-genres
```

**Note**: This approach keeps credentials out of shell history and environment variables. Standard environment variables work fine for non-sensitive setups.

## Usage

Once configured, simply ask Claude questions about your Plex library:

- "What movies can I watch in under 2 hours?"
- "Find sci-fi movies from the 2010s I haven't seen"
- "Show me all Christopher Nolan films"
- "British comedy shows with unwatched episodes"

Claude will automatically use the Plex tools to search your library and provide recommendations.

## Components

### Skills

- **plex-query**: Teaches Claude how to query your Plex server using the CLI tools

### Scripts

- **plex-movie**: Search and filter movies
- **plex-tv**: Search and filter TV shows
- **plex-genres**: List available genres in your library

## Troubleshooting

**Connection errors**: Verify your `PLEX_URL` and `PLEX_TOKEN` are correct. Test the connection:

```bash
python scripts/plex-movie --help
```

**No results found**: Check that your Plex libraries are correctly configured and accessible. Use `plex-genres` to see available genres.

**Authentication failures**: Ensure your Plex token is valid and has not expired.

## Development

This plugin is part of the lepinkainen-skills collection.

Repository: <https://github.com/lepinkainen/skills>

## License

MIT
