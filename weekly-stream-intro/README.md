# Goated Weekly Stream: 10s intro

**Video → [`goated_weekly_stream_intro.mp4`](goated_weekly_stream_intro.mp4)** (1920×1080, 60fps, H.264 + AAC 320k)
Last frame: [`final_frame.png`](final_frame.png). Compare with `assets/final_frame_reference.webp`.

Everything is rendered by [`render.py`](render.py) (numpy + OpenCV + Pillow, ffmpeg for encoding).
Music is `assets/music.mp3` from 0:25. Each hit below is keyed to an onset measured in the track.

| Time | Music | On screen |
|---|---|---|
| 0.0–1.5 | intro pad (+ soft noise riser) | background flickers up from black, the logo glitches in at centre, lime sparks get pulled into it, the camera tightens |
| 1.56 | 808 | logo slams in: flash, god rays, shockwave refraction, spark burst, and an explosion of bills/dice/tickets out of the logo |
| 2.02–2.39 | clap | logo whips up into its lockup position; THE GOATED slams in letter by letter from the centre out |
| 3.42 / 3.63 | 808 double | WEEKLY then STREAM slam in from opposite sides with squash, a white-hot impact, a shake and debris sparks |
| 4.04 | clap | light sweep across WEEKLY STREAM |
| 4.87 | 808 | lime light bar, then the date decodes from scrambled glyphs, centre out |
| 5.69 | clap | Kick icon spins in and the URL types on with a cursor |
| 6.73 / 6.94 | 808 double | RGB-split glitch on the title, a gust of bills from both top corners |
| 7.35 | clap | light sweep across the full lockup |
| 8.17 | 808 | time-freeze: the rain decelerates into slow motion and settles into the key-art layout |
| 9.0–10.0 | | hold on the final frame while the music fades out |

The rain is 3D-projected sprites (perspective flutter, sheen and real motion blur) on three depth
layers: a blurred, tinted far layer, a sharp mid layer kept mostly to the sides of the text, and an
out-of-focus near layer in front. Ten "hero" items are solved backwards from the reference so
they come to rest where the key art places them.

## Re-render

```
pip install opencv-python-headless numpy pillow
python3 render.py --sheet              # timeline contact sheet -> out/sheet.png
python3 render.py --preview 3.45 9.99  # single frames -> out/preview_*.png
python3 render.py                      # full render -> out/goated_weekly_stream_intro.mp4 (~4 min on 4 cores)
python3 render.py --remux              # re-mux audio/encode from the existing chunks
```

Timing lives in the `H1…C5` constants; layout lives in `LOGO_POS`, `GOATED_Y`, `STREAM_Y`, `DATE_Y`, and `KICK_Y`.
To change the date, edit `date_text` in `Assets`.
