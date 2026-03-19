# Insights 

These insights are intended to be **actionable** for Level Designers. 

> Note: Run `scripts/generate_insights.py` to regenerate the numbers/figures from local dataset, then paste the outputs below.

---

## Insight 1 — Player traffic is extremely concentrated (large parts of maps go under-used)
### What caught my eye
Movement heatmaps quickly “burn in” along a few corridors/lanes, while big regions stay cold even across 5 days.

### Evidence (pattern / stat)
From `scripts/generate_insights.py` (all files, traffic = `Position` + `BotPosition`):
- **AmbroseValley**: only **35.2%** of 100×100 bins are touched; **top 5%** of bins contain **53.5%** of all traffic
- **GrandRift**: only **20.0%** of bins touched; **top 5%** contains **57.7%** of traffic
- **Lockdown**: only **22.9%** of bins touched; **top 5%** contains **59.2%** of traffic

### Actionable? What to do + what metrics it affects
- **Action**: make at least 1–2 “cold” regions valuable and safe-to-reach:
  - add meaningful loot/objectives
  - add traversal affordances (cover, zipline/shortcut, sightline breaks) to reduce perceived risk
  - tune storm push direction/pacing so optimal rotations aren’t always the same lanes
  - Run periodic **in-game events** tied to cold regions to temporarily draw players there and diversify traffic patterns
  - Use **controlled bot presence** in cold regions to create early engagement and reduce perceived emptiness, while ensuring they don’t become low-risk farming zones
- **Expected metric impact**:
  - **Area utilization** (bins touched) increases
  - **Traffic concentration** (top-5% share) decreases
  - **Time-to-first-contact** may increase slightly (healthier pacing) and **kill distribution** becomes less clustered
  - **Average travel distance** per player increases slightly
  - **Mid-game player count** increases (less early clustering leads to more players surviving into later phases)
  - **Third-party encounter** rate decreases(fewer stacked fights in the same location

**Why this matters for Level Designer**
  Right now, fights and rotations are concentrated in a few lanes, leaving large parts of the map underutilized. Fixing this increases encounter variety, reduces predictability, and makes    more of the map worth engaging with

---

## Insight 2 — Bots significantly skew movement patterns (must be separated by default)

It’s easy to misread traffic heatmaps as “player preference” when a substantial fraction is bot navigation.A large portion of movement data comes from bots, which can make heatmaps look like player preference when they’re actually reflecting AI behavior

### Evidence (pattern / stat)
Across the entire dataset:
- **Human `Position` rows**: **51,347**
- **Bot `BotPosition` rows**: **21,712**
- **Bot share of movement samples**: **29.7%**

### Actionable? What to do + what metrics it affects
- **Action**:
  - default the tool to **separate** human and bot layers (or provide 1-click toggles), so designers can answer “what do humans do?” vs “where do bots patrol?”
  - use bot-only views to evaluate **spawn and patrol design** (are bots accidentally funneling humans into the same lanes?)
  - Correlate **bot density** with **encounter rates**. Check if bot-heavy zones artificially inflate combat frequency or third-party fights.
  - Run **A/B-style analysis** (bot density vs human routing). If possible, compare matches with varying bot presence to see how much bots actually influence rotations.
  - Use bots intentionally as design levers (controlled manner).Instead of letting bots distort data, place them deliberately to guide players into underutilized areas.
- **Expected metric impact**:
  - Better decisions on **AI placement** and **patrol lanes**
  - More accurate interpretation of **player behaviour** (reduced false positives from bot paths)
  - Potential changes in **encounter rate** and perceived fairness
  - Reduced **misleading signals** in heatmaps (fewer false conclusions about player flow)
  - Better control over early vs mid-game **combat density**.
  - Potential improvement in perceived **map liveliness**.
  - More balanced region-wise encounter distribution. 

### Why a Level Designer should care
Bots can make up a large share of movement data. If they aren’t separated, heatmaps can reflect AI behavior instead of real player choices, leading to layout changes that optimize for bots rather than actual players.

---

## Insight 3 — Storm has low lethality (~5% of deaths), so it may not strongly influence player movement
### What stood out
Storm has low lethality (~5% of deaths), so it may not strongly influence player movement

### Evidence (pattern / stat)
Across the entire dataset:
- **Storm deaths** (`KilledByStorm`): **39**
- **All deaths** (`Killed`, `BotKilled`, `KilledByStorm`): **742**
- **Storm share of deaths**: **5.3%**

### Actionable? What to do + what metrics it affects
- **Action** :
  - If the storm should strongly shape movement: increase pressure (damage, speed, visibility) or tighten timing to force rotations.
  - If the storm is meant to be soft guidance: keep lethality low, but ensure it still influences rotations (validate via movement patterns, not deaths).
  - Add environmental friction in storm zones. Movement slowdowns, reduced visibility, or terrain penalties so being in the storm feels bad even without killing players.
  - Make storm pressure uneven (directional bias).Instead of uniform shrink, bias the storm so certain regions become temporarily unsafe, forcing varied rotations instead of                    predictable paths.
  - Introduce “safe-but-costly” rotations. Add longer but safer routes vs shorter high-risk ones, so players make trade-offs instead of always optimizing the same lane.
  - Measure “storm compliance rate. Percentage or amount of players who rotate before taking damage vs those who tank the storm. This tells you if the storm is respected or ignored.
    
- **Expected metric impact**:
  - Increased storm-driven rotations without spike in deaths.
  - Potential rise in storm deaths (if pressure is increased).
  - Reduced late-game clustering (if players are forced to move earlier).
  - Higher rotation diversity if storm meaningfully disrupts fixed paths(less repeated paths).
  - Clear visibility into player response behavior (early vs late movers).

### Why this matters for Level Design
The storm is one of the main tools for controlling pacing and player movement. If it isn’t having a noticeable impact, rotations are driven mostly by player habits, which tend to converge into a few predictable routes and leave large parts of the map underused.

