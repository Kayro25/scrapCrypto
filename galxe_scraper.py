import requests
import json
from datetime import datetime, date

# ==============================
# CONFIG
# ==============================

API_URL = "https://graphigo.prd.galaxy.eco/query"

HEADERS = {
    "content-type": "application/json",
    "origin": "https://app.galxe.com",
    "referer": "https://app.galxe.com/",
    "platform": "web",
    "user-agent": "Mozilla/5.0"
}

QUERY = """
query CampaignList($input: ListCampaignInput!) {
  campaigns(input: $input) {
    pageInfo {
      endCursor
      hasNextPage
    }
    list {
      id
      name
      description
      rewardName
      startTime
      endTime
      chain
      space {
        name
        isVerified
      }
    }
  }
}
"""

# ==============================
# GALXE SCRAPER
# ==============================

def fetch_quests():
    all_campaigns = []
    after = "-1"
    seen_cursors = set()
    max_pages = 10
    page = 0

    while page < max_pages:
        page += 1

        variables = {
            "input": {
                "listType": "Newest",
                "statuses": ["Active"],
                "first": 20,
                "after": after,
                "isRecurring": False
            }
        }

        payload = {
            "operationName": "CampaignList",
            "query": QUERY,
            "variables": variables
        }

        try:
            resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print("Erro ao buscar dados:", e)
            break

        if "errors" in data:
            print("Erro na API Galxe:")
            print(json.dumps(data, indent=2))
            break

        campaigns = data["data"]["campaigns"]["list"]
        page_info = data["data"]["campaigns"]["pageInfo"]

        if not campaigns:
            break

        all_campaigns.extend(campaigns)

        end_cursor = page_info["endCursor"]
        if end_cursor in seen_cursors or not page_info["hasNextPage"]:
            break

        seen_cursors.add(end_cursor)
        after = end_cursor

    return all_campaigns

# ==============================
# SCORE AVANÇADO
# ==============================

def score_quest(quest):
    score = 0

    name = (quest.get("name") or "").lower()
    desc = (quest.get("description") or "").lower()
    reward = (quest.get("rewardName") or "").lower()
    chain = (quest.get("chain") or "").upper()
    verified = quest["space"].get("isVerified", False)

    text = f"{name} {desc} {reward}"

    # Confiança
    if verified:
        score += 4
    else:
        score -= 1

    # Reward
    if reward:
        score += 2
        strong_rewards = ["usdt", "usdc", "eth", "btc", "$", "token", "airdrop", "nft"]
        if any(w in reward for w in strong_rewards):
            score += 2
    else:
        score -= 2

    # Chains
    top_chains = ["ETHEREUM", "ARBITRUM", "OPTIMISM", "BASE", "POLYGON"]
    mid_chains = ["BSC", "AVALANCHE", "SOLANA"]

    if chain in top_chains:
        score += 2
    elif chain in mid_chains:
        score += 1
    else:
        score -= 1

    # Tipo de campanha
    good_types = ["airdrop", "testnet", "early", "whitelist", "incentive", "reward", "points"]
    score += min(3, sum(1 for w in good_types if w in text))

    # Social farming
    social_only = ["follow", "retweet", "like", "join discord", "invite", "comment"]
    if any(w in text for w in social_only) and not reward:
        score -= 4
    else:
        score -= sum(1 for w in social_only if w in text)

    # Scam / bait
    scam_words = [
        "guaranteed", "instant reward", "100% free",
        "limited now", "act now", "claim now", "hurry up"
    ]
    score -= sum(2 for w in scam_words if w in text)

    if not verified and any(w in reward for w in ["btc", "eth", "1000", "5000", "100000"]):
        score -= 4

    # Projeto obscuro
    if not verified and not reward:
        score -= 3

    return max(score, 0)

# ==============================
# CLASSIFICAÇÃO
# ==============================

def classify(score):
    if score >= 9:
        return "🔥 Imperdível"
    elif score >= 7:
        return "⭐ Excelente"
    elif score >= 5:
        return "✅ Boa"
    elif score >= 3:
        return "⚠️ Mediana"
    else:
        return "❌ Ruim"

# ==============================
# EXPORT HTML
# ==============================

def export_html(quests):
    rows = ""
    for q in quests:
        rows += f"""
        <tr>
            <td>{q['score']}</td>
            <td>{classify(q['score'])}</td>
            <td>{q['name']}</td>
            <td>{q['space']['name']}</td>
            <td>{q['chain']}</td>
            <td>{q['rewardName'] or '-'}</td>
            <td>{'✔️' if q['space']['isVerified'] else '❌'}</td>
        </tr>
        """

    html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>Ranking de Quests Galxe</title>
<style>
body {{ font-family: Arial; background: #0d1117; color: #c9d1d9; padding: 20px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #30363d; padding: 8px; text-align: left; }}
th {{ background: #161b22; }}
tr:nth-child(even) {{ background: #161b22; }}
h1 {{ color: #58a6ff; }}
</style>
</head>
<body>
<h1>📊 Ranking de Quests Galxe</h1>
<p>Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
<table>
<tr>
<th>Score</th>
<th>Classificação</th>
<th>Quest</th>
<th>Projeto</th>
<th>Chain</th>
<th>Reward</th>
<th>Verificado</th>
</tr>
{rows}
</table>
</body>
</html>
"""

    with open("quests_ranking.html", "w", encoding="utf-8") as f:
        f.write(html)

# ==============================
# MAIN
# ==============================

def main():
    print("🔎 Buscando quests...")
    quests = fetch_quests()

    for quest in quests:
        quest["score"] = score_quest(quest)

    filtered = [
        q for q in quests
        if q["score"] >= 5 and (q["space"]["isVerified"] or q["rewardName"])
    ]

    filtered.sort(key=lambda q: q["score"], reverse=True)

    today = date.today().isoformat()

    with open("quests_filtradas.json", "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    with open(f"quests_filtradas_{today}.json", "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    export_html(filtered)

    print(f"✅ {len(filtered)} quests salvas")
    print("🌐 Arquivo visual gerado: quests_ranking.html")

if __name__ == "__main__":
    main()
