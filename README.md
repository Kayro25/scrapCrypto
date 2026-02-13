📊 Galxe Quest Ranker

Script em Python que:

🔎 Busca campanhas ativas na API GraphQL da Galxe

🧠 Aplica um sistema de pontuação (score)

💰 Estima probabilidade de payout

📁 Exporta resultados em JSON

🌐 Gera um ranking em HTML

🤖 Envia alertas no Telegram para quests “imperdíveis”



---

🧱 Arquitetura Geral

Fluxo principal:

1. Buscar quests via GraphQL
2. Calcular score
3. Estimar payout
4. Filtrar quests relevantes
5. Exportar JSON
6. Gerar HTML
7. Enviar alertas Telegram


---

⚙️ Configurações

API_URL = "https://graphigo.prd.galaxy.eco/query"

Endpoint GraphQL usado para buscar campanhas.

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

Credenciais do bot Telegram via variáveis de ambiente.

O bot só é ativado se ambas estiverem definidas:

ENABLE_BOT = BOT_TOKEN and CHAT_ID


---

🛰️ Query GraphQL

A query CampaignList busca:

id

name

description

rewardName

startTime

endTime

chain

space:

name

isVerified



Filtros aplicados:

Apenas campanhas Active

Ordenadas por Newest

20 por página

Máximo de 10 páginas



---

🧰 Funções Utilitárias

slugify_space(name)

Transforma nome do projeto em slug URL-friendly.

Exemplo:

"Polygon Labs" → "polygon-labs"


---

build_galxe_url(quest)

Constrói URL pública da quest:

https://app.galxe.com/quest/{space_slug}/{id}


---

notify_telegram(message)

Envia mensagem formatada em HTML para Telegram.

Características:

parse_mode = HTML

Sem preview de link

Timeout de 10 segundos

Falhas são silenciosamente ignoradas



---

📥 Busca de Quests

fetch_quests()

Responsável por:

Paginação com after

Controle de cursor duplicado

Limite de 10 páginas

Evita loop infinito


Retorna:

List[dict]


---

🧠 Sistema de Pontuação

score_quest(quest)

Score baseado em múltiplos fatores.

✅ Projeto Verificado

Condição	Pontos

Verified	+4
Não verificado	-1



---

🎁 Reward

Condição	Pontos

Tem reward	+2
Reward forte (USDT, NFT, Airdrop, etc)	+2
Sem reward	-2



---

🔗 Blockchain

Top Chains (+2):

ETHEREUM

ARBITRUM

OPTIMISM

BASE

POLYGON


Mid Chains (+1):

BSC

AVALANCHE

SOLANA


Outras chains: -1


---

🧠 Tipo da Quest

Palavras positivas:

airdrop

testnet

early

whitelist

reward

points


Máximo: +3


---

🚫 Social-only (penalidade)

Palavras como:

follow

retweet

like

join discord

invite


Cada ocorrência reduz score.


---

⚠️ Palavras suspeitas

guaranteed

instant

claim now

hurry


Cada uma remove -2 pontos.


---

Score final nunca pode ser negativo:

return max(score, 0)


---

💰 Estimativa de Payout

calculate_payout_chance(score)

Score	Payout Estimado

≥ 9	85%
≥ 7	65%
≥ 5	45%
≥ 3	25%
< 3	10%


⚠️ Estimativa heurística, não estatística.


---

📤 Exportação

JSON

Arquivo gerado:

quests_filtradas.json

Contém apenas quests com:

score >= 5

Ordenadas por score (decrescente).


---

HTML

Arquivo gerado:

quests_ranking.html

Contém:

Score

Payout estimado

Nome da quest (linkável)

Projeto

Chain

Reward

Status verificado


Formato simples utilizando <table>.


---

🔥 Sistema de Alerta

Quests consideradas imperdíveis:

score >= 9

Mensagem enviada:

🔥 Quest Imperdível!
Nome
Reward
Score
Payout
Link


---

🚀 Função Principal

main()

Responsável por:

1. Buscar quests


2. Aplicar score


3. Estimar payout


4. Filtrar score ≥ 5


5. Identificar imperdíveis (≥ 9)


6. Exportar JSON


7. Gerar HTML


8. Enviar alertas Telegram


9. Exibir resumo no console




---

📁 Arquivos Gerados

Arquivo	Descrição

quests_filtradas.json	Dados estruturados
quests_ranking.html	Ranking visual



---

🛠 Possíveis Melhorias

Cache local para evitar requisições repetidas

Histórico diário de quests

Comparação com dia anterior

Score baseado em Machine Learning

Interface web com Flask ou FastAPI

Sistema de blacklist

Dashboard interativo (Chart.js)

Integração com Discord



---

🎯 Resumo Final

Este script funciona como um:

> Scanner + Ranker + Notificador automático de oportunidades na Galxe



Transforma dados brutos da API em:

🧠 Análise heurística

📊 Ranking estruturado

🌐 Visualização HTML

🤖 Alertas automatizados
