# Register Clobbering Across Call Boundaries

**Context:** T025 (Per-frame PLAYING tick) — debugging why `requested_dir` cycled
through UP→LEFT→DOWN→RIGHT despite correct input.

**The insight:** When a function uses a register as scratch and the caller depends
on that register's value surviving the call, the corruption can be silent and
symptomatically distant. The caller's stale register value gets consumed later,
producing wrong behavior that looks like an I/O or emulator bug.

In this case, `movement_distance_to_next_center_px` used B as a scratch register
(`ld b, a` in `.positive_before_center`, `.horizontal_right`, `.vertical_down`).
The caller `movement_request_direction` stores the input direction in B and
expects it to survive across `call movement_distance_to_next_center_px`. After the
call returned with B corrupted, `.accept` did `ld a, b` and stored the garbage
value (the pixel offset) as `requested_dir`.

**Example:**
```asm
; Before (broken):
movement_request_direction:
    ld b, a                    ; B = input direction (must survive)
    ...
.window_check:
    call movement_distance_to_next_center_px   ; clobbers B!
    cp 5
    jr c, .accept
    ret
.accept:
    ld a, b                    ; B is now pixel offset, not direction
    ld (PACMAN_REQUESTED_DIR), a

; After (fixed):
.window_check:
    push bc                    ; save direction in B (and C alongside)
    call movement_distance_to_next_center_px
    pop bc                     ; restore B; pop does not touch A, so distance is preserved
    cp 5
    jr c, .accept
    ret
```

**Pitfall:** an earlier attempt at this fix did `ld c, a / pop bc / ld a, c` —
intending to stash the distance in C, restore B from the stack, then recover the
distance. But `pop bc` overwrites C with the *original* C from the stack, so
`ld a, c` reads stale data. T021 silently regressed because the perpendicular
turn window was being checked against an arbitrary register value instead of the
real distance. Lesson: when stashing a result around a `pop`, use a register
the pop won't touch (A is the natural choice — `pop bc/de/hl/af` all leave A
unaffected unless you pop AF).

**How to apply:** When a function call doesn't behave as expected, check
whether any callee modifies registers the caller depends on. Z80 has few
registers; B/C/D/E are commonly used as scratch. If a caller stores a value
in any of these across a `call`, verify the callee (and all its transitive
callees) preserves it. `push/pop` around the call is the safest fix.
