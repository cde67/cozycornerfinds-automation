"""
Generates branded Instagram gift-guide graphics for Cozy Corner Finds (a home
organization / cozy-living affiliate content account). Each post is a themed
roundup of 5 generic item categories - no real product photos or brand names,
since we don't have Amazon Product Advertising API access yet (that requires
an already-active Associates account with qualifying sales). The caption
points to the affiliate link for each item via the bio link page.
"""
import os
import random
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_TITLE = os.path.join(SCRIPT_DIR, "ArchivoBlack-Regular.ttf")
FONT_BODY = os.path.join(SCRIPT_DIR, "Oswald-Variable.ttf")

SIZE = 1080
MARGIN = 80

INK = (45, 40, 38, 255)
ACCENT = (196, 130, 84, 255)
BG = (250, 245, 238, 255)
CARD = (255, 255, 255, 255)

# Rotating themes. Each item is a generic, non-branded description an affiliate
# link can point to (e.g. "amazon.com/s?k=<search terms>&tag=<associates-id>").
THEMES = [
    {"title": "5 Cozy Finds Under $30", "items": [
        "Chunky knit throw blanket", "Ceramic aromatherapy diffuser",
        "Soft LED string lights", "Oversized floor cushion", "Warm salt lamp"]},
    {"title": "Entryway Organization Must-Haves", "items": [
        "Wall-mounted key + mail organizer", "Stackable shoe rack",
        "Boot tray for wet weather", "Slim console table", "Woven storage baskets"]},
    {"title": "Small Bedroom Storage Hacks", "items": [
        "Under-bed rolling storage bins", "Over-the-door hanging organizer",
        "Floating wall shelves", "Bed frame with built-in drawers", "Velvet hangers (space-saving)"]},
    {"title": "Kitchen Counter Declutter Kit", "items": [
        "Bamboo dish rack", "Stackable spice organizer",
        "Under-sink pull-out organizer", "Magnetic knife strip", "Countertop appliance garage"]},
    {"title": "Work-From-Home Desk Upgrades", "items": [
        "Cable management box", "Monitor riser with storage",
        "Desk pad + wrist rest set", "Adjustable laptop stand", "Warm desk lamp"]},
    {"title": "Bathroom Spa-Day Essentials", "items": [
        "Teak bath caddy tray", "Waffle-knit towel set",
        "Fog-free shower mirror", "Bath pillow with suction cups", "Rainfall shower head"]},
    {"title": "Closet Organization Starter Set", "items": [
        "Velvet non-slip hangers", "Clear stackable shoe boxes",
        "Hanging closet organizer", "Cedar wood blocks", "Over-the-rod scarf hanger"]},
    {"title": "Cozy Reading Nook Ideas", "items": [
        "Oversized bean bag chair", "Book page clip light",
        "Faux fur throw pillow", "Wooden book stand", "Mini electric kettle for tea"]},
]


def load_font(path, size, weight=None):
    font = ImageFont.truetype(path, size)
    if path == FONT_BODY and weight:
        font.set_variation_by_axes([weight])
    return font


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_post(theme, out_path):
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, SIZE, 18], fill=ACCENT)

    eyebrow_font = load_font(FONT_BODY, 32, 600)
    draw.text((MARGIN, 70), "COZY CORNER FINDS", font=eyebrow_font, fill=ACCENT)

    title_font = load_font(FONT_TITLE, 64)
    lines = wrap_text(draw, theme["title"], title_font, SIZE - 2 * MARGIN)
    y = 130
    for line in lines:
        draw.text((MARGIN, y), line, font=title_font, fill=INK)
        y += 74

    card_top = y + 30
    card_bottom = SIZE - 140
    draw.rounded_rectangle([MARGIN, card_top, SIZE - MARGIN, card_bottom], radius=28, fill=CARD, outline=(225, 215, 205), width=2)

    item_font = load_font(FONT_BODY, 36, 500)
    num_font = load_font(FONT_TITLE, 40)
    row_h = (card_bottom - card_top - 60) // 5
    for i, item in enumerate(theme["items"]):
        row_y = card_top + 40 + i * row_h
        draw.ellipse([MARGIN + 40, row_y, MARGIN + 100, row_y + 60], fill=ACCENT)
        draw.text((MARGIN + 70, row_y + 30), str(i + 1), font=num_font, fill=(255, 255, 255, 255), anchor="mm")
        item_lines = wrap_text(draw, item, item_font, SIZE - 2 * MARGIN - 160)
        draw.text((MARGIN + 130, row_y + 8), item_lines[0], font=item_font, fill=INK)
        if len(item_lines) > 1:
            draw.text((MARGIN + 130, row_y + 44), item_lines[1], font=item_font, fill=INK)

    cta_font = load_font(FONT_BODY, 38, 600)
    draw.text((SIZE // 2, SIZE - 80), "Shop the look — link in bio", font=cta_font, fill=ACCENT, anchor="mm")

    img.save(out_path, "PNG")


def caption_for(theme):
    numbered = "\n".join(f"{i+1}. {item}" for i, item in enumerate(theme["items"]))
    return (
        f"{theme['title']} ✨\n\n{numbered}\n\n"
        f"All linked in our bio! As an Amazon Associate we earn from qualifying purchases.\n\n"
        f"#cozyhome #homeorganization #giftguide #homedecor #organizationideas"
    )


def main():
    out_dir = os.path.join(SCRIPT_DIR, "posts")
    os.makedirs(out_dir, exist_ok=True)
    theme = random.choice(THEMES)
    slug = theme["title"].lower().replace(" ", "_").replace("$", "").replace("-", "")
    img_path = os.path.join(out_dir, f"{slug}.png")
    make_post(theme, img_path)
    caption = caption_for(theme)
    with open(os.path.join(out_dir, f"{slug}_caption.txt"), "w") as f:
        f.write(caption)
    print(f"Made {img_path}")
    print(f"Caption:\n{caption}")


if __name__ == "__main__":
    main()
