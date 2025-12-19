# Multi-Criteria Search Examples

This file demonstrates how to effectively combine multiple filters for complex queries.

## The Power of Combination

Multi-criteria searches allow precise filtering by combining duration, genre, actors, ratings, year, and watch status. The key is mapping all user requirements to CLI parameters in a single command.

## Example 1: The Perfect Friday Night Movie

**User Query:** "Find me a highly-rated action movie from the 2000s with Tom Cruise that I haven't seen, preferably under 2 hours"

**Criteria Analysis:**
1. Genre: Action
2. Actor: Tom Cruise
3. Decade: 2000s
4. Rating: Highly-rated (8.0+)
5. Duration: Under 2 hours (120 minutes)
6. Watch status: Unwatched

**Command:**
```bash
plex-movie \
  --genre action \
  --actor "Tom Cruise" \
  --decade 2000s \
  --min-rating 8.0 \
  --max-duration 120 \
  --unwatched \
  --limit 10
```

**Expected Results:**
- Mission: Impossible - Ghost Protocol (2011, 133min) - 7.4/10
- Edge of Tomorrow (2014, 113min) - 7.9/10
- Collateral (2004, 120min) - 7.5/10

**Note:** If no results match ALL criteria, consider relaxing duration first (extend to 140 mins), then rating (lower to 7.0), then decade.

## Example 2: Binge-Worthy Crime Drama Discovery

**User Query:** "I want a crime drama from the last 15 years with great reviews that I haven't started, but I don't want a huge commitment - under 30 episodes total"

**Criteria Analysis:**
1. Genre: Crime drama
2. Year range: Last 15 years (2009-2024)
3. Rating: Great reviews (8.5+)
4. Watch status: Unwatched only
5. Episode count: <30 episodes (post-filter)

**Commands:**
```bash
# Query by decade
plex-tv --genre crime --decade 2010s --min-rating 8.5 --unwatched-only --limit 20
plex-tv --genre crime --decade 2020s --min-rating 8.5 --unwatched-only --limit 20
```

**Post-Processing:**
- Combine results from both decades
- Filter to shows with totalEpisodes < 30
- Sort by rating
- Calculate total binge time for each

**Expected Results:**
- Mindhunter (2017, 19 episodes) - 8.6/10
- True Detective S1 (2014, 8 episodes) - 9.0/10
- Mare of Easttown (2021, 7 episodes) - 8.4/10

## Example 3: Director Marathon Planning

**User Query:** "I want to have a Nolan marathon with movies I haven't seen from his recent work, nothing longer than 3 hours"

**Criteria Analysis:**
1. Director: Christopher Nolan
2. Time period: Recent (2010s-2020s)
3. Duration: Max 3 hours (180 minutes)
4. Watch status: Unwatched
5. Goal: Multiple movies for marathon

**Commands:**
```bash
# Get recent Nolan films
plex-movie \
  --director "Christopher Nolan" \
  --decade 2010s \
  --max-duration 180 \
  --unwatched \
  --all

plex-movie \
  --director "Christopher Nolan" \
  --decade 2020s \
  --max-duration 180 \
  --unwatched \
  --all
```

**Post-Processing:**
- Combine results
- Sort chronologically
- Calculate total runtime for marathon
- Suggest viewing order

**Expected Results:**
- Inception (2010, 148min)
- Interstellar (2014, 169min)
- Dunkirk (2017, 106min)
- Tenet (2020, 150min)

**Marathon Note:** Total ~9.5 hours - suggest 2-day marathon or select 2-3 films

## Example 4: Quick Comedy Break

**User Query:** "I need a laugh but only have about an hour - funny movie, good ratings, nothing I've seen"

**Criteria Analysis:**
1. Genre: Comedy
2. Duration: ~60 minutes (max 70 to be safe)
3. Rating: Good (7.0+)
4. Watch status: Unwatched
5. Urgency: Want quick results

**Command:**
```bash
plex-movie \
  --genre comedy \
  --max-duration 70 \
  --min-rating 7.0 \
  --unwatched \
  --limit 5
```

**Presentation Tips:**
- Prioritize shortest films that fit
- Mention exactly how long each is
- Include brief genre descriptors (romantic comedy, dark comedy, etc.)

## Example 5: Award Season Catch-Up

**User Query:** "Show me Oscar-winning movies from the last 10 years that are highly rated and I haven't watched"

**Criteria Analysis:**
1. Awards: Oscar-winning (check ratings/metadata for clues)
2. Time period: Last 10 years (2014-2024)
3. Rating: Highly rated (8.5+)
4. Watch status: Unwatched

**Commands:**
```bash
# Query by decade with high ratings
plex-movie --decade 2010s --min-rating 8.5 --unwatched --limit 30
plex-movie --decade 2020s --min-rating 8.5 --unwatched --limit 30
```

**Post-Processing:**
- Filter to 2014 and later by checking year field
- Look for Oscar indicators in metadata
- Prioritize highest-rated films
- Cross-reference with known Best Picture winners

**Note:** Without explicit Oscar metadata, use high ratings (8.5+) as proxy for award-worthy films

## Example 6: Family Movie Night With Constraints

**User Query:** "Find a family-friendly adventure movie from the 80s or 90s that's well-rated and under 2 hours that my kids haven't seen"

**Criteria Analysis:**
1. Genre: Adventure
2. Decade: 80s or 90s
3. Content rating: Family-friendly (post-filter for PG/G)
4. Rating: Well-rated (7.5+)
5. Duration: Under 2 hours (120 minutes)
6. Watch status: Unwatched

**Commands:**
```bash
# 80s adventure movies
plex-movie \
  --genre adventure \
  --decade 80s \
  --min-rating 7.5 \
  --max-duration 120 \
  --unwatched \
  --limit 15

# 90s adventure movies
plex-movie \
  --genre adventure \
  --decade 90s \
  --min-rating 7.5 \
  --max-duration 120 \
  --unwatched \
  --limit 15
```

**Post-Processing:**
- Combine results from both decades
- Filter to PG or G content ratings
- Remove films too intense for children
- Prioritize classics (Goonies, Hook, etc.)

## Example 7: Mood-Based TV Discovery

**User Query:** "I want a light-hearted show to watch during dinner - episodes around 20 minutes, comedy, something I haven't started yet with good ratings"

**Criteria Analysis:**
1. Genre: Comedy
2. Episode duration: ~20 minutes (22 typical for sitcoms)
3. Tone: Light-hearted (post-filter)
4. Watch status: Unwatched only
5. Rating: Good (7.5+)
6. Use case: Background during dinner

**Command:**
```bash
plex-tv \
  --genre comedy \
  --max-episode-duration 25 \
  --min-rating 7.5 \
  --unwatched-only \
  --limit 15
```

**Presentation Tips:**
- Focus on sitcoms and light comedies
- Avoid dark comedies or dramedies
- Mention episode count (commitment level)
- Suggest starting with pilot episode

## Example 8: Continue or Start Fresh?

**User Query:** "I'm deciding between continuing The West Wing or starting The Crown - both are political dramas I'm interested in. I've watched 2 seasons of West Wing already."

**Criteria Analysis:**
- Need specific show data for both
- Compare watch status, episode counts, ratings
- Consider remaining commitment for each

**Commands:**
```bash
# Check West Wing status
plex-tv --show-title "West Wing" --unwatched-episodes

# Check The Crown status
plex-tv --show-title "Crown" --unwatched-episodes
```

**Analysis Points:**
- West Wing: Already invested, X episodes remaining
- The Crown: Fresh start, Y total episodes
- Compare ratings
- Consider user preference for continuation vs novelty

**Recommendation Framework:**
```
West Wing Progress:
- 2 seasons complete (44 episodes watched)
- 5 seasons remaining (110 episodes, ~82 hours)
- Rating: 8.8/10
- You're past the pilot phase, momentum is good

The Crown:
- 0 seasons watched
- 6 seasons total (60 episodes, ~60 hours)
- Rating: 8.6/10
- Smaller commitment overall

Recommendation: [Based on analysis]
```

## Example 9: Genre Blending

**User Query:** "I want something that's both a sci-fi and a thriller, preferably from the last 20 years with excellent ratings"

**Criteria Analysis:**
1. Genres: Sci-fi AND thriller (may need creative querying)
2. Time period: Last 20 years (2004-2024)
3. Rating: Excellent (8.0+)
4. Watch status: Default unwatched

**Strategy:**
```bash
# Query sci-fi first
plex-movie --genre "sci-fi" --min-rating 8.0 --unwatched --limit 30

# Query thriller
plex-movie --genre thriller --min-rating 8.0 --unwatched --limit 30
```

**Post-Processing:**
- Look for movies appearing in both result sets
- Filter by year ≥ 2004
- Check genre arrays in JSON for dual classification
- Prioritize films with both genre tags

**Expected Results:**
- Ex Machina (2014) - Sci-fi thriller, 7.7/10
- Arrival (2016) - Sci-fi drama/thriller, 7.9/10
- Inception (2010) - Sci-fi thriller, 8.8/10

## Example 10: Actor + Director Collaboration

**User Query:** "What movies directed by Spielberg with Tom Hanks that I haven't seen?"

**Criteria Analysis:**
1. Director: Steven Spielberg
2. Actor: Tom Hanks
3. Watch status: Unwatched
4. Looking for specific collaborations

**Command:**
```bash
plex-movie \
  --director "Spielberg" \
  --actor "Tom Hanks" \
  --unwatched \
  --all
```

**Expected Results:**
- Saving Private Ryan (1998)
- Catch Me If You Can (2002)
- The Terminal (2004)
- Bridge of Spies (2015)

**Presentation:**
- Note this is their complete collaboration filmography
- Mention chronological order for viewing
- Highlight highest-rated if user wants best first

## Tips for Effective Multi-Criteria Searches

### Priority Order for Filters

When multiple criteria are specified, apply in this order for best results:

1. **Media type** (movie vs TV)
2. **Genre** (narrows content type significantly)
3. **People** (actor, director - very specific)
4. **Time period** (decade, year - historical context)
5. **Quality** (ratings - ensures good content)
6. **Duration** (runtime constraints)
7. **Watch status** (discovery vs catch-up)

### When Results Are Empty

If a multi-criteria search returns no results, relax filters in this order:

1. Remove duration constraints (try flexible timing)
2. Reduce rating threshold (7.0 → 6.5)
3. Expand time period (single decade → multiple decades)
4. Try related genres (action → thriller, drama → crime)
5. Simplify people search (exact name → partial name)

### When Too Many Results

If search returns too many options, tighten filters:

1. Increase rating threshold (7.0 → 8.0 → 9.0)
2. Narrow time period (decade → 5-year range → specific year)
3. Add duration constraints if not present
4. Reduce result limit to force prioritization
5. Add watch status filter (all → unwatched)

### Combining Movie and TV Queries

For time-constrained queries ("I have 90 minutes"), query both:

```bash
# Movies under 90 minutes
plex-movie --max-duration 90 --min-rating 7.0 --unwatched

# TV shows with episodes under 90 minutes (for multi-episode viewing)
plex-tv --max-episode-duration 45 --started
```

Present both options, noting movies are complete experiences while TV episodes are part of series.

## Advanced Techniques

### Genre Approximation

If exact genre doesn't match, try related genres:
- Romance → Drama, Comedy
- Horror → Thriller, Mystery
- Western → Action, Drama
- Family → Animation, Adventure

### Rating Source Flexibility

If requesting specific rating source (IMDB, Rotten Tomatoes):
- Use `--min-rating` with appropriate threshold
- Check JSON output for specific rating sources
- Post-filter if multiple rating sources present

### Decade Boundary Handling

For queries spanning decades (late 90s to early 2000s):
```bash
# Get both decades
plex-movie --decade 90s --genre action --min-rating 7.0
plex-movie --decade 2000s --genre action --min-rating 7.0

# Then filter to 1997-2003 in post-processing
```

### Watch Status Nuance

Understand the watch status hierarchy:
- `--unwatched` (movies) / `--unwatched-only` (TV): Never watched
- `--started` (TV only): Partially watched, has unwatched content
- `--completed` (TV only): Fully watched
- `--all`: Everything regardless of status

Use appropriate status for user intent:
- "Find something new" → unwatched-only
- "What should I continue" → started
- "What have I finished" → completed
- "Everything you have" → all
