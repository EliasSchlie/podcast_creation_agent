# Creating Podcast Cover Art

The podcast cover is a 1400x1400 JPEG generated with Pillow. Spotify requires minimum 300x300, recommends 3000x3000.

## Generate cover

```bash
uv run python docs/generate_cover.py
# Creates podcast_cover.jpg in current directory
```

## Customize

Always use `docs/generate_cover.py` as the starting template -- only change colors and text. The layout (font sizes, positions, gradient style) is already tuned for Spotify's thumbnail.

- **Colors**: Modify the gradient RGB values in the nested loop
- **Text**: Change the `draw.text()` calls for title/subtitle. All title words use `font_large` (same size).
- **Font**: Uses system Helvetica by default, falls back to Pillow's default font

## Upload to Spotify

Upload the cover via Spotify Creators dashboard (Settings -> show cover art) or through the pipeline's `create-podcast` command.
