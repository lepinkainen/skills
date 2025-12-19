# Complex Movie Query Examples

This file contains advanced examples of movie queries that combine multiple criteria.

## Time-Constrained Award Winners

**User Query:** "I want to watch an award-winning movie with 90%+ user score that I haven't seen before, but I only have 2 hours"

**Analysis:**
- Duration constraint: 2 hours = 120 minutes
- Rating requirement: 90%+ = 9.0+ on 10-point scale
- Watch status: Unwatched (default)

**Command:**
```bash
plex-movie --max-duration 120 --min-rating 9.0 --unwatched
```

**Result Interpretation:**
- Filter to movies rated 9.0 or higher
- Ensure runtime is under 120 minutes
- Only show unwatched content
- Present top results with ratings, duration, and synopsis

## Director-Specific Era

**User Query:** "Show me all Christopher Nolan films from the 2010s"

**Analysis:**
- Director: Christopher Nolan
- Time period: 2010s decade
- No watch status filter (use --all to see everything)

**Command:**
```bash
plex-movie --director "Christopher Nolan" --decade 2010s --all
```

**Alternative using year range:**
```bash
# Note: If decade doesn't work, query each year
for year in {2010..2019}; do
  plex-movie --director "Christopher Nolan" --year $year --all
done
```

## Multi-Genre Filtering

**User Query:** "Find me a sci-fi action movie with good ratings that I haven't seen"

**Analysis:**
- Genres: sci-fi AND action (note: some tools may only support one genre at a time)
- Rating: "good" = moderate threshold, 7.0+
- Watch status: Unwatched

**Command:**
```bash
# First try sci-fi, then filter results by action
plex-movie --genre "sci-fi" --min-rating 7.0 --unwatched

# Or try action genre with sci-fi
plex-movie --genre action --min-rating 7.0 --unwatched
```

**Note:** If the tool doesn't support multiple genres in one query, try each genre separately and look for overlap in results, or use the broader genre that's more important to the user.

## Actor Pairing

**User Query:** "Movies with both Leonardo DiCaprio and Tom Hanks"

**Analysis:**
- Multiple actors: Need to query once and check results for both

**Command:**
```bash
# Query for first actor
plex-movie --actor "Leonardo DiCaprio" --all

# Then manually check results for Tom Hanks in the actor list
# Or query for second actor and cross-reference
plex-movie --actor "Tom Hanks" --all
```

**Result Processing:**
- Execute both queries
- Find movies that appear in both result sets
- "Catch Me If You Can" should appear in both lists

## Hidden Gems Discovery

**User Query:** "Show me highly-rated movies from the 80s that I haven't watched"

**Analysis:**
- Time period: 1980s
- Rating: High (8.0+)
- Watch status: Unwatched
- Goal: Discovery, so maybe increase limit

**Command:**
```bash
plex-movie --decade 80s --min-rating 8.0 --unwatched --limit 30
```

**Presentation Tips:**
- Sort by rating (highest first)
- Include genre diversity in recommendations
- Mention why each is highly rated (awards, critical acclaim)

## Family Movie Night

**User Query:** "Find me a family-friendly comedy under 90 minutes"

**Analysis:**
- Genre: Comedy
- Duration: Under 90 minutes
- Content rating: Need to check rating field (PG, PG-13)
- Note: Content rating might not be a CLI parameter, so filter after results

**Command:**
```bash
plex-movie --genre comedy --max-duration 90 --unwatched
```

**Post-Processing:**
- Check the JSON results for `contentRating` field
- Filter to PG or G ratings manually
- Present family-appropriate options

## Recent Additions

**User Query:** "What highly-rated movies were added to my Plex recently?"

**Analysis:**
- Recency: Use `addedAt` field in results
- Rating: High quality (8.0+)
- Watch status: Probably unwatched

**Command:**
```bash
plex-movie --min-rating 8.0 --unwatched --limit 50
```

**Post-Processing:**
- Parse `addedAt` timestamp from JSON results
- Sort by most recent additions
- Present top 10 newest highly-rated movies

## Actor Filmography Review

**User Query:** "Show me all Meryl Streep movies I haven't watched yet"

**Analysis:**
- Actor: Meryl Streep
- Watch status: Unwatched
- Likely want comprehensive list

**Command:**
```bash
plex-movie --actor "Meryl Streep" --unwatched --limit 100
```

**Presentation:**
- Group by decade or genre
- Highlight award winners or highest rated
- Suggest viewing order (chronological or by rating)

## Mood-Based Discovery

**User Query:** "I'm in the mood for a dark thriller from the 90s or 2000s, nothing too long"

**Analysis:**
- Genre: Thriller (dark suggests certain sub-genres)
- Time period: 1990-2009
- Duration: "Not too long" = assume under 120 minutes
- Watch status: Default unwatched

**Command:**
```bash
# Try 90s first
plex-movie --genre thriller --decade 90s --max-duration 120 --unwatched

# Then 2000s
plex-movie --genre thriller --decade 2000s --max-duration 120 --unwatched
```

**Presentation:**
- Combine results from both decades
- Filter to darker themes by checking summary/description
- Prioritize films known for dark tone (Se7en, Zodiac, etc.)

## Rating Source Comparison

**User Query:** "Movies with high IMDB ratings but that I haven't seen"

**Analysis:**
- Rating source: IMDB (tool uses best available, may be IMDB)
- Rating threshold: High = 8.0+
- Watch status: Unwatched

**Command:**
```bash
plex-movie --min-rating 8.0 --unwatched --limit 30
```

**Note:** The tool returns all available ratings in JSON. Check the `ratings` field to specifically filter by IMDB ratings post-query if multiple sources are present.

## Marathon Planning

**User Query:** "Give me three 2-hour action movies for a Saturday marathon"

**Analysis:**
- Genre: Action
- Duration: ~120 minutes each
- Quantity: 3 movies
- Watch status: Probably unwatched or mix

**Command:**
```bash
# Get candidates
plex-movie --genre action --max-duration 130 --min-rating 7.0 --limit 10
```

**Post-Processing:**
- Filter to movies close to 120 minutes
- Select top 3 by rating
- Calculate total runtime (should be ~6 hours)
- Present in suggested viewing order
