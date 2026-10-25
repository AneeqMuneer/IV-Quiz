#!/usr/bin/env python3
"""
Generate one Urdu MP3 per question for the IV Quiz practice page.

Setup (once):
    pip install edge-tts mutagen imageio-ffmpeg
    (imageio-ffmpeg bundles ffmpeg, so you don't need to install ffmpeg yourself.
     If ffmpeg is already on your PATH, that one is used instead.)

Run (needs internet):
    python generate_audio.py --force

Output:  audio/q1.mp3 ... audio/q275.mp3   (put the 'audio' folder next to index.html)

What it does for each question
  1. Speaks the Urdu parts with an Urdu neural voice and the English names/terms with an
     English voice (one short clip per piece).
  2. Joins the pieces and REMOVES the silences: leading/trailing silence is cut and any pause longer than --max-pause (default 0.15s) is cut down to about that length. This is what removes the
     long breaks between pieces.
  3. Speeds the result up (or slows it a little) with a pitch-preserving tempo change so it
     lasts about --target seconds, within --min-speed / --max-speed.

Useful options
    python generate_audio.py --only 1-20            # try a few first
    python generate_audio.py --force                # overwrite existing files
    python generate_audio.py --target 4.5           # shorter questions
    python generate_audio.py --target 0             # no tempo change, only silence removal
    python generate_audio.py --max-pause 0.1        # even tighter (may sound rushed)
    python generate_audio.py --max-pause 0.25       # looser, more natural pauses
    python generate_audio.py --single-voice         # one voice for everything (no switching)
    python generate_audio.py --voice-ur ur-PK-AsadNeural          # male Urdu voice

Note: edge-tts uses Microsoft's online "read aloud" service without an API key. It is an
unofficial client, so availability is not guaranteed. Fine for a one-off practice tool.
"""
import argparse
import asyncio
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import edge_tts
from mutagen.mp3 import MP3

# Same rule the web page uses: runs of Latin letters/digits are "English", the rest is Urdu.
TOK = r"[A-Za-z0-9$\u00C0-\u017F(][A-Za-z0-9$\u00C0-\u017F'\u2019\u2018\"()&/%\-.,:+\u2013\u2014]*"
RX = re.compile(TOK + r"(?: " + TOK + r")*")
QUOTES = "'\u2018\u2019\""
KEEP = {"FOCUS", "LEED", "SOAS", "STEP"}  # acronyms that are read as words, not spelled out


def find_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ffmpeg not found. Run:  pip install imageio-ffmpeg   (or install ffmpeg yourself)")


def spell_acronyms(s: str) -> str:
    return re.sub(r"\b[A-Z]{2,6}\b", lambda m: m.group(0) if m.group(0) in KEEP else " ".join(m.group(0)), s)


def segments(text: str, single_voice: bool):
    """Split Urdu text into [(text, is_english)] pieces."""
    out, last = [], 0

    def push(s: str, en: bool):
        s = s.strip(QUOTES + " ") if en else re.sub("[" + QUOTES + "]", " ", s)
        if en:
            s = spell_acronyms(s)
        # keep only pieces that contain real letters/digits; a lone "،" or "؟" makes the voice
        # service answer "No audio was received"
        if any(ch.isalnum() for ch in s):
            out.append((s.strip(), en and not single_voice))

    for m in RX.finditer(text):
        if m.start() > last:
            push(text[last:m.start()], False)
        push(m.group(0).rstrip(",:."), True)
        last = m.end()
    if last < len(text):
        push(text[last:], False)
    return out


async def synth(text: str, voice: str) -> bytes:
    buf = bytearray()
    async for chunk in edge_tts.Communicate(text, voice).stream():
        if chunk["type"] == "audio":
            buf += chunk["data"]
    if not buf:
        raise RuntimeError("no audio returned")
    return bytes(buf)


def duration(path_or_bytes) -> float:
    src = io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, (bytes, bytearray)) else str(path_or_bytes)
    return MP3(src).info.length


def run_ffmpeg(ffmpeg: str, args: list):
    r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + r.stderr.strip()[:300])


def tighten_and_fit(parts, args, ffmpeg: str):
    """Join clips, remove silences, then fit to the target length. Returns (mp3_bytes, seconds, info)."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        inputs = []
        for i, b in enumerate(parts):
            p = d / f"s{i}.mp3"
            p.write_bytes(b)
            inputs += ["-i", str(p)]
        n = len(parts)
        raw_len = sum(duration(b) for b in parts)

        sil = (f"silenceremove=start_periods=1:start_silence=0.02:start_threshold={args.threshold}dB"
               f":stop_periods=-1:stop_duration={args.max_pause}:stop_silence=0"
               f":stop_threshold={args.threshold}dB")
        chain = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1,{sil}[a]"
        tight = d / "tight.mp3"
        run_ffmpeg(ffmpeg, [*inputs, "-filter_complex", chain, "-map", "[a]",
                            "-ar", "24000", "-ac", "1", "-b:a", "48k", str(tight)])
        tight_len = duration(tight)

        speed = 1.0
        if args.target and args.target > 0:
            speed = max(args.min_speed, min(args.max_speed, tight_len / args.target))
        if abs(speed - 1.0) < 0.04:
            speed = 1.0
        if speed != 1.0:
            fit = d / "fit.mp3"
            run_ffmpeg(ffmpeg, ["-i", str(tight), "-filter:a", f"atempo={speed:.3f}",
                                "-ar", "24000", "-ac", "1", "-b:a", "48k", str(fit)])
            final = fit
        else:
            final = tight
        data = final.read_bytes()
        return data, duration(final), f"{raw_len:.1f}s raw -> {tight_len:.1f}s trimmed, x{speed:.2f}"


async def make_question(q, args, sem, ffmpeg):
    path = Path(args.out) / f"q{q['id']}.mp3"
    if path.exists() and not args.force:
        return q["id"], None, "skipped"
    segs = segments(q["question"]["ur"], args.single_voice)
    if not segs:
        return q["id"], None, "empty"
    async with sem:
        for attempt in range(1, 4):
            try:
                parts = [await synth(t, args.voice_en if en else args.voice_ur) for t, en in segs]
                data, secs, info = await asyncio.to_thread(tighten_and_fit, parts, args, ffmpeg)
                path.write_bytes(data)
                return q["id"], secs, info
            except Exception as e:  # network hiccup: retry
                if attempt == 3:
                    return q["id"], None, f"FAILED: {e}"
                await asyncio.sleep(2 * attempt)


def parse_only(s):
    if not s:
        return None
    a, _, b = s.partition("-")
    return int(a), int(b or a)


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", default="questions_en_ur.json")
    ap.add_argument("--out", default="audio")
    ap.add_argument("--voice-ur", default="ur-PK-UzmaNeural")
    ap.add_argument("--voice-en", default="en-US-AriaNeural")
    ap.add_argument("--single-voice", action="store_true")
    ap.add_argument("--target", type=float, default=5.0, help="target seconds per question (0 = don't change speed)")
    ap.add_argument("--min-speed", type=float, default=0.85, help="slowest allowed (1.0 = normal)")
    ap.add_argument("--max-speed", type=float, default=1.6, help="fastest allowed")
    ap.add_argument("--max-pause", type=float, default=0.15, help="longest pause allowed (s); longer silences are cut down to this")
    ap.add_argument("--threshold", type=int, default=-45, help="silence level in dB")
    ap.add_argument("--only", help="question range, e.g. 1-20")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args()

    ffmpeg = find_ffmpeg()
    data = json.loads(Path(args.json).read_text(encoding="utf-8"))["questions"]
    rng = parse_only(args.only)
    if rng:
        data = [q for q in data if rng[0] <= q["id"] <= rng[1]]
    Path(args.out).mkdir(exist_ok=True)

    sem = asyncio.Semaphore(args.concurrency)
    tasks = [asyncio.create_task(make_question(q, args, sem, ffmpeg)) for q in data]
    durs, failed = [], []
    for i, t in enumerate(asyncio.as_completed(tasks), 1):
        qid, d, note = await t
        if d:
            durs.append(d)
        if note.startswith("FAILED"):
            failed.append(qid)
        print(f"[{i}/{len(tasks)}] Q{qid}: {note}" + (f"  => {d:.1f}s" if d else ""))
    if durs:
        print(f"\nDone. Average length: {sum(durs)/len(durs):.2f}s over {len(durs)} files "
              f"(min {min(durs):.1f}s, max {max(durs):.1f}s).")
    if failed:
        print("Failed (just re-run the script to retry):", sorted(failed))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())