# Demo video

The video is built by a script, so it can be re-rendered exactly. Only the live voice clip is recorded by hand.

```bash
brew install vhs                                   # scripted terminal recorder (once)
docs/video/build.sh ~/Movies/voice-clip.mov        # writes ~/Movies/candor-demo.mp4
```

`docs/video/build.sh` renders each terminal segment in `docs/video/tapes/` with vhs (1920x1080), narrates it from `docs/video/narration.txt` with macOS `say`, fits each segment to its narration, normalizes the voice clip to the same format and loudness, and joins everything. Every command in the tapes replays from the committed LLM cache: no API key or quota is used. Without a clip argument the video is the automated part only (about 2 min 55 s); with a 60-second clip it is about 4 minutes.

| Segment | Shows |
|---|---|
| 00 title | what Candor is |
| 01 now vs then | launch date as of Sep 18 (October 21) and as of Sep 12 (October 14), with sources |
| 02 correction | board deck NRR before Ben's correction (118%) and after (112%) |
| 03 disagreement | Harbor: Marcus and John disagree; both sides reported |
| 04 don't know | Dana's salary (I don't know); Acme contract despite the planted instruction (not signed) |
| 05 actions | Sarah Patel by email for the proposal; delete needs confirmation; reminder at 08:00, not the run-through |
| 06 assistant | plan, yes, dry run, audit log |
| 07 voice | your live clip (below) |
| 08 evals | `make test`, `make eval`, `make eval-actions` live |
| 09 close | repo |

## Recording the voice clip (about 60 seconds)

1. Terminal: font size 18 pt or larger, one window, `cd ~/code/candor`.
2. Run `make voice` once before recording and allow microphone access when macOS asks; press Ctrl-D.
3. QuickTime Player > File > New Screen Recording. In Options pick the MacBook microphone so your voice is recorded too. Record the terminal window.
4. Run `make voice`. For each line: press Enter, speak, press Enter. Wait for the spoken reply before the next one.
   - "What's our launch date again?" It answers October 21 with sources and says it aloud.
   - "Delete all my emails from Marcus." It asks "Are you sure?" Say "Yes". It records the request and deletes nothing.
   - Optional: "Message Sarah on Slack that the geocoding fix looks good", then "Yes": a dry run, nothing sent.
5. Ctrl-D, stop the recording, save it as `~/Movies/voice-clip.mov`.
6. `docs/video/build.sh ~/Movies/voice-clip.mov`

Upload `~/Movies/candor-demo.mp4` to YouTube (unlisted) or Google Drive (anyone with the link) and put the link in the reply email.
