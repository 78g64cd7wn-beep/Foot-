#!/usr/bin/env python3
import os
import sys
import json
import textwrap
import urllib.request
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    print("Erreur : ANTHROPIC_API_KEY n'est pas definie.")
    sys.exit(1)

TOPICS_FILE = "posted_topics.json"
LOG_FILE = "posts_log.md"
PENDING_FILE = "pending.json"
IMAGE_PATH = "images/latest_post.png"
SKIP_MARKER = "AUCUNE_ACTU"

SYSTEM_PROMPT = f"""Tu es un agent d'actualite football, specialise dans le football francais et europeen.

Ta mission a chaque execution :
1. Utilise la recherche web pour verifier s'il y a une actualite football NOTABLE et RECENTE (moins de quelques heures) : transfert officialise, resultat de match important, blessure d'un joueur majeur, declaration marquante, record battu.
2. Compare avec la liste des sujets deja traites. Ne repete jamais un sujet deja couvert.
3. Sois strict : une rumeur non confirmee ou un simple entrainement ne suffisent pas.

DEUX CAS POSSIBLES :

CAS A - actu nouvelle et notable trouvee :
Reponds EXACTEMENT dans ce format (une ligne par champ, rien d'autre) :
TITLE: [4 a 8 mots, percutant, pour affichage sur une image]
CAPTION: [le texte complet du post Instagram : accroche, corps 60-100 mots, chute, 3-5 hashtags, tout sur une seule ligne avec des \\n pour les retours a la ligne]
SOURCE: [media d'origine]
TOPIC_ID: [3-6 mots resumant le sujet, pour eviter les doublons]

CAS B - rien de notable :
Reponds UNIQUEMENT avec : {SKIP_MARKER}
"""

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

topics = load_json(TOPICS_FILE, [])
recent_topics = topics[-30:]
topics_str = "\n".join(f"- {t['topic']}" for t in recent_topics) if recent_topics else "(aucun sujet traite pour l'instant)"

now_iso = datetime.now(timezone.utc).isoformat()
user_message = f"""Verifie l'actu football maintenant ({now_iso}).

Sujets deja traites recemment (ne pas repeter) :
{topics_str}
"""

payload = {
    "model": "claude-sonnet-4-6",
    "max_tokens": 1500,
    "system": SYSTEM_PROMPT,
    "tools": [{"type": "web_search_20250305", "name": "web_search"}],
    "messages": [{"role": "user", "content": user_message}],
}

req = urllib.request.Request(
    "https://api.anthropic.com/v1/messages",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))
except Exception as e:
    print(f"Erreur lors de l'appel API : {e}")
    sys.exit(1)

text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
result_text = "\n".join(text_blocks).strip()

if not result_text or SKIP_MARKER in result_text:
    print("Rien de notable pour l'instant, pas de post genere.")
    sys.exit(0)

fields = {"TITLE": "", "CAPTION": "", "SOURCE": "", "TOPIC_ID": ""}
for line in result_text.splitlines():
    for key in fields:
        prefix = f"{key}:"
        if line.strip().startswith(prefix):
            fields[key] = line.strip()[len(prefix):].strip()

if not fields["CAPTION"] or not fields["TOPIC_ID"]:
    print("Reponse mal formee, on ignore ce cycle.")
    sys.exit(0)

caption = fields["CAPTION"].replace("\\n", "\n")
title = fields["TITLE"] or "Actu Foot"
source = fields["SOURCE"] or ""

os.makedirs("images", exist_ok=True)
os.makedirs("fonts", exist_ok=True)


# ---------------------------------------------------------------------------
# Polices : on telecharge une police impactante (style "media sportif") une
# seule fois, avec repli sur DejaVu si le telechargement echoue.
# ---------------------------------------------------------------------------
FONT_TITLE_PATH = "fonts/Anton-Regular.ttf"
FONT_BODY_PATH = "fonts/Oswald-Bold.ttf"
FONT_LIGHT_PATH = "fonts/Oswald-Regular.ttf"

FONT_SOURCES = {
    FONT_TITLE_PATH: "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf",
    FONT_BODY_PATH: "https://github.com/google/fonts/raw/main/ofl/oswald/static/Oswald-Bold.ttf",
    FONT_LIGHT_PATH: "https://github.com/google/fonts/raw/main/ofl/oswald/static/Oswald-Regular.ttf",
}

for path, url in FONT_SOURCES.items():
    if not os.path.exists(path):
        try:
            urllib.request.urlretrieve(url, path)
        except Exception as e:
            print(f"Avertissement : impossible de telecharger {url} ({e})")

FALLBACK_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FALLBACK_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def load_font(path, fallback, size):
    try:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
        return ImageFont.truetype(fallback, size)
    except Exception:
        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Dessin de l'image
# ---------------------------------------------------------------------------
W, H = 1080, 1080

# Couleurs
COLOR_TOP = (12, 18, 16)
COLOR_BOTTOM = (4, 6, 6)
ACCENT = (64, 214, 128)      # vert vif
ACCENT_DARK = (28, 96, 60)
WHITE = (245, 245, 245)
GREY = (150, 155, 152)

img = Image.new("RGB", (W, H), COLOR_TOP)
draw = ImageDraw.Draw(img)

# --- Fond en degrade vertical ---------------------------------------------
for y in range(H):
    t = y / H
    r = int(COLOR_TOP[0] + (COLOR_BOTTOM[0] - COLOR_TOP[0]) * t)
    g = int(COLOR_TOP[1] + (COLOR_BOTTOM[1] - COLOR_TOP[1]) * t)
    b = int(COLOR_TOP[2] + (COLOR_BOTTOM[2] - COLOR_TOP[2]) * t)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# --- Cercle decoratif discret en fond (texture) ----------------------------
overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
odraw = ImageDraw.Draw(overlay)
odraw.ellipse([W - 480, -280, W + 280, 480], outline=(255, 255, 255, 14), width=26)
odraw.ellipse([-260, H - 460, 300, H + 280], outline=(255, 255, 255, 10), width=18)
img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
draw = ImageDraw.Draw(img)

# --- Barre d'accent tout en haut -------------------------------------------
draw.rectangle([(0, 0), (W, 10)], fill=ACCENT)

# --- Badge categorie ---------------------------------------------------
badge_font = load_font(FONT_BODY_PATH, FALLBACK_BOLD, 30)
badge_text = "ACTU FOOT"
bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
badge_w = (bbox[2] - bbox[0]) + 56
badge_h = 56
badge_x, badge_y = 60, 70
draw.rounded_rectangle(
    [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
    radius=28,
    fill=ACCENT,
)
draw.text(
    (badge_x + 28, badge_y + badge_h / 2),
    badge_text,
    font=badge_font,
    fill=(6, 10, 8),
    anchor="lm",
)


# --- Titre : on ajuste la taille automatiquement pour que ca tienne -------
def wrap_by_pixels(text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        w = draw.textbbox((0, 0), trial, font=font)[2]
        if w <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


MAX_TEXT_WIDTH = W - 140
title_text = title.upper()

for size in range(120, 55, -4):
    font_title = load_font(FONT_TITLE_PATH, FALLBACK_BOLD, size)
    lines = wrap_by_pixels(title_text, font_title, MAX_TEXT_WIDTH)
    line_height = int(size * 1.08)
    total_height = line_height * len(lines)
    widest = max(draw.textbbox((0, 0), l, font=font_title)[2] for l in lines)
    if len(lines) <= 5 and total_height <= 520 and widest <= MAX_TEXT_WIDTH:
        break

# Position verticale : bloc titre centre sur le tiers inferieur du visuel
block_top = H - 420
y = block_top
for line in lines:
    draw.text((70, y), line, font=font_title, fill=WHITE)
    y += line_height

# --- Trait d'accent sous le titre ------------------------------------------
underline_y = y + 18
draw.rectangle([(70, underline_y), (70 + 140, underline_y + 8)], fill=ACCENT)

# --- Pied de page : source + date, separes par une ligne fine -------------
footer_y = H - 92
draw.line([(70, footer_y - 26), (W - 70, footer_y - 26)], fill=(60, 66, 63), width=2)

font_footer = load_font(FONT_LIGHT_PATH, FALLBACK_REG, 32)
date_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")

if source:
    draw.text((70, footer_y), source.upper(), font=font_footer, fill=GREY, anchor="lm")

date_bbox = draw.textbbox((0, 0), date_str, font=font_footer)
date_w = date_bbox[2] - date_bbox[0]
draw.text((W - 70 - date_w, footer_y), date_str, font=font_footer, fill=GREY, anchor="lm")

img.save(IMAGE_PATH)

with open(PENDING_FILE, "w", encoding="utf-8") as f:
    json.dump({
        "caption": caption,
        "topic_id": fields["TOPIC_ID"],
        "source": fields["SOURCE"],
        "image_path": IMAGE_PATH,
    }, f, ensure_ascii=False, indent=2)

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
log_entry = f"\n\n## {timestamp}\n\n{caption}\n\nSource : {fields['SOURCE']}\n"
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("# Historique des posts foot generes\n")
with open(LOG_FILE, "a", encoding="utf-8") as f:
    f.write(log_entry)

print(f"Post prepare : {fields['TOPIC_ID']}")
