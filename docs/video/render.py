"""Render index.html (next to this file): stills for checking, or every frame piped into ffmpeg.
  python render.py stills 3 15.5 ...      -> work/stills/t003.0.png ...
  python render.py video <seconds> <out>  -> silent 1920x1080 30 fps H.264
"""
import json, subprocess, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
page_html = (HERE / "index.html").read_text().replace("__TIMELINE__", (HERE / "timeline.json").read_text())
(HERE / "build.html").write_text(page_html)

def open_page(p):
    browser = p.chromium.launch(args=["--allow-file-access-from-files", "--force-color-profile=srgb"])
    page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    page.goto((HERE / "build.html").as_uri())
    page.evaluate("window.ready")
    return browser, page

mode = sys.argv[1]
with sync_playwright() as p:
    browser, page = open_page(p)
    if mode == "stills":
        out = HERE / "stills"; out.mkdir(exist_ok=True)
        for t in map(float, sys.argv[2:]):
            page.evaluate(f"render({t})")
            page.screenshot(path=str(out / f"t{t:05.1f}.png"))
        print("stills:", out)
    else:
        seconds, dest = float(sys.argv[2]), sys.argv[3]
        ff = subprocess.Popen(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", "30", "-c:v", "mjpeg",
                               "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-r", "30", dest],
                              stdin=subprocess.PIPE)
        n = int(round(seconds * 30))
        for f in range(n):
            page.evaluate(f"render({f / 30})")
            ff.stdin.write(page.screenshot(type="jpeg", quality=95))
            if f % 300 == 0:
                print(f"frame {f}/{n}", flush=True)
        ff.stdin.close(); ff.wait()
        print("video:", dest)
    browser.close()
