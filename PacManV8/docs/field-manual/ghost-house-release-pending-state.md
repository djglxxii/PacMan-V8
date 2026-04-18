# Ghost House Release Pending State

**Context:** T012 needed ghost-house dot counters before any sprite or
tile-by-tile door movement exists.

**The insight:** Keep release eligibility separate from exit motion. A ghost
whose dot counter or fallback timer fires should enter `PENDING_RELEASE`; a
later movement slice can explicitly begin `EXITING` and then mark the ghost
`OUTSIDE`. This preserves release order without pretending the door path has
already been implemented.

**Example:** T012 initializes Pinky as pending because the level-start
threshold is zero, but `GHOST_HOUSE_NEXT_GHOST` remains Pinky until a later
caller invokes `ghost_house_begin_next_exit` and `ghost_house_complete_exit`.
Inky and Clyde counters do not advance while Pinky is pending or exiting.
