# Escalation Copilot

Starnest Academy AI Hackathon 2026 · Track: **AI for Customer Experience & Digital Services**

A one-page tool that turns an escalated support chat into a 3-line summary, an issue category, a sentiment score, a churn-risk flag with the reason, a ready-to-send reply in Azerbaijani, and one next action, in under 10 seconds.

## User and problem

**User:** a human support agent at a mobile operator or bank in Azerbaijan (an Azercell-style online support team).

**Problem:** the support chatbot resolves most chats, but the hardest ones get escalated to a human with no context. The agent has to re-read 30–40 messages, often mixing Azerbaijani, Russian and English, while an angry customer waits. Customers who are about to leave look the same as everyone else in the queue.

**What the copilot does:** paste the chat, click **Analyze**, and get:

| Field | Example |
|---|---|
| Summary (3 lines) | What the customer wants · what already happened · what is still open |
| Category | billing, roaming, tariff, internet_speed, network_coverage, sim_card, refund, other |
| Sentiment | 1 (calm) to 5 (furious) |
| Churn risk + reason | **HIGH**: "Customer threatens to port their number to Bakcell" |
| Suggested reply (AZ) | Editable, copy with one click |
| Next action | refund, tariff_change, escalate_to_tech, unblock_sim, explain_charges, retention_offer, no_action |

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

Open http://localhost:8501, pick a sample chat (or paste your own) and click **Təhlil et**.

```bash
# Analyze one chat from the command line
echo "Customer: internet yoxdur 3 gündür, Bakcell-ə keçəcəm" | python copilot.py
```

### Offline mode

Without an API key (or with **Oflayn rejim** switched on in the sidebar) the app uses a simple keyword baseline in `copilot.py`. It keeps the demo running if venue Wi-Fi or the API fails, but its replies are templates and its summary is extractive. Real results come from the LLM mode.

### Deploy to Streamlit Community Cloud

1. Push this repo to GitHub and create a new app at share.streamlit.io pointing at `app.py`.
2. In **Settings → Secrets** add `GEMINI_API_KEY = "your-key"`. Streamlit exposes top-level secrets as environment variables, so no code change is needed.

## Testing

```bash
python eval.py              # LLM mode (needs GEMINI_API_KEY)
python eval.py --offline    # keyword baseline
python eval.py --limit 5    # quick smoke run
```

`eval.py` runs all 20 tickets in `data/tickets.json`, compares them with the hand-written labels and writes `results/eval_<mode>.md` (ready for the pitch "Proof" slide) plus a JSON file with every prediction and reply.

**Test set** (`data/tickets.json`): 20 synthetic escalated chats drafted with an AI assistant (review and edit them as a team before submitting). None are taken from a real operator.

- Languages: Azerbaijani, Russian, English and mixed chats
- Tone: 5 calm, 10 annoyed, 5 furious
- Categories: roaming, internet speed, tariff, SIM card, billing, network coverage, refund
- Tricky cases: sarcasm (T14), two issues in one chat (T15), threatening to switch operator (T16, plus T17–T20)

**Metrics reported:** category accuracy, churn-risk accuracy, sentiment within ±1, average and max response time. Add a 1–5 reply-quality score from 2–3 people outside the team, and a before/after timing (agent reading the raw chat vs. using the tool on 3 chats).

### Results

| Mode | Category | Churn risk | Sentiment ±1 | Avg time |
|---|---|---|---|---|
| Offline keyword baseline | 95% | 75% | 90% | <0.01s |
| LLM (`gemini-2.5-flash`) | _run `python eval.py`_ | | | |

The offline baseline's keywords were written while looking at this same test set, so its scores are optimistic and are shown only as a floor. See `results/eval_offline.md` for the cases it misses.

## Project structure

| File | What it does |
|---|---|
| `app.py` | Streamlit UI in Azerbaijani: sample-chat dropdown, paste box, **Təhlil et** button, risk / category / sentiment cards, summary, next step, editable reply, "time saved" counter |
| `labels_az.py` | Azerbaijani display names for categories, actions, risk levels and sentiment (internal codes stay in English) |
| `copilot.py` | Builds the request, calls Gemini with structured JSON output (Pydantic schema), and holds the offline fallback |
| `prompts.py` | System prompt, category/action vocabulary, 2 few-shot examples |
| `data/tickets.json` | 20 synthetic chats with labels (category, churn risk, sentiment) |
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
| Claude Code (AI coding assistant) | Scaffolding of the code, test set and this README | — |
| Data | 20 synthetic chats written for this project. No real customer or operator data. | — |

## Known limitations

- **Synthetic data only.** Accuracy on real operator chats is unknown; 20 tickets is a small test set.
- **Azerbaijani quality** depends on the model. Replies should always be read by the agent before sending, which is why the reply box is editable.
- **No account access.** The copilot only sees the chat text. It cannot verify balances, charges or tariffs, and is told not to invent amounts.
- **One main category per chat.** When a customer raises two issues (T15) only the one they are most upset about is categorised; the summary should mention both.
- **Churn risk is a judgement, not a prediction model.** It is based on what the customer writes, not on customer history.
- **Latency** depends on network and API load; the offline mode is the fallback for a failing connection.

## Next steps

Pilot with an operator or bank on anonymised chats, real-time mode inside the agent console, CRM integration (account data, past contacts), and a feedback button so agents can correct the category and risk.
