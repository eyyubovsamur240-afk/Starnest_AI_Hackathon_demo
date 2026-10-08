# Escalation Copilot

Starnest Academy AI Hackathon 2026 · Track: **AI for Customer Experience & Digital Services**

A tool for the human agent who takes over when the support **chatbot** gives up. It ranks the escalated chats by churn risk, and for each one shows a 3-line summary, the issue category, sentiment, churn risk with the reason, why the bot failed, a ready-to-send reply in Azerbaijani, a next action and, for customers about to leave, a retention offer. Personal data is masked before anything is sent to the AI model.

## User and problem

**User:** a human support agent at a mobile operator or bank in Azerbaijan (an Azercell-style online support team).

**Problem:** the support chatbot resolves most chats, but the hardest ones get handed over to a human with no context. The agent has to re-read the whole **Bot ↔ Müştəri** conversation, often mixing Azerbaijani, Russian and English, while an angry customer waits. Customers who are about to leave look the same as everyone else in the queue, and nobody tracks why the bot keeps failing.

**What the copilot does** (three tabs, whole UI in Azerbaijani):

1. **🔍 Söhbət təhlili (main screen):** the Bot ↔ Müştəri chat on the left; on the right the **Təhlil et** button, summary, sentiment, churn risk, issue category and a suggested reply. Below it, an **AI dəqiqliyi** block: category and sentiment accuracy from `eval.py`, plus summary (👍/👎) and reply quality (stars) rated by a person in the app.
2. **📥 Prioritet növbəsi (priority queue):** every escalated chat analysed and sorted by churn risk, then sentiment, then waiting time. Click a row to see the customer profile, the chat, why the bot failed, a new FAQ entry for the bot, the next action and a retention offer.
3. **📈 Statistika (dashboard):** complaint categories, why the bot handed over, churn-risk mix, how many chats had personal data masked, and a downloadable list of new FAQ entries for the bot.

For each chat:

| Field | Example |
|---|---|
| Summary (3 lines) | What the customer wants · what already happened · what is still open |
| Category | billing, roaming, tariff, internet_speed, network_coverage, sim_card, refund, other |
| Sentiment | 1 (calm) to 5 (furious) |
| Churn risk + reason | **HIGH**: "Customer threatens to port their number to Bakcell" |
| Suggested reply (AZ) | Editable, copy with one click |
| Next action | refund, tariff_change, escalate_to_tech, unblock_sim, explain_charges, retention_offer, no_action |
| Why the bot failed | not_understood, loop, wrong_answer, missing_knowledge, no_permission, with the reason and a fix tip |
| New FAQ entry for the bot | A question and answer to add to the bot's knowledge base so it handles this case next time |
| Retention offer | Only for high risk, or medium risk with a loyal or high-value customer. Rule-based from the (made-up) CRM profile, with cost and customer value, so the model never invents discounts |
| Privacy | Phone numbers, names, card numbers, e-mails and FIN codes are replaced with `[TELEFON]`, `[AD]`, `[KART]`, `[EMAIL]`, `[FİN]` before the chat leaves the machine. The agent can toggle to see exactly what was sent |

## Quick start

Requires Python 3.10+. The whole interface is in Azerbaijani; the summary, churn-risk reason and reply are generated in Azerbaijani too.

**Windows (PowerShell)**

```powershell
python -m pip install -r requirements.txt
$env:GEMINI_API_KEY="your-key"          # optional, free at aistudio.google.com/apikey
python -m streamlit run app.py
```

`$env:` only lasts for the current PowerShell window. Using `python -m` makes pip and Streamlit run on the same Python when more than one is installed.

**macOS / Linux**

```bash
python3 -m pip install -r requirements.txt
export GEMINI_API_KEY=your-key
python3 -m streamlit run app.py
```

Open http://localhost:8501, pick a sample chat (or paste your own) and click **Təhlil et**. Offline, the whole queue of 40 chats is analysed at once. With an API key, open **Prioritet növbəsi**, pick how many chats to analyse with the slider and click **▶ Növbəni təhlil et** (the free Gemini tier is rate-limited, so the default is 15; results are cached in `.cache/` and open instantly next time).

```bash
# Analyze one chat from the command line
echo "Müştəri: internet yoxdur 3 gündür, Bakcell-ə keçəcəm" | python copilot.py
```

### Offline mode

Without an API key (or with **Oflayn rejim** switched on in the sidebar) the app uses a simple keyword baseline in `copilot.py`. It keeps the demo running if venue Wi-Fi or the API fails, but its replies and FAQ entries are templates and its summary is extractive. If one chat fails in LLM mode, that chat falls back to offline and the queue keeps going. Real results come from the LLM mode.

### Deploy to Streamlit Community Cloud

1. Push this repo to GitHub and create a new app at share.streamlit.io pointing at `app.py`.
2. In **Settings → Secrets** add `GEMINI_API_KEY = "your-key"`. Streamlit exposes top-level secrets as environment variables, so no code change is needed.

## Testing

```bash
python eval.py              # LLM mode (needs GEMINI_API_KEY)
python eval.py --offline    # keyword baseline
python eval.py --limit 5    # quick smoke run
```

`eval.py` runs all 40 tickets in `data/tickets.json`, compares them with the hand-written labels and writes `results/eval_<mode>.md` (ready for the pitch "Proof" slide) plus a JSON file with every prediction and reply.

**Test set** (`data/tickets.json`): 40 synthetic chats between a customer (`Müştəri:`) and the operator's chatbot (`Bot:`), each ending with the bot handing over to a human. Drafted with an AI assistant (review and edit them as a team before submitting). None are taken from a real operator. Each ticket also has a made-up CRM profile (`customer`: name, years as a customer, tariff, monthly fee, contacts in the last 30 days, minutes waiting) and labels for category, churn risk, sentiment and `bot_failure`. Seven chats contain fake personal data (T06, T09, T18, T22, T23, T33, T38) to test masking.

- Languages: Azerbaijani, Russian, English and mixed chats
- Tone: 11 calm, 19 annoyed, 10 furious
- Categories: roaming, internet speed, tariff, SIM card, billing, network coverage, refund
- Tricky cases: sarcasm (T14), two issues in one chat (T15), threatening to switch operator (T16, plus T17–T20), complaint about the bot itself with no technical issue named (T31), a mild switching hint (T33), refund for the customer's own mistake (T36), possible fraud (T38)
- T21–T40 were added later to cover every category (including `other`) and all three risk levels in each language

**Metrics reported:** category accuracy, churn-risk accuracy, sentiment within ±1, bot-failure reason accuracy, chats with personal data masked, average and max response time. Add a 1–5 reply-quality score from 2–3 people outside the team, and a before/after timing (agent reading the raw chat vs. using the tool on 3 chats).

### Results

| Mode | Category | Churn risk | Sentiment ±1 | Bot-failure reason | Avg time |
|---|---|---|---|---|---|
| Offline keyword baseline (40 chats) | 77.5% | 67.5% | 75% | 67.5% | <0.01s |
| LLM (`gemini-2.5-flash`) | _run `python eval.py`_ | | | | |

The offline baseline's keywords were written while looking at T01–T20 (95% / 75% / 90% there), so the drop on T21–T40 shows how much it overfits. It is shown only as a floor. See `results/eval_offline.md` for the cases it misses.

## Project structure

| File | What it does |
|---|---|
| `app.py` | Streamlit UI in Azerbaijani: main analysis screen with the AI accuracy block, priority queue, statistics with charts |
| `copilot.py` | Masks the chat, calls Gemini with structured JSON output (Pydantic schema), caches results, and holds the offline fallback |
| `privacy.py` | Rule-based masking of phone numbers, names, card numbers, e-mails and FIN codes |
| `offers.py` | Rule-based retention offers from the issue category, churn risk and customer profile |
| `prompts.py` | System prompt, category/action/bot-failure vocabulary, 2 few-shot examples |
| `labels_az.py` | Azerbaijani display names for categories, actions, risk levels, sentiment and bot-failure reasons (internal codes stay in English) |
| `data/tickets.json` | 40 synthetic Bot ↔ Müştəri chats with made-up customer profiles and labels |
| `eval.py` | Runs the test set and writes the accuracy table |
| `results/` | Eval outputs |

## Models, libraries, data and tools used

Disclosed as required by section 5 of the Terms & Conditions.

| What | Used for | Licence / terms |
|---|---|---|
| Google Gemini (`gemini-2.5-flash`, configurable via `COPILOT_MODEL`) | Chat analysis and reply generation | Gemini API terms (free tier) |
| [Streamlit](https://streamlit.io) | Web UI | Apache 2.0 |
| [google-genai Python SDK](https://github.com/googleapis/python-genai) | API client, structured output parsing | Apache 2.0 |
| [Pydantic](https://docs.pydantic.dev) | Output schema and validation | MIT |
| [Altair](https://altair-viz.github.io) and [pandas](https://pandas.pydata.org) (installed with Streamlit) | Dashboard charts and tables | BSD-3 |
| Claude Code (AI coding assistant) | Scaffolding of the code, test set and this README | — |
| Data | 40 synthetic chats and customer profiles written for this project. No real customer or operator data. | — |

## Known limitations

- **Synthetic data only.** Accuracy on real operator chats is unknown; 40 tickets is still a small test set.
- **Azerbaijani quality** depends on the model. Replies should always be read by the agent before sending, which is why the reply box is editable.
- **No account access.** The copilot only sees the chat text. It cannot verify balances, charges or tariffs, and is told not to invent amounts.
- **One main category per chat.** When a customer raises two issues (T15) only the one they are most upset about is categorised; the summary should mention both.
- **Churn risk is a judgement, not a prediction model.** It is based on what the customer writes; the profile is only used for the queue order and the retention offer.
- **Masking is a safety net, not a certified anonymiser.** It catches common Azerbaijani phone, card and FIN formats and names introduced with "adım…", "меня зовут…", "my name is…" or known from the profile. A name written any other way can slip through.
- **Retention offers are made-up rules** with made-up prices, to show the idea. A real operator would plug in its own offer catalogue.
- **Latency** depends on network and API load; the offline mode is the fallback for a failing connection.

## Next steps

Pilot with an operator or bank on anonymised chats, real-time mode inside the agent console, CRM integration (account data, past contacts), and a feedback button so agents can correct the category and risk.
