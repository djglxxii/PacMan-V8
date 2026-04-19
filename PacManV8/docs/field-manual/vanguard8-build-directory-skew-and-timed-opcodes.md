# Vanguard8 Build Directory Skew and Timed Opcode Gaps

**Context:** T016 added a VBlank-driven AY-3-8910 PSG update path to the
PacManV8 ROM. The ROM runs successfully under one local Vanguard8 headless
binary but aborts under another local Vanguard8 headless binary when the
Pac-Man ROM reaches the interrupt handler.

**The insight:** There are two independent CMake build directories for the same
`/home/djglxxii/src/Vanguard8` source checkout:

```text
/home/djglxxii/src/Vanguard8/build
/home/djglxxii/src/Vanguard8/cmake-build-debug
```

These are not two emulator projects. They are two separate build products from
the same source tree, and rebuilding one does not update the other.

Observed local state on 2026-04-19:

```text
/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless
  built Apr 16, size 892 KB
  CMake generator: Unix Makefiles
  CMAKE_BUILD_TYPE: empty

/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless
  built Mar 28, size 4.5 MB
  CMake generator: Ninja
  CMAKE_BUILD_TYPE: Debug
  Ninja path comes from JetBrains/CLion tooling
```

The PacManV8 project documentation and prior task evidence mostly used:

```bash
/home/djglxxii/src/Vanguard8/cmake-build-debug/src/vanguard8_headless
```

That binary successfully runs the T016 ROM for 180 frames and produces the
expected audio hash:

```text
Audio SHA-256: a8d5a5c921628a88b12a4b95e1294af3ddd79620bd940b0702300098af341483
```

The newer-looking `build` binary fails:

```bash
/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless \
  --rom /home/djglxxii/src/PacManV8/build/pacman.rom \
  --frames 180 --hash-audio
```

Failure:

```text
Unsupported timed Z180 opcode 0xC5 at PC 0x39
```

This is not a PacManV8 ROM bug. Opcode `0xC5` is standard Z80 `PUSH BC`.
The failing binary's timed CPU execution path is missing support for an
ordinary stack instruction that the current PacManV8 VBlank handler uses.

The relevant ROM bytes at the interrupt handler are:

```text
0038: F5        PUSH AF
0039: C5        PUSH BC   ; confirmed missing in build/src/vanguard8_headless
003A: D5        PUSH DE   ; likely next timed-path gap
003B: E5        PUSH HL   ; likely next timed-path gap
003C: DB 81     IN A,(0x81)
003E: CD .. ..  CALL audio_update_frame
0040: E1        POP HL    ; likely next timed-path gap
0041: D1        POP DE    ; likely next timed-path gap
0042: C1        POP BC    ; likely next timed-path gap
0043: F1        POP AF
0044: FB        EI
0045: ED 4D     RETI
```

The handler widened register preservation around `audio_update_frame`, so the
ROM now exercises more stack opcodes during timed interrupt execution.

**Recommendation:** Fix this in the Vanguard8 emulator, not in PacManV8.

1. Pick one canonical Vanguard8 build directory. Prefer one documented path
   for PacManV8 verification and remove or ignore stale alternatives.
2. Reconfigure and rebuild that canonical directory from current Vanguard8
   source.
3. Patch the Vanguard8 timed Z180 opcode dispatcher to support the stack
   register opcodes used by the current PacManV8 interrupt path.
4. Add emulator-side tests for the full `PUSH/POP rr` family, not only the
   first failing opcode, to avoid one-opcode-at-a-time repair loops.
5. After the emulator patch, rerun the PacManV8 T016 command against the
   canonical binary and update PacManV8 docs if the canonical path changes.

Minimum confirmed opcode to add:

```text
0xC5  PUSH BC  confirmed missing at PC 0x0039
```

Strongly recommended same-pass coverage:

```text
0xD5  PUSH DE  likely next in the same handler at PC 0x003A
0xE5  PUSH HL  likely next in the same handler at PC 0x003B
0xE1  POP HL   likely next in the same handler at PC 0x0040
0xD1  POP DE   likely next in the same handler at PC 0x0041
0xC1  POP BC   likely next in the same handler at PC 0x0042
```

Also verify the already-used stack opcodes remain covered:

```text
0xF5  PUSH AF
0xF1  POP AF
```

Recommended PacManV8 regression command after the emulator fix:

```bash
cd /home/djglxxii/src/PacManV8
python3 tools/build.py
/path/to/canonical/vanguard8_headless \
  --rom build/pacman.rom \
  --frames 180 \
  --hash-audio \
  --expect-audio-hash a8d5a5c921628a88b12a4b95e1294af3ddd79620bd940b0702300098af341483
```

Expected result:

```text
Frames completed: 180
Audio SHA-256: a8d5a5c921628a88b12a4b95e1294af3ddd79620bd940b0702300098af341483
```

