# Installation — Agent actu foot

## Ce que ça fait
Toutes les heures, l'agent vérifie s'il y a une actualité football notable (transfert, résultat, blessure, déclaration...). S'il trouve quelque chose de vraiment nouveau, il génère un post et l'ajoute à `posts_log.md`. S'il n'y a rien de neuf, il ne fait rien — pas de post creux juste pour publier.

Le fichier `posted_topics.json` garde en mémoire les sujets déjà traités pour éviter les doublons d'une vérification à l'autre.

## Étapes d'installation (10 minutes, gratuit)

1. **Créer un compte GitHub** (si tu n'en as pas) → github.com

2. **Créer un nouveau repository**
   - Nom au choix, ex. `agent-histoires`
   - Le mettre en **privé** si tu ne veux pas que le contenu soit public

3. **Uploader ces fichiers** dans le repo, en gardant la même arborescence :
   ```
   generate_post.py
   .github/workflows/daily-post.yml
   README.md
   ```
   (glisser-déposer sur la page GitHub suffit, ou "Add file" > "Upload files")
   Pas besoin de créer `posted_topics.json` toi-même, le script le crée automatiquement au premier post.

4. **Obtenir une clé API Anthropic**
   - Va sur console.anthropic.com
   - Crée une clé API (section "API Keys")
   - Il faudra un peu de crédit sur le compte (quelques centimes par post généré)

5. **Ajouter la clé comme secret GitHub**
   - Dans ton repo : Settings > Secrets and variables > Actions > New repository secret
   - Nom : `ANTHROPIC_API_KEY`
   - Valeur : ta clé API

6. **C'est prêt.** Le script se lance automatiquement chaque jour à 9h.
   Pour tester tout de suite sans attendre : onglet "Actions" du repo > sélectionner le workflow > "Run workflow"

## Modifier la fréquence de vérification
Dans `.github/workflows/daily-post.yml`, la ligne `cron: "0 * * * *"` définit une vérification toutes les heures. Pour vérifier toutes les 30 min : `*/30 * * * *`. Attention : sur un repo **privé**, GitHub Actions offre 2000 minutes gratuites/mois — au-delà de toutes les 30 min ça peut approcher la limite. Sur un repo **public**, c'est illimité.

## Modifier le style ou le sujet des posts
Tout le comportement de l'agent est dans `generate_post.py`, variable `SYSTEM_PROMPT`. Tu peux l'éditer pour changer le ton, la longueur, ou même revenir aux histoires captivantes générales au lieu du foot.

## Note sur le coût
Chaque vérification consomme un peu de crédit API (recherche web + génération), même quand il n'y a rien à poster. À raison d'une vérification par heure, ça reste de l'ordre de quelques euros par mois — à surveiller sur console.anthropic.com.
