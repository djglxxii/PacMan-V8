# Headless Runtime Dump Version Skew

**Context:** T007 needed a PPM frame capture from the Vanguard 8 headless
emulator to verify the VDP-B maze framebuffer in the actual runtime.

**The insight:** The two local headless binaries are not equivalent. The
`cmake-build-debug` binary can run `--hash-frame`, but its `--dump-frame`
output behaved like a fixed fixture and did not respond to ROM changes. The
`build` binary advertises `--dump-fixture` separately and has a runtime dump
path, but it aborted on an unsupported timed Z180 opcode while running the
T007 ROM. Do not treat a PPM from `cmake-build-debug --dump-frame` as runtime
evidence unless its output labels the source as runtime or changes with ROM
content.

**Example:** For T007, this command failed before producing runtime evidence:

```bash
/home/djglxxii/src/Vanguard8/build/src/vanguard8_headless --rom build/pacman.rom --frames 60 --dump-frame tests/evidence/T007-vdp-b-maze-render/frame_060.ppm --hash-frame 60
```

The first failure was:

```text
Unsupported timed Z180 opcode 0x1 at PC 0x1FD
```

After an emulator retry, the same runtime-dump path progressed farther but
still aborted in the VDP-B VRAM seek helper:

```text
Unsupported timed Z180 opcode 0x79 at PC 0x23B
```

A second retry after another patch report still failed on the same opcode and
PC. Check the actual binary timestamp as well as the emulator source status
before assuming the runtime dump path has changed.

After the timed path was implemented farther, the ROM progressed to the next
register-transfer instruction in the same helper and failed on:

```text
Unsupported timed Z180 opcode 0x78 at PC 0x23E
```

After that opcode was covered, the same helper progressed to the immediate OR
used to set the VDP write-address control bit:

```text
Unsupported timed Z180 opcode 0xF6 at PC 0x241
```

Once `0xF6` was covered, the runtime reached an earlier setup instruction in
the framebuffer load routine:

```text
Unsupported timed Z180 opcode 0x11 at PC 0x20B
```

After `0x11` was covered, the copy loop reached another register-transfer
instruction:

```text
Unsupported timed Z180 opcode 0x7A at PC 0x246
```

After `0x7A` was covered, the next unsupported instruction was the register OR
used to test whether the byte counter has reached zero:

```text
Unsupported timed Z180 opcode 0xB3 at PC 0x247
```

After `0xB3` was covered, the next unsupported instruction was the conditional
return that exits the copy loop when the counter is zero:

```text
Unsupported timed Z180 opcode 0xC8 at PC 0x248
```

A static audit of the T007 ROM also predicted the copy-loop decrement would be
next:

```text
0x1B at PC 0x24D ; DEC DE
```

Once both `0xC8` and `0x1B` were implemented in the emulator timed path, the
runtime dump completed. Treat this output as the positive signal that the PPM
came from the live compositor rather than the fixture path:

```text
Frame dump source: runtime
Frame dump size: 256x212
```

For T007, the runtime PPM was byte-identical to the accepted generated preview,
which made the VDP-B upload easy to verify:

```bash
cmp -s tests/evidence/T006-maze-tile-re-authoring/maze_v8_preview.ppm \
  tests/evidence/T007-vdp-b-maze-render/frame_060.ppm
```
