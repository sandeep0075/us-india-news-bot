import json
import os
import re
import smtplib
from datetime import datetime
from email.message import EmailMessage
import feedparser
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

FEEDS = [
    "https://news.google.com/rss/search?q=H1B+OR+USCIS+OR+PERM+OR+Green+Card+India&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Indian+Americans+OR+US+India+immigration+OR+remittance+tax&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=India+US+trade+OR+visa+bulletin+India&hl=en-US&gl=US&ceid=US:en",
]

SEEN_FILE = "seen_stories.json"


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_seen(seen_list):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen_list[-100:], f, indent=2)


def clean_html(raw_html):
    return re.sub(r"<[^>]+>", "", raw_html or "").strip()


def fetch_top_new_story(seen_titles):
    seen_lower = {t.lower() for t in seen_titles}
    for url in FEEDS:
        parsed = feedparser.parse(url)
        for entry in parsed.entries:
            title = entry.get("title", "").strip()
            if not title or title.lower() in seen_lower:
                continue
            return {
                "title": title,
                "summary": clean_html(entry.get("summary", "")),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            }
    return None


def analyze_story_with_llm(story):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = f"""
You are a senior news editor creating a visual briefing for Indians living in the United States.
Pick apart this news story and explain its practical details and impact in 5 to 6 clear, numbered points.

Headline: {story['title']}
Details: {story['summary']}

Return ONLY a valid JSON object matching this exact structure:
{{
  "badge": "BREAKING NEWS",
  "main_headline": "SHORT PUNCHY 3-5 WORD HEADLINE IN ALL CAPS",
  "yellow_subtitle": "1-2 LINE SUBTITLE IN ALL CAPS EXPLAINING THE CORE TOPIC",
  "section_header": "KEY DETAILS & IMPACT EXPLAINED",
  "status_pill": "LATEST UPDATE — WHAT YOU NEED TO KNOW",
  "points": [
    {{
      "icon": "🏛️",
      "text": "Clear, detailed explanation with <span class='hl'>2 to 4 key words highlighted</span> in red."
    }}
  ]
}}

Rules:
- Provide 5 or 6 points.
- Each point should be 14 to 24 words long so it is informative yet easy to scan on a phone.
- Use a distinct, relevant emoji for each point's "icon".
- Wrap the single most important phrase in each point inside <span class='hl'>...</span>.
- Do not include markdown fences or extra commentary outside the JSON.
"""
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )
    return json.loads(response.text)


def render_infographic(data, output_path="digest.png"):
    cards_html = ""
    for i, item in enumerate(data["points"], start=1):
        cards_html += f"""
        <div class="card">
            <div class="icon-box">{item['icon']}</div>
            <div class="divider"></div>
            <div class="point-text"><strong>{i}.</strong> {item['text']}</div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'DejaVu Sans', 'Segoe UI', Arial, sans-serif; }}
      body {{
        width: 1080px;
        background: linear-gradient(180deg, #e7edf5 0%, #f8fafc 100%);
        color: #16243d;
      }}
      .top-bar {{
        background: #14284b;
        color: #ffffff;
        padding: 28px 45px;
        display: flex;
        align-items: center;
        gap: 22px;
        border-bottom: 6px solid #c82333;
      }}
      .top-bar h1 {{
        font-size: 46px;
        font-weight: 900;
        letter-spacing: 1px;
      }}
      .breaking-tag {{
        background: #c82333;
        color: #ffffff;
        font-weight: 800;
        font-size: 23px;
        padding: 8px 22px;
        transform: skewX(-15deg);
      }}
      .breaking-tag span {{
        display: inline-block;
        transform: skewX(15deg);
      }}
      .hero {{
        padding: 38px 45px 22px 45px;
        background: radial-gradient(circle at top right, rgba(20, 40, 75, 0.08), transparent 60%);
      }}
      .main-headline {{
        font-size: 54px;
        font-weight: 900;
        line-height: 1.08;
        color: #14284b;
        margin-bottom: 18px;
        max-width: 960px;
      }}
      .yellow-banner {{
        display: inline-block;
        background: #f5b82e;
        color: #14284b;
        font-size: 28px;
        font-weight: 800;
        padding: 10px 20px;
        border-radius: 8px;
        line-height: 1.25;
      }}
      .section-pill-wrap {{
        text-align: center;
        margin: 14px 0 22px 0;
      }}
      .section-pill {{
        display: inline-block;
        background: #b8292f;
        color: #ffffff;
        font-size: 25px;
        font-weight: 800;
        padding: 10px 34px;
        border-radius: 10px;
        letter-spacing: 0.5px;
      }}
      .cards-container {{
        padding: 0 45px;
        display: flex;
        flex-direction: column;
        gap: 15px;
      }}
      .card {{
        background: #ffffff;
        border: 2.5px solid #2b3e5c;
        border-radius: 16px;
        padding: 18px 24px;
        display: flex;
        align-items: center;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
      }}
      .icon-box {{
        width: 82px;
        font-size: 46px;
        text-align: center;
        flex-shrink: 0;
      }}
      .divider {{
        width: 3px;
        height: 62px;
        background: #2b3e5c;
        margin: 0 22px;
        flex-shrink: 0;
      }}
      .point-text {{
        font-size: 26px;
        line-height: 1.32;
        color: #1a202c;
        font-weight: 600;
      }}
      .hl {{
        color: #b8292f;
        font-weight: 800;
      }}
      .footer-wrap {{
        text-align: center;
        padding: 28px 0 38px 0;
      }}
      .footer-pill {{
        display: inline-block;
        background: #b8292f;
        color: #ffffff;
        font-size: 28px;
        font-weight: 900;
        padding: 12px 42px;
        border-radius: 40px;
        letter-spacing: 1px;
      }}
    </style>
    </head>
    <body>
      <div class="top-bar">
        <h1>NEWS UPDATE</h1>
        <div class="breaking-tag"><span>{data['badge']}</span></div>
      </div>

      <div class="hero">
        <div class="main-headline">{data['main_headline']}</div>
        <div class="yellow-banner">{data['yellow_subtitle']}</div>
      </div>

      <div class="section-pill-wrap">
        <div class="section-pill">{data['section_header']}</div>
      </div>

      <div class="cards-container">
        {cards_html}
      </div>

      <div class="footer-wrap">
        <div class="footer-pill">{data['status_pill']}</div>
      </div>
    </body>
    </html>
    """

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
        page.set_content(html)
        page.locator("body").screenshot(path=output_path)
        browser.close()


def send_email(image_path, title, link):
    msg = EmailMessage()
    msg["Subject"] = f"US–India News Brief: {title}"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]
    msg.set_content(
        f"Top US–India Story ({datetime.now().strftime('%b %d, %I:%M %p')}):\n"
        f"{title}\n\n"
        f"Read full source article: {link}\n"
    )

    with open(image_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="image", subtype="png", filename="us-india-news-card.png")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ["EMAIL_FROM"], os.environ["SMTP_APP_PASSWORD"])
        smtp.send_message(msg)


if __name__ == "__main__":
    seen = load_seen()
    story = fetch_top_new_story(seen)

    if not story:
        print("No unseen stories found in this 2-hour window. Skipping email.")
    else:
        print(f"Processing story: {story['title']}")
        structured = analyze_story_with_llm(story)
        render_infographic(structured, "digest.png")
        send_email("digest.png", story["title"], story["link"])
        seen.append(story["title"])
        save_seen(seen)
        print("Digest image emailed and story marked as seen.")
