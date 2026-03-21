"""Generate a podcast cover image with a gradient background and text overlay."""

from PIL import Image, ImageDraw, ImageFont

# 1400x1400 is a good balance between Spotify's min (300) and max (3000)
WIDTH = HEIGHT = 1400

img = Image.new("RGB", (WIDTH, HEIGHT))
draw = ImageDraw.Draw(img)

# Purple-blue gradient background
for y in range(HEIGHT):
    for x in range(WIDTH):
        r = int(30 + (y / HEIGHT) * 40)
        g = int(10 + (x / WIDTH) * 30)
        b = min(255, int(60 + (y / HEIGHT) * 120 + (x / WIDTH) * 60))
        img.putpixel((x, y), (r, g, b))

# Text overlay
try:
    font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
    font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
except OSError:
    font_large = ImageFont.load_default()
    font_small = font_large

draw.text((100, 500), "Positive", fill=(255, 255, 255), font=font_large)
draw.text((100, 600), "Psychology", fill=(255, 255, 255), font=font_large)
draw.text((100, 700), "Podcast", fill=(200, 200, 255), font=font_large)
draw.text((100, 850), "AI Deep Dive", fill=(180, 180, 220), font=font_small)

img.save("podcast_cover.jpg", "JPEG", quality=95)
print(f"Created podcast_cover.jpg ({img.size})")
