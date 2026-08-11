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

os.makedirs("images", exist_ok=True)

W, H = 1080, 1080
bg_color = (14, 22, 18)
accent_color = (60, 200, 120)

img = Image.new("RGB", (W, H), bg_color)
draw = ImageDraw.Draw(img)

font_path_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font_path_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

try:
    font_title = ImageFont.truetype(font_path_bold, 72)
    font_small = ImageFont.truetype(font_path_regular, 36)
except Exception:
    font_title = ImageFont.load_default()
    font_small = ImageFont.load_default()

draw.rectangle([(0, 0), (W, 12)], fill=accent_color)
draw.text((60, 60), "ACTU FOOT", font=font_small, fill=accent_color)

wrapped = textwrap.wrap(title.upper(), width=16)
y = H / 2 - (len(wrapped) * 90) / 2
for line in wrapped:
    bbox = draw.textbbox((0, 0), line, font=font_title)
    line_w = bbox[2] - bbox[0]
    draw.text(((W - line_w) / 2, y), line, font=font_title, fill="white")
    y += 90

date_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
draw.text((60, H - 90), date_str, font=font_small, fill=(150, 150, 150))

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
