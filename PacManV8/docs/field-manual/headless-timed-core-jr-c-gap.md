# Headless Timed Core JR C Gap

**Context:** T019 added level-progression cache code that ran during boot,
then the headless emulator aborted before the first frame.

**The insight:** The Vanguard 8 headless timed core currently aborts on Z80
opcode `0x38` (`JR C,d`) when it appears on an executed path. Existing source
files already contain carry-conditional branches in gameplay routines that are
not reached during the current boot review path, so this may surface later as
more runtime gameplay is wired in. When the branch is only defensive or
unimportant to the active path, prefer a simple non-carry branch sequence; when
carry branching is essential, report it as an emulator opcode blocker with the
PC and command that reproduced it.

**Example:** The first failing T019 run used:

```text
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless --rom build/pacman.rom --frames 960 --hash-frame 960
Unsupported timed Z180 opcode 0x38 at PC 0x900
```

`PC=0x0900` was inside `level_progression_update_current_cache`, at a
defensive `JR C` used to clamp invalid level zero. Replacing that defensive
carry branch with explicit zero/equality checks kept the active behavior the
same and let the runtime complete the 960-frame review.
