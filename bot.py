import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
import feedparser
from PIL import Image, ImageDraw, ImageFont

FEEDS = [
    "https://news.google.com/rss/search?q=H1B+OR+USCIS+OR+Indian+Americans&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=India+US+relations+OR+RBI+rupee&hl=en-IN&gl=IN&ceid=IN:en",
]

KEYWORDS = ("h-1b", "h1b", "visa", "uscis", "green card", "indian american", "india", "rupee", "remittance")

def get_headlines(limit=5):
    items = []
    seen = set()
    for url in FEEDS:
        parsed = feedparser.parse(url)
        for entry in parsed.entries:
            title = entry.get("title", "").strip()
            key = title.lower()
            if not title or key in seen:
                continue
            if any(k in key for k in KEYWORDS):
                seen.add(key)
                items.append(title)
            if len(items) >= limit:
                return items
    return items

def render_digest_image(headlines, output_path="digest.png"):
    width, height = 1080, 1350
    img = Image.new("RGB", (width, height), color=(18, 22, 28))
    draw = ImageDraw.Draw(img)

    # Load a TTF font if available on your system/runner, else fallback
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    title_font = ImageFont.truetype(font_paths[0], 38) if os.path.exists(font_paths[0]) else ImageFont.load_default()
    body_font = ImageFont.truetype(font_paths[1], 28) if os.path.exists(font_paths[1]) else ImageFont.load_default()

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    draw.text((60, 60), "US–India Brief (2h)", fill=(255, 153, 51), font=title_font)
    draw.text((60, 115), stamp, fill=(160, 170, 185), font=body_font)

    y = 200
    for idx, headline in enumerate(headlines, start=1):
        wrapped = []
        words = headline.split()
        line = f"{idx}. "
        for w in words:
            test = f"{line}{w} ".strip()
            if draw.textlength(test, font=body_font) <= width - 120:
                line = test + " "
            else:
                wrapped.append(line.strip())
                line = f"   {w} "
        if line.strip():
            wrapped.append(line.strip())

        for wline in wrapped:
            draw.text((60, y), wline, fill=(240, 244, 248), font=body_font)
            y += 42
        y += 28
        if y > height - 100:
            break

    img.save(output_path)
    return output_path

def send_email_with_image(image_path):
    msg = EmailMessage()
    msg["Subject"] = f"2-Hour US–India News Digest ({datetime.now().strftime('%I:%M %p')})"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]
    msg.set_content("Attached is your latest 2-hour news digest image.")

    with open(image_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="image", subtype="png", filename="digest.png")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ["EMAIL_FROM"], os.environ["SMTP_APP_PASSWORD"])
        smtp.send_message(msg)

if __name__ == "__main__":
    headlines = get_headlines(limit=5) or ["No major matching updates in this cycle."]
    path = render_digest_image(headlines)
    send_email_with_image(path)
