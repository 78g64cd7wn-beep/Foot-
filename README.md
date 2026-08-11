# Installation — Agent actu foot + publication Instagram automatique

## Ce que ça fait
Toutes les heures :
1. L'agent vérifie s'il y a une actu foot notable (transfert, résultat, blessure, déclaration...)
2. S'il trouve quelque chose : il génère un texte + une image, les publie sur GitHub (pour avoir une image accessible publiquement), puis envoie le tout à Buffer qui le publie sur Instagram
3. Si rien de notable : il ne fait rien, pas de post creux

## Fichiers du projet
- `generate_post.py` — vérifie l'actu, génère texte + image
- `publish_to_buffer.py` — envoie le post prêt vers Instagram via Buffer
- `.github/workflows/daily-post.yml` — orchestre le tout chaque heure
- `posts_log.md` — historique de tous les posts générés (créé automatiquement)
- `posted_topics.json` — mémoire anti-doublons (créé automatiquement)
- `images/latest_post.png` — dernière image générée (créée automatiquement)

## Secrets nécessaires (Settings → Secrets and variables → Actions)
- `ANTHROPIC_API_KEY` — clé API Anthropic (déjà configurée)
- `BUFFER_ACCESS_TOKEN` — clé API Buffer (déjà configurée)

## Important : le repo doit rester PUBLIC
Buffer va chercher l'image via une URL publique (`raw.githubusercontent.com`). Si le repo passe en privé, la publication échouera.

## La clé Buffer expire
La clé API Buffer générée a une durée de vie de 30 jours. Il faudra en régénérer une et mettre à jour le secret `BUFFER_ACCESS_TOKEN` à cette échéance.

## Tester manuellement
Repo → onglet Actions → "Vérification actu foot" → Run workflow

## Modifier la fréquence
Dans `.github/workflows/daily-post.yml`, la ligne `cron: "0 * * * *"` = toutes les heures.

## Modifier le style du texte ou de l'image
- Texte : `generate_post.py`, variable `SYSTEM_PROMPT`
- Image : `generate_post.py`, section "Génération de l'image"
