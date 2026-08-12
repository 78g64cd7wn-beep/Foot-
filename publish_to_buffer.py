"""
Agent IA - Actu foot (étape 2/2).
Lit pending.json (créé par generate_post.py) et publie sur Instagram via Buffer.
Doit être lancé APRÈS que l'image ait été poussée sur GitHub (pour avoir une URL publique).
"""

import os
import sys
import json
import urllib.request

BUFFER_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")  # format: owner/repo
PENDING_FILE = "pending.json"
TOPICS_FILE = "posted_topics.json"

if not os.path.exists(PENDING_FILE):
    print("Rien à publier ce cycle.")
    sys.exit(0)

if not BUFFER_TOKEN:
    print("Erreur : BUFFER_ACCESS_TOKEN n'est pas définie.")
    sys.exit(1)

if not GITHUB_REPOSITORY:
    print("Erreur : GITHUB_REPOSITORY n'est pas définie.")
    sys.exit(1)

with open(PENDING_FILE, "r", encoding="utf-8") as f:
    pending = json.load(f)

image_url = f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main/{pending['image_path']}"


def graphql(query, variables=None):
    body = {"query": query}
    if variables:
        body["variables"] = variables
    req = urllib.request.Request(
        "https://api.buffer.com",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {BUFFER_TOKEN}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


# --- FIX : "organizations" est un champ de "account", pas une query racine ---
org_result = graphql("query { account { organizations { id } } }")
orgs = org_result.get("data", {}).get("account", {}).get("organizations", [])
if not orgs:
    print(f"Erreur : aucune organisation trouvée. Réponse : {org_result}")
    sys.exit(1)
organization_id = orgs[0]["id"]

channels_query = """
query GetChannels($orgId: OrganizationId!) {
  channels(input: { organizationId: $orgId }) {
    id
    name
    service
  }
}
"""
channels_result = graphql(channels_query, {"orgId": organization_id})
channels = channels_result.get("data", {}).get("channels", [])
instagram_channel = next((c for c in channels if c.get("service", "").lower() == "instagram"), None)

if not instagram_channel:
    print(f"Erreur : aucun channel Instagram trouvé parmi {channels}")
    sys.exit(1)

channel_id = instagram_channel["id"]

create_post_mutation = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess {
      post { id text dueAt }
    }
    ... on MutationError {
      message
    }
  }
}
"""
variables = {
    "input": {
        "text": pending["caption"],
        "channelId": channel_id,
        "schedulingType": "automatic",
        "mode": "addToQueue",
        "assets": [{"image": {"url": image_url}}],
    }
}

result = graphql(create_post_mutation, variables)
create_result = result.get("data", {}).get("createPost", {})

if "message" in create_result:
    print(f"Échec de la publication : {create_result['message']}")
    sys.exit(1)

if "post" not in create_result:
    print(f"Réponse inattendue de Buffer : {result}")
    sys.exit(1)

print(f"Post ajouté à la file Buffer pour Instagram : {create_result['post']}")

topics = []
if os.path.exists(TOPICS_FILE):
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        topics = json.load(f)
topics.append({"topic": pending["topic_id"]})
with open(TOPICS_FILE, "w", encoding="utf-8") as f:
    json.dump(topics, f, ensure_ascii=False, indent=2)
