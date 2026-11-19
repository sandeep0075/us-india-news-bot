import os
import json
import smtplib
from datetime import datetime
from email.message import EmailMessage
import feedparser
from google import genai
from playwright.sync_api import sync_playwright

FEEDS = [
    "https://news.google.com/rss/search?q=H1B+OR+USCIS+OR+PERM+OR+Green+Card+India&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=US+India+tax+OR+remittance+OR+immigration&hl=en-US&gl=US&ceid=US:en",
]

def fetch_top_story():
    for url in FEEDS:
        parsed = feedparser.parse(url)
        if parsed.entries:
            entry = parsed.entries[0]
            return {
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "link": entry.get("link", ""),
            }
    return None

def analyze_story_with_llm(story):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = f"""
    You are a news editor for Indians living in the United States.
    Take this news story and turn it into a deep-dive infographic breakdown.
    
    Story Title: {story['title']}
    Story Summary: {story['summary']}

    Return ONLY valid JSON with this exact schema:
    {{
      "badge": "BREAKING NEWS",
      "main_headline": "SHORT PUNCHY 3-5 WORD HEADLINE IN CAPS",
      "yellow_subtitle": "2-LINE SUBTITLE IN CAPS EXPLAINING THE CORE TOPIC",
      "section_header": "MAJOR DETAILS & IMPACT EXPLAINED",
      "status_pill": "LATEST UPDATE — KEY TAKEAWAYS",
      "points": [
        {{
          "icon": "🏛️",
          "text": "Detailed explanation of point 1 with <span class='hl'>key highlighted phrase</span> inside."
        }}
      ]
    }}
    Include 5 to 6 clear, informative points explaining how this affects Indians in America.
    Use relevant emojis for each icon. Wrap the most important 2-4 words of each point in <span class='hl'>...</span>.
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    raw = response.text.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(raw)

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
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; }}
      body {{
        width: 1080px;
        background: linear-gradient(180deg, #e9eef5 0%, #f7f9fc 100%);
        color: #16243d;
      }}
      .top-bar {{
        background: #14284b;
        color: white;
        padding: 28px 45px;
        display: flex;
        align-items: center;
        gap: 20px;
        border-bottom: 6px solid #c82333;
      }}
      .top-bar h1 {{ font-size: 46px; font-weight: 900; letter-spacing: 1px; }}
      .breaking-tag {{
        background: #c82333;
        color: white;
        font-weight: 800;
        font-size: 24px;
        padding: 8px 22px;
        transform: skewX(-15deg);
      }}
      .breaking-tag span {{ display: inline-block; transform: skewX(15deg); }}
      .hero {{
        padding: 40px 45px 25px 45px;
        background: radial-gradient(circle at top right, rgba(20,40,75,0.08), transparent 60%);
      }}
      .main-headline {{
        font-size: 56px;
        font-weight: 900;
        line-height: 1.08;
        color: #14284b;
        margin-bottom: 18px;
        max-width: 780px;
      }}
      .yellow-banner {{
        display: inline-block;
        background: #f5b82e;
        color: #14284b;
        font-size: 30px;
        font-weight: 800;
        padding: 10px 20px;
        border-radius: 8px;
        line-height: 1.25;
      }}
      .section-pill-wrap {{ text-align: center; margin: 15px 0 22px 0; }}
      .section-pill {{
        display: inline-block;
        background: #b8292f;
        color: white;
        font-size: 26px;
        font-weight: 800;
        padding: 10px 34px;
        border-radius: 10px;
        letter-spacing: 0.5px;
      }}
      .cards-container {{ padding: 0 45px; display: flex; flex-direction: column; gap: 16px; }}
      .card {{
        background: white;
        border: 2.5px solid #2b3e5c;
        border-radius: 16px;
        padding: 18px 24px;
        display: flex;
        align-items: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
      }}
      .icon-box {{
        width: 85px;
        font-size: 48px;
        text-align: center;
        flex-shrink: 0;
      }}
      .divider {{
        width: 3px;
        height: 64px;
        background: #2b3e5c;
        margin: 0 22px;
        flex-shrink: 0;
      }}
      .point-text {{
        font-size: 27px;
        line-height: 1.32;
        color: #1a202c;
        font-weight: 600;
      }}
      .hl {{ color: #b8292f; font-weight: 800; }}
      .footer-wrap {{ text-align: center; padding: 30px 0 40px 0; }}
      .footer-pill {{
        display: inline-block;
        background: #b8292f;
        color: white;
        font-size: 30px;
        font-weight: 900;
        padding: 12px 44px;
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
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        page.set_content(html)
        page.locator("body").screenshot(path=output_path)
        browser.close()

def send_email(image_path, title, link):
    msg = EmailMessage()
    msg["Subject"] = f"US–India Deep Dive: {title}"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]
    msg.set_content(f"Read full article: {link}\n\nYour visual breakdown is attached.")

    with open(image_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="image", subtype="png", filename="news-card.png")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ["EMAIL_FROM"], os.environ["SMTP_APP_PASSWORD"])
        smtp.send_message(msg)

if __name__ == "__main__":
    story = fetch_top_story()
    if story:
        structured = analyze_story_with_llm(story)
        render_infographic(structured, "digest.png")
        send_email("digest.png", story["title"], story["link"])
