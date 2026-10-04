# Demo video

Two parts: a 75-second cut built from code, then about 60 seconds of the voice assistant recorded live.

```bash
CANDOR_PLAYWRIGHT_PYTHON=/path/to/python-with-playwright docs/video/build.sh ~/Movies/voice-clip.mov
# -> ~/Movies/candor-demo.mp4
```

## Part 1: the cut (docs/video/)

Made with the `/brag` skill (its `brag-slim` variant). `brag-plan.md` has the angle and the storyboard. `index.html` draws every frame as a pure function of time. `render.py` captures the 2,250 frames with headless Chromium. `music.py` synthesizes an original soundtrack (A minor, 92 BPM, music and effects in one key). `build.sh` mixes the soundtrack, bakes the poster in as frame 0 and appends the voice clip. Every record, answer and number on screen is real Candor data or output.

| Time | Scene | Shows |
|---|---|---|
| 0 to 7 | Hook | "When is the launch?" Three real messages that disagree (Sep 30, Oct 14, Oct 21) |
| 7 to 14 | Reveal | Candor, and what it remembers: 889 meeting segments, 230 Slack messages, 58 emails… |
| 14 to 32 | Time travel | An as-of playhead over Sep 8 to Sep 18: September 30, then October 14, then October 21, with source ids; later records dim as "not written yet" |
| 32 to 44 | Who said what | Dana's second-hand report against John's first-hand decision on dark mode |
| 44 to 57 | What it won't say | "I don't know" (Dana's salary), the planted instruction ignored (Acme not signed), the pasted key redacted and gone after deletion |
| 57 to 68 | Actions | The reminder lands at 8:00, not the 7:30 run-through; the delete asks for confirmation |
| 68 to 75 | Proof | 96% retrieval, 100% answers (rules), 89% (LLM judge), 12/12 actions, ₹0; then "Now, live" |

## Part 2: the voice clip (about 60 seconds)

1. Terminal: font 18 pt or larger, one window, `cd ~/code/candor`.
2. Run `make voice` once and allow microphone access when macOS asks; Ctrl-D.
3. QuickTime Player, then File, then New Screen Recording. In Options choose the MacBook microphone. Record the terminal window.
4. `make voice`. For each line: press Enter, speak, press Enter, and wait for the spoken reply.
   - "What's our launch date again?" It answers October 21 with sources, out loud.
   - "Delete all my emails from Marcus." It asks "Are you sure?" Say "Yes": recorded, nothing deleted.
   - Optional: "Message Sarah on Slack that the geocoding fix looks good", then "Yes": a dry run.
5. Ctrl-D, stop recording, save as `~/Movies/voice-clip.mov`, run the command at the top.

Upload `~/Movies/candor-demo.mp4` to YouTube (unlisted) or Google Drive (anyone with the link) and put the link in the reply email.
