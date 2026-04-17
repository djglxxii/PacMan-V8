# Frightened Mode Pauses Global Timer

**Context:** T010 added the first scatter/chase and frightened-mode controller.

**The insight:** Treat frightened mode as an overlay that pauses the
scatter/chase phase countdown. Store the prior scatter/chase mode at
frightened entry, keep the current phase and remaining-frame count unchanged
while frightened frames decrement, and restore the prior mode without issuing
a reversal when frightened expires. This preserves the pending phase boundary
after frightened mode ends.

**Example:**

```text
frame 100: scatter phase 0 has 320 frames remaining
enter frightened: reversal mask = 0x0F, frightened remaining = 360
frame 460: frightened expires, scatter phase 0 still has 320 frames remaining
frame 780: scatter reaches its original boundary and switches to chase
```
