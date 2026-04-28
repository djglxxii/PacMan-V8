#!/usr/bin/env python3
"""T025 per-frame PLAYING tick — energizer route (minimal)."""

from __future__ import annotations
import hashlib, re, struct, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROM = REPO / "build" / "pacman.rom"
EVIDENCE = REPO / "tests" / "evidence" / "T025-per-frame-playing-tick"
HEADLESS = REPO.parent / "Vanguard8" / "cmake-build-debug" / "src" / "vanguard8_headless"

MASKS = {"up": 0x80, "down": 0x40, "left": 0x20, "right": 0x10}
DIRS = {0: "UP", 1: "LEFT", 2: "DOWN", 3: "RIGHT", 4: "NONE"}
STATES = {0: "ATTR", 1: "READY", 2: "PLAY", 3: "DYING", 4: "LVLC", 5: "CONT", 6: "NLEV", 7: "INTR"}


def build():
    r = subprocess.run([sys.executable, str(REPO / "tools" / "build.py")],
                       capture_output=True, text=True, cwd=str(REPO))
    if r.returncode != 0:
        print(f"BUILD FAILED:\n{r.stderr}", file=sys.stderr)
        sys.exit(1)


def button(btns):
    s = 0xFF
    for b in btns:
        if b in MASKS:
            s &= ~MASKS[b]
    return s


def write_replay(path, rhash, frames):
    data = bytearray(b"V8RR")
    data.extend(struct.pack("<B", 1))
    data.extend(rhash)
    data.extend(struct.pack("<B", 0))
    data.extend(struct.pack("<I", len(frames)))
    for i, c in enumerate(frames):
        data.extend(struct.pack("<IBB", i, c, 0xFF))
    path.write_bytes(bytes(data))


def peek(frame, replay):
    cmd = [str(HEADLESS), "--rom", str(ROM), "--replay", str(replay),
           "--frames", str(frame),
           "--peek-logical", "0x8100:7",
           "--peek-logical", "0x8120:3",
           "--peek-logical", "0x81FE:2",
           "--peek-logical", "0x8202:1",
           "--peek-logical", "0x8250:2"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return None
    result = {}
    for line in r.stdout.splitlines():
        m = re.match(r"^\s*(0x[0-9A-Fa-f]+):\s+([0-9A-Fa-f\s]+)$", line.strip())
        if m:
            addr = int(m.group(1), 16)
            result[addr] = [int(b, 16) for b in m.group(2).strip().split()]
    return result


def pac_tile(pac):
    return (pac[1] >> 3, pac[3] >> 3)


def fmt_row(f, pac, blk, pel, stall, state, full=True):
    pt = pac_tile(pac)
    p_tile = f"({pt[0]:2d},{pt[1]:2d})"
    cdir = DIRS.get(pac[4], "?")
    req = DIRS.get(pac[5], "?")
    pc = pel[0] | (pel[1] << 8)
    st_s = STATES.get(state, "??")
    if full:
        b_tile = f"({blk[0]:2d},{blk[1]:2d})"
        bdir = DIRS.get(blk[2], "?")
        return (f"  {f:5d} {st_s:>4s} "
                f"{p_tile:>9s} {cdir:>5s} {req:>5s} "
                f"{b_tile:>9s} {bdir:>5s} "
                f"{pc:5d} {stall:5d}")
    else:
        return (f"  {f:5d} {st_s:>4s} "
                f"{p_tile:>9s} {cdir:>5s}     - "
                f"{'':>9s}     - "
                f"{pc:5d} {stall:5d}")


def main():
    build()
    rhash = hashlib.sha256(ROM.read_bytes()).digest()

    NEUT = button([])
    RIGHT = button(["right"])
    UP = button(["up"])
    DOWN = button(["down"])

    # Route plan:
    # 0-399 NEUT  — drift LEFT to wall at (4,26), stop at (5,26) centre
    # 400-499 RIGHT — reverse, ride row 26 right to (21,26)
    # 500-799 UP    — buffered early, turn UP at (21,26), ride column 21
    #                 all the way up to row 4 (stops at blocked (21,3))
    # 800-829 RIGHT — turn RIGHT at (21,4), ride row 4 right
    # 830-999 DOWN  — buffered, tried at cols 22-25 (fails, (X,5) empty),
    #                 succeeds at (26,4)→(26,5)→(26,6) ENERGIZER
    frames_list = [NEUT] * 400
    frames_list += [RIGHT] * 100
    frames_list += [UP] * 300
    frames_list += [RIGHT] * 30
    frames_list += [DOWN] * 170
    total_frames = len(frames_list)

    with tempfile.TemporaryDirectory(prefix="t025-") as td:
        replay = Path(td) / "test.v8r"
        write_replay(replay, rhash, frames_list)
        EVIDENCE.mkdir(parents=True, exist_ok=True)

        lines = []
        lines.append("# T025 PLAYING Tick Trace — energizer route")
        lines.append("# Route: NEUT 0-399, RIGHT 400-499, UP 500-799, RIGHT 800-829, DOWN 830-999")
        lines.append("# Target: energizer at (26,26)")
        lines.append("#")
        header = (f"{'frame':>5s} {'st':>4s} "
                  f"{'pac_tile':>9s} {'cdir':>5s} {'req':>5s} "
                  f"{'blinky':>9s} {'bdir':>5s} "
                  f"{'pellets':>7s} {'stall':>5s}")
        lines.append(f"# {header}")
        lines.append(f"# {'-' * 84}")

        # ---- Phase 1: broad survey (11 probes) ----
        probes = [300, 380, 400, 500, 600, 700, 800, 830, 860, 890, 920, 950, 999]
        survey = {}
        energizer_probe = None
        for f in probes:
            p = peek(f, replay)
            if p:
                survey[f] = p
                if p.get(0x8202, [0])[0] >= 2 and energizer_probe is None:
                    energizer_probe = f

        # Print survey
        lines.append("# --- Broad survey ---")
        prev_pc = None
        for f in probes:
            p = survey.get(f)
            if p is None:
                continue
            pac = p.get(0x8100, [0] * 7)
            blk = p.get(0x8120, [0] * 3)
            pel = p.get(0x81FE, [0, 0])
            stall = p.get(0x8202, [0])[0]
            state = p.get(0x8250, [99])[0]
            pc = pel[0] | (pel[1] << 8)
            notes = ""
            if stall >= 3:
                notes = "*** ENERGIZER! ***"
            elif prev_pc is not None and pc < prev_pc:
                notes = f"ate {prev_pc - pc} pellet(s)"
            lines.append(fmt_row(f, pac, blk, pel, stall, state)
                         + (f"  {notes}" if notes else ""))
            prev_pc = pc

        # ---- Phase 2: find exact energizer frame ----
        energizer_frame = None
        if energizer_probe is not None:
            # Walk backward from probe to find first stall frame
            for f in range(energizer_probe, max(energizer_probe - 15, 0), -1):
                p = peek(f, replay)
                if p and p.get(0x8202, [0])[0] == 0:
                    break  # f was the pre-stall frame
            # f+1 is the first frame with stall
            energizer_frame = f + 1
        else:
            # Scan DOWN segment
            for f in range(830, min(999, total_frames), 8):
                p = peek(f, replay)
                if p and p.get(0x8202, [0])[0] >= 3:
                    energizer_frame = f
                    break
            if energizer_frame is not None:
                for f in range(energizer_frame, max(energizer_frame - 15, 0), -1):
                    p = peek(f, replay)
                    if p and p.get(0x8202, [0])[0] == 0:
                        break
                energizer_frame = f + 1

        # ---- Phase 3: dense energizer scan ----
        if energizer_frame is not None:
            ef = energizer_frame
            d_start = max(ef - 2, 0)
            d_end = min(ef + 6, total_frames)
            lines.append("#")
            lines.append(f"# --- Dense: energizer pickup ~frame {ef} ---")
            for f in range(d_start, d_end):
                p = peek(f, replay)
                if p is None:
                    continue
                pac = p.get(0x8100, [0] * 7)
                pel = p.get(0x81FE, [0, 0])
                stall = p.get(0x8202, [0])[0]
                state = p.get(0x8250, [99])[0]
                marker = ""
                if stall > 0:
                    marker = f" <-- DOT_STALL={stall}"
                elif f > ef:
                    marker = " <-- resumed"
                lines.append(fmt_row(f, pac, [0] * 3, pel, stall, state, False) + marker)

            # Stall sequence
            stall_seq = []
            for f in range(ef, min(ef + 6, total_frames)):
                p = peek(f, replay)
                if p:
                    stall_seq.append(str(p.get(0x8202, [0])[0]))
            lines.append(f"# Energizer stall sequence: {stall_seq}")

            # Pellet delta
            p_pre = peek(ef - 1, replay)
            p_post = peek(ef, replay)
            if p_pre and p_post:
                pc_pre = (p_pre.get(0x81FE, [0, 0])[0]
                          | (p_pre.get(0x81FE, [0, 0])[1] << 8))
                pc_post = (p_post.get(0x81FE, [0, 0])[0]
                           | (p_post.get(0x81FE, [0, 0])[1] << 8))
                lines.append(f"# Pellet count decreased: {pc_pre} -> {pc_post} "
                             f"(delta={pc_pre - pc_post})")
        else:
            lines.append("#")
            lines.append("# *** FAIL: No energizer detected ***")

        # ---- Summary ----
        lines.append("#")
        lines.append("# --- Summary ---")
        pac_tiles = set()
        for f, p in survey.items():
            pt = pac_tile(p.get(0x8100, [0] * 7))
            pac_tiles.add(pt)
        lines.append(f"# Pac-Man tiles: {sorted(pac_tiles)}")
        lines.append(f"# {'PASS' if len(pac_tiles) >= 3 else 'FAIL'}: moved >= 3 tiles")
        lines.append(f"# Energizer: {'YES' if energizer_frame is not None else 'NO'}")

        # Frame dumps
        for label, fnum in [("f0300", 300), ("fplay", 380), ("f0800", 800)]:
            cmd = [str(HEADLESS), "--rom", str(ROM), "--replay", str(replay),
                   "--frames", str(fnum),
                   "--dump-frame", str(EVIDENCE / f"tick_frame_{label}.ppm")]
            subprocess.run(cmd, capture_output=True)

        trace = EVIDENCE / "tick_trace.txt"
        trace.write_text("\n".join(lines) + "\n")
        for line in lines:
            print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
