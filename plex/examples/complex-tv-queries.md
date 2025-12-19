# Complex TV Show Query Examples

This file contains advanced examples of TV show queries, including episode-level filtering and watch status tracking.

## Continued Viewing Discovery

**User Query:** "I have 30 minutes, give me all the shows with episode length under 30 minutes that I've already started but haven't finished"

**Analysis:**
- Episode duration: Under 30 minutes
- Watch status: Started (>0 episodes watched AND has unwatched episodes)
- Time constraint: Can watch one episode now

**Command:**
```bash
plex-tv --max-episode-duration 30 --started
```

**Result Interpretation:**
- Filter to shows with short episodes
- Only shows with watch progress >0% and <100%
- Return shows sorted by most recently watched or highest rated
- Present with: title, unwatched episode count, next episode details

## Binge-Worthy Discovery

**User Query:** "Find me a British comedy show I haven't watched at all (0 episodes seen)"

**Analysis:**
- Genre: British comedy (may need two genre filters)
- Watch status: Unwatched only (0 episodes seen)
- Intent: Start a new series

**Command:**
```bash
plex-tv --genre british --genre comedy --unwatched-only --limit 10
```

**Alternative if single genre only:**
```bash
# Try British first
plex-tv --genre british --unwatched-only

# Or comedy first
plex-tv --genre comedy --unwatched-only
```

**Post-Processing:**
- If tool doesn't support multiple genres, filter results manually
- Look for keywords like "British", "BBC", "UK" in descriptions
- Prioritize shows with high ratings

## Episode Count Tracking

**User Query:** "How many unwatched episodes of It's Always Sunny in Philadelphia do I have?"

**Analysis:**
- Specific show: "It's Always Sunny in Philadelphia"
- Need episode-level data
- Want unwatched count

**Command:**
```bash
plex-tv --show-title "Always Sunny" --unwatched-episodes
```

**Expected Output:**
```json
{
  "title": "It's Always Sunny in Philadelphia",
  "totalEpisodes": 170,
  "watchedEpisodes": 120,
  "unwatchedEpisodes": 50,
  "unwatchedEpisodesList": [
    {"season": 9, "episode": 1, "title": "...", "duration": 22},
    {"season": 9, "episode": 2, "title": "...", "duration": 22},
    ...
  ]
}
```

**Presentation:**
- "You have 50 unwatched episodes of It's Always Sunny"
- "You've watched through Season 8, next up is Season 9 Episode 1"
- Total remaining watch time if needed

## Quick Watch Options

**User Query:** "I have 45 minutes before bed, what can I watch?"

**Analysis:**
- Time constraint: 45 minutes
- Could be a movie OR a TV episode
- Prefer unwatched content
- Want good quality

**Combined Approach:**
```bash
# Check for movies
plex-movie --max-duration 45 --min-rating 7.0 --unwatched --limit 5

# Check for TV episodes from started shows
plex-tv --max-episode-duration 45 --started --limit 5

# Check for TV pilots/first episodes
plex-tv --max-episode-duration 45 --unwatched-only --limit 5
```

**Presentation:**
- Present both movie and TV options
- Prioritize shows user has started (continuity)
- Mention new shows if user wants something fresh

## Genre-Specific Binge Planning

**User Query:** "Show me all sci-fi shows from the 2010s that I haven't finished"

**Analysis:**
- Genre: Sci-fi
- Decade: 2010s
- Watch status: Started OR unwatched (exclude completed)
- Use --all but filter out completed in post-processing

**Command:**
```bash
plex-tv --genre "sci-fi" --decade 2010s --all --limit 50
```

**Post-Processing:**
- Filter out shows with watchProgress = 100%
- Sort by unwatched episode count (most content first)
- Include shows user started (priority) and unwatched shows
- Present with episode counts and descriptions

## Limited Series Discovery

**User Query:** "What British dramas can I finish in one weekend?"

**Analysis:**
- Genre: British drama
- Episode count: Limited series (probably <20 episodes total)
- Watch status: Unwatched or partially watched
- Time available: ~12-16 hours of viewing

**Command:**
```bash
plex-tv --genre drama --genre british --all --limit 30
```

**Post-Processing:**
- Filter to shows with totalEpisodes < 20
- Calculate total runtime (episodes × duration)
- Filter to shows with <16 hours total runtime
- Prioritize unwatched shows
- Present with total episode count and estimated binge time

## Show Similarity Search

**User Query:** "I loved Breaking Bad, what other crime dramas should I watch?"

**Analysis:**
- Genre: Crime drama
- Quality: High-rated (Breaking Bad quality = 9.0+)
- Watch status: Unwatched
- Similar themes: Dark, serialized

**Command:**
```bash
plex-tv --genre crime --min-rating 8.5 --unwatched-only --limit 15
```

**Alternative:**
```bash
plex-tv --genre drama --min-rating 8.5 --unwatched-only --limit 15
```

**Presentation:**
- Filter to crime/drama shows
- Highlight similar shows (The Wire, Better Call Saul, Ozark)
- Mention why each is similar (tone, themes, quality)
- Note episode commitment (total episodes, seasons)

## Actor Tracking Across Shows

**User Query:** "What shows on my Plex have Bryan Cranston that I haven't watched?"

**Analysis:**
- Actor: Bryan Cranston
- Watch status: Unwatched only
- Want complete list

**Command:**
```bash
plex-tv --actor "Bryan Cranston" --unwatched-only --limit 20
```

**Presentation:**
- List all shows featuring the actor
- Note their role if available in metadata
- Highlight most popular/highest rated shows first
- Mention episode commitment for each

## Catch-Up Planning

**User Query:** "Which shows do I have the most unwatched episodes for?"

**Analysis:**
- Need all shows with unwatched episodes
- Sort by unwatched episode count (descending)
- Include shows user has started

**Command:**
```bash
plex-tv --started --limit 100
```

**Post-Processing:**
- Parse unwatchedEpisodes count for each show
- Sort by unwatched count (most to least)
- Calculate total watch time for catch-up
- Present top 10 shows with biggest backlogs

**Presentation:**
```
Shows with the most unwatched episodes:
1. The Office - 87 unwatched episodes (~29 hours)
2. Friends - 64 unwatched episodes (~21 hours)
3. ...
```

## New Show Commitment Planning

**User Query:** "Show me highly-rated shows I haven't started with less than 30 episodes total"

**Analysis:**
- Watch status: Unwatched only
- Episode count: Limited commitment (<30 episodes)
- Quality: High-rated (8.0+)

**Command:**
```bash
plex-tv --unwatched-only --min-rating 8.0 --limit 50
```

**Post-Processing:**
- Filter to totalEpisodes < 30
- Calculate total binge time
- Sort by rating
- Present as manageable commitments

**Presentation:**
```
Highly-rated limited series to start:
- Chernobyl (5 episodes, ~5 hours) - 9.4/10
- The Queen's Gambit (7 episodes, ~7 hours) - 8.6/10
- ...
```

## Continue vs Start New

**User Query:** "Should I continue The Wire or start The Sopranos?"

**Analysis:**
- Compare two specific shows
- Need watch status for both
- Need episode counts, ratings

**Commands:**
```bash
# Check The Wire
plex-tv --show-title "The Wire" --unwatched-episodes

# Check The Sopranos
plex-tv --show-title "Sopranos" --unwatched-episodes
```

**Presentation:**
- Show watch progress for The Wire
- Show total commitment for The Sopranos
- Compare ratings, episode counts
- Provide recommendation based on:
  - How far into The Wire they are
  - Total time commitment remaining for each
  - Ratings and user preferences

## Episode Duration Optimization

**User Query:** "I workout for 40 minutes, what shows have episodes around 40 minutes?"

**Analysis:**
- Episode duration: ~40 minutes (35-45 range)
- Watch status: Mix of started and unwatched
- Want variety of options

**Command:**
```bash
# Started shows first (continuity)
plex-tv --max-episode-duration 45 --started --limit 10

# New shows if needed
plex-tv --max-episode-duration 45 --unwatched-only --limit 10
```

**Post-Processing:**
- Filter to episodes between 35-45 minutes
- Calculate if episode fits workout time
- Present mix of shows to continue and new shows

## Decade-Specific Nostalgia

**User Query:** "What 90s sitcoms are on my Plex that I haven't watched?"

**Analysis:**
- Genre: Sitcom (comedy)
- Decade: 1990s
- Watch status: Unwatched

**Command:**
```bash
plex-tv --genre sitcom --decade 90s --unwatched-only --limit 20
```

**Alternative:**
```bash
plex-tv --genre comedy --decade 90s --unwatched-only --limit 20
```

**Presentation:**
- List classic 90s sitcoms
- Note episode counts (sitcoms can have 100+ episodes)
- Highlight most popular/influential shows
- Suggest starting with pilots

## Completion Status Overview

**User Query:** "What shows have I completely finished?"

**Analysis:**
- Watch status: Completed (100% watched)
- Want comprehensive list
- Maybe for rating/review purposes

**Command:**
```bash
plex-tv --completed --limit 200
```

**Presentation:**
- List all completed shows
- Sort by completion date (most recent first) if available
- Include ratings and episode counts
- Useful for "what should I rewatch" or "what did I think of this"
