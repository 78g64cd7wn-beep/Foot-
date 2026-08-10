#!/usr/bin/env python3
"""
Agent IA - Actu foot en temps réel.
Vérifie s'il y a une actualité football notable et poste UNIQUEMENT si c'est le cas.
Évite de répéter un sujet déjà traité récemment.
"""

import os
import sys
import json
import urllib.request
from datetime import datetime, timezone

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    print("Erreur : la variable d'environnement ANTHROPIC_API_KEY n'est pas définie.")
    sys.exit(1)

TOPICS_FILE = "posted_topics.json"
LOG_FILE = "posts_log.md"
SKIP_MARKER = "AUCUNE_ACTU"

SYSTEM_PROMPT = f"""Tu es un agent d'actualité football, spécialisé dans le football français et européen (Ligue 1, Champions League, Europa League, grands championnats européens).

Ta mission à chaque exécution :
1. Utilise la recherche web pour vérifier s'il y a une actualité football NOTABLE et RÉCENTE (moins de quelques heures) : transfert officialisé, résultat de match important, blessure d'un joueur majeur, déclaration marquante, record battu, décision arbitrale controversée, etc.
2. Compare avec la liste des sujets déjà traités (fournie dans le message utilisateur). Si l'actu la plus intéressante que tu trouves a déjà été traitée, ne la reprends pas.
3. DEUX CAS POSSIBLES :

CAS A — Il y a une vraie actu nouvelle et notable :
Réponds avec un post prêt à publier, dans ce format exact (texte brut, sans markdown) :
---
[Accroche percutante, 1 phrase]

[Corps du texte, 60-120 mots, ton dynamique, factuel]

[Réaction ou mise en perspective, 1-2 phrases]

[3-5 hashtags]
Source : [média/origine de l'info]
TOPIC_ID: [3-6 mots résumant le sujet, pour éviter les doublons futurs]
---

CAS B — Rien de vraiment nouveau ou notable depuis la dernière vérification :
Réponds UNIQUEMENT avec le mot : {SKIP_MARKER}
Ne génère JAMAIS un post artificiel juste pour publier quelque chose. Le silence est préférable à un post creux.

Sois strict sur la notion de "notable" : un simple entraînement ou une rumeur non confirmée ne suffit pas.
"""

def load_topics():
    if os.path.exists(TOPICS_FILE):
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_topics(topics):
    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)

topics = load_topics()
recent_topics = topics[-30:]  # on ne garde que les 30 derniers pour ne pas alourdir le prompt
topics_str = "\n".join(f"- {t['topic']}" for t in recent_topics) if recent_topics else "(aucun sujet traité pour l'instant)"

now_iso = datetime.now(timezone.utc).isoformat()

user_message = f"""Vérifie l'actu football maintenant ({now_iso}).

Sujets déjà traités récemment (ne pas répéter) :
{topics_str}
"""

payload = {
    "model": "claude-sonnet-4-6",
    "max_tokens": 1500,
    "system": SYSTEM_PROMPT,
    "tools": [{"type": "web_search_20250305", "name": "web_search"}],
    "messages": [
        {"role": "user", "content": user_message}
    ],
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

text_blocks = [block["text"] for block in data.get("content", []) if block.get("type") == "text"]
result_text = "\n".join(text_blocks).strip()

if not result_text:
    print("Erreur : aucune réponse texte reçue de l'API.")
    sys.exit(1)

if SKIP_MARKER in result_text:
    print("Rien de notable pour l'instant, pas de post généré.")
    sys.exit(0)

# Extraire le TOPIC_ID pour la déduplication future, sans le laisser dans le post final
topic_id = "sujet non identifié"
lines = result_text.splitlines()
clean_lines = []
for line in lines:
    if line.strip().startswith("TOPIC_ID:"):
        topic_id = line.split("TOPIC_ID:", 1)[1].strip()
    else:
        clean_lines.append(line)
post_text = "\n".join(clean_lines).strip()

timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
log_entry = f"\n\n## ⚽ {timestamp}\n\n{post_text}\n"

if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("# Historique des posts foot générés\n")

with open(LOG_FILE, "a", encoding="utf-8") as f:
    f.write(log_entry)

topics.append({"date": timestamp, "topic": topic_id})
save_topics(topics)

print(f"Nouveau post généré : {topic_id}")
