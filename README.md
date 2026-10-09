# Escalation Copilot

Starnest Academy AI Hackathon 2026 · Track: **AI for Customer Experience & Digital Services**

**Every chat the support bot gives up on becomes two things: a fast, informed answer from a human agent, and a lesson that stops the bot failing the same way again.**

| Submission item | Where |
|---|---|
| Demo link | _Streamlit Community Cloud link: to be added_ ([run it locally](#how-to-open-the-demo) in two commands) |
| Video (≤ 2 min) | _to be added_ |
| Pitch deck | Uploaded on the hackathon dashboard |
| User and problem | [below](#user-and-problem) |
| Quality testing results | [below](#quality-testing) · `results/` · `tests/` |
| Models, data and components used | [Disclosure](#disclosure-models-data-components-and-ai-assistants) |

## User and problem

**User:** the human support agent at a mobile operator in Azerbaijan (an Azercell-style online support team) who takes over when the chatbot hands a chat over.

**What goes wrong today:**

- The bot resolves the easy chats; the hardest ones land on a human **with no context**. The agent re-reads the whole Bot ↔ Müştəri conversation, often mixing Azerbaijani, Russian and English, while an already angry customer waits.
- The queue is first-come, first-served. A customer who says "I'm moving to Bakcell" looks the same as a calm question about roaming.
- Nobody records **why the bot failed**, so the same handover happens again tomorrow.

**Outcome when it is solved:** the agent sees what the customer wants, how upset they are and whether they are about to leave in a few seconds, starts from a ready Azerbaijani reply, handles the customers at risk of leaving first, and the bot team gets a ready FAQ entry for every gap. How much time this saves is measured in [Comparison with today's approach](#comparison-with-todays-approach).

## Prototype: the core scenario

Three pages in the sidebar; the whole interface is in Azerbaijani.

1. **🔍 Söhbət təhlili (main screen).** Pick an escalated chat (or paste one) and click **Təhlil et**. The agent gets a 3-line summary, sentiment (1–5), churn risk with the reason, the issue category and an editable reply in Azerbaijani. Below it, the **AI dəqiqliyi** block shows the eval scores and lets the agent rate the summary (👍/👎) and reply (stars).
2. **📥 Prioritet növbəsi (priority queue).** Every escalated chat analysed and ordered by churn risk, then sentiment, then waiting time. Opening a row shows the customer profile, why the bot failed, a new FAQ entry for the bot, the next action and, for customers at risk, a retention offer.
3. **📈 Statistika (dashboard).** Complaint categories, why the bot handed over, churn-risk mix, chats with personal data masked, and a downloadable list of new FAQ entries.

### What the AI contributes, and what it doesn't

| Step | Done by | Why |
|---|---|---|
| Mask phones, names, cards, e-mails and FIN codes | Rules (`privacy.py`) | Personal data must not leave the machine; rules are predictable and auditable |
| Summary, category, sentiment, churn risk and reason, why the bot failed, FAQ entry, AZ reply, next action | **Gemini** (`gemini-3.8-flash`, `copilot.py`, `prompts.py`), structured JSON checked against a Pydantic schema | Needs reading mixed-language, sarcastic, misspelled chats, which keyword rules do badly (see the eval below) |
| Queue order | Rules on Gemini's output plus waiting time | Transparent to the agent |
| Retention offer | Rules (`offers.py`) on Gemini's risk + the CRM profile | The model never invents discounts or prices |
| Offline fallback | Keyword rules | Keeps the demo working if the API or Wi-Fi fails; every result shows a 🤖 Gemini or ⚙️ Oflayn badge so it's always clear who decided |

The answer key in `data/tickets.json` (`expected`) is only read by `eval.py` after the analysis to score it. It is never sent to Gemini or shown in the app, and `tests/test_copilot.py` checks that.

## Quality testing

### Test set

`data/tickets.json`: 40 synthetic chats between a customer (`Müştəri:`) and the operator's bot (`Bot:`), each ending in a handover, with a made-up CRM profile and a hand-written answer key (category, churn risk, sentiment, bot-failure reason).

- Languages: Azerbaijani, Russian, English and mixed. Tone: 11 calm, 19 annoyed, 10 furious. Churn risk: 11 low, 18 medium, 11 high.
- Tricky cases: sarcasm (T14), two issues in one chat (T15), threats to switch operator (T16–T20), a complaint about the bot itself (T31), a mild switching hint (T33), a refund for the customer's own mistake (T36), possible fraud (T38).
- Seven chats contain fake personal data to test masking (T06, T09, T18, T22, T23, T33, T38).

### Automated tests

`pytest` (82 tests, run in CI on every push):

- `tests/test_privacy.py`: every phone format, card, e-mail, FIN code and name pattern is masked; all 7 test chats with personal data come out with no name or phone left.
- `tests/test_offers.py`: no offer at low risk; medium risk only for loyal or high-value customers; high risk always gets a priced offer.
- `tests/test_copilot.py`: the test set is well formed; the output always fits the schema; only the masked chat is sent to Gemini; the answer key never reaches the prompt.
- `tests/test_quota_and_cache.py`: each chat costs one Gemini request and is never sent twice; a daily-quota 429 stops at once (no retries), a 503 is retried after 5, 15 and 30 s, the next model in `GEMINI_MODEL` takes over when one runs out or stays busy, and an interrupted eval still writes a report marked as a sample.

### Accuracy (`python eval.py`)

| Mode | Category | Churn risk | Sentiment ±1 | Bot-failure reason | Avg time | Cost / chat |
|---|---|---|---|---|---|---|
| Keyword rules (offline baseline, 40 chats) | 77.5% | 67.5% | 75% | 67.5% | <0.01 s | 0 |
| Gemini `gemini-3.8-flash` (40 chats) | _run `python eval.py`_ | | | | | |

The keyword rules were written while looking at T01–T20 (95% / 75% / 90% on those), so they overfit: they are shown only as the floor that the AI has to beat. Full per-chat results are in `results/eval_<mode>.json`.

### Examples of failures

From the keyword baseline (`results/eval_offline.md` lists all 16 misses):

| Chat | What happened | Why it matters |
|---|---|---|
| T14, sarcasm: "Wow, əla xidmətdir, 3 gündür internet yoxdur 👏" | Rules read churn risk as **low**; the answer key says medium. The bot itself thanked the customer for "positive feedback" | Words like "əla" fool keywords; this is what the model has to read correctly |
| T31, complaint about the bot: "SİZİN BOTUNUZ MƏNİ DƏLİ EDİR!!!" | Rules picked **tariff** (from the bot's menu text); the answer is other | Bot text pollutes keyword matching |
| T38, possible fraud: calls to Somalia at 3 am | Rules picked **roaming / low**; the answer is billing / medium | A worried, polite customer can still be at risk |
| T15, two issues in one chat | Rules picked billing; the answer is refund | Only one main category per chat; the summary must mention both |

Gemini's own misses are written to `results/eval_llm.md` by the same script; the ones worth discussing go here once the run is done.

### Comparison with today's approach

Today the agent reads the raw chat and writes a reply from scratch. Protocol: 2–3 people outside the team each handle the same 3 chats twice, once with the raw chat only and once with the copilot, and record the seconds until they have a reply ready plus a 1–5 quality score for the reply (scored by someone who didn't write it).

| | Raw chat (today) | With Escalation Copilot |
|---|---|---|
| Seconds to understand the chat and have a reply ready | _to be measured_ | _to be measured_ |
| Reply quality (1–5) | _to be measured_ | _to be measured_ |
| Customers at risk of leaving spotted | Only if the agent reads that far | Flagged and moved to the top of the queue |
| Why the bot failed recorded | No | Reason + FAQ entry for every handover |

## Feasibility

**Data requirements.** For a pilot: an export of escalated bot chats (anonymised or masked with `privacy.py`), the operator's issue categories, and its real retention-offer catalogue to replace the made-up one in `offers.py`. No model training is needed: the prompt, the category list and 2 few-shot examples are the whole set-up. A few hundred labelled chats would replace our 40 synthetic ones as the test set.

**Running costs.** The demo runs on the Gemini free tier, so it costs nothing. On the paid tier, `eval.py` records the tokens Gemini reports for every chat and prints the cost per chat and per 1,000 chats at the price set in `GEMINI_PRICE_IN` / `GEMINI_PRICE_OUT` (USD per 1M tokens; the defaults are the older gemini-2.5-flash list price of $0.30 / $2.50, so set the current price for your model from [ai.google.dev/pricing](https://ai.google.dev/pricing)). One chat costs **one** Gemini request (one call returns every field), and every answer is saved to `results/gemini_cache.json`, so re-opening a chat or re-running the eval costs nothing. Hosting is a single Streamlit app.

**Free-tier limit.** On the free tier Google allows only **20 requests a day** for `gemini-3.8-flash` (quota `GenerateRequestsPerDayPerProjectPerModel-FreeTier`), so the 40-chat eval needs two days or a billed key. When the limit is hit, `eval.py` stops with one message and writes a report from the chats that finished, marked partial, and the app shows a message in Azerbaijani and switches to the ⚙️ offline rules. Saved answers keep working either way. The limit is per Google Cloud project and per model, so a second key in the same project shares it; `eval.py` prints which key it uses (source and last 4 characters). Because each model has its own quota, `GEMINI_MODEL` takes a comma-separated fallback list (`python eval.py --list-models` shows what the key can use): when one model's daily limit is used up, or it stays busy (503) after its retries, the next model answers. The saved answer and the report record which model answered each chat, and the report shows the keyword rules on the same chats next to Gemini, so a partial run is still a fair, labelled sample.

**Next step.** A 2-week shadow pilot with one support team: the copilot runs next to the agents on real escalated chats, agents rate each summary and reply in the app, and we compare handling time and the bot's handover rate before and after adding the generated FAQ entries.

## What is different

Most support copilots summarise a chat and suggest a reply. Escalation Copilot is built for the moment **the bot fails**:

- **It closes the loop to the bot.** Every handover gets a reason (not understood, loop, wrong answer, missing knowledge, no permission) and a ready question-and-answer to add to the bot's knowledge base, exportable from the dashboard. The fewer handovers, the less the agents need the tool at all.
- **It ranks the queue by who is about to leave**, not by arrival time, and pairs high-risk customers with a priced, rule-based retention offer.
- **It works in the languages Azerbaijani customers actually mix**, AZ/RU/EN in one chat, and always answers in Azerbaijani.
- **Personal data is masked before the model sees it**, and the agent can toggle to see exactly what was sent.

## How to open the demo

**Online:** the Streamlit Community Cloud link at the top. Nothing to install.

**Locally** (Python 3.10+). Windows PowerShell:

```powershell
python -m pip install -r requirements.txt
$env:GEMINI_API_KEY="your-key"          # optional, free at aistudio.google.com/apikey
python -m streamlit run app.py
```

macOS / Linux:

```bash
python3 -m pip install -r requirements.txt
export GEMINI_API_KEY=your-key
python3 -m streamlit run app.py
```

Open http://localhost:8501, pick a sample chat and click **Təhlil et**. Without a key (or with **Oflayn rejim** on in the sidebar) the app uses the keyword fallback. Sample chats that already have a saved Gemini answer in `results/gemini_cache.json` open instantly with the 🤖 Gemini badge, even without a key, and cost no quota; only a new pasted chat (or a sample with no saved answer) calls Gemini live. With a key, open **Prioritet növbəsi**, choose how many chats to analyse and click **▶ Növbəni təhlil et** to fill in the missing ones (the free tier allows 20 requests a day, see [Feasibility](#feasibility)).

**Deploy to Streamlit Community Cloud:** create an app at share.streamlit.io pointing at `app.py`, then add `GEMINI_API_KEY = "your-key"` (and optionally `GEMINI_MODEL = "gemini-3.8-flash"`) under **⋮ → Settings → Secrets**.

**Tests and eval:**

```bash
python -m pytest -q          # 82 automated tests, no key needed
python eval.py --offline     # keyword baseline -> results/eval_offline.*
python eval.py               # Gemini -> results/eval_llm.*; only chats without a saved answer call the API
python eval.py --limit 5     # quick Gemini check on 5 chats
python eval.py --list-models # models this key can use; chain them: GEMINI_MODEL="model-a,model-b"
```

## Disclosure: models, data, components and AI assistants

Required by rules 03 and 04 of the hackathon.

| What | Used for | Licence / terms |
|---|---|---|
| Google Gemini (`gemini-3.8-flash`, configurable via `GEMINI_MODEL`) | Chat analysis and reply generation | Gemini API terms (free tier). Free-tier inputs may be used by Google to improve its models, so only synthetic chats are sent. |
| [Streamlit](https://streamlit.io) | Web UI and hosting (Community Cloud) | Apache 2.0 |
| [google-genai Python SDK](https://github.com/googleapis/python-genai) | API client and structured output | Apache 2.0 |
| [Pydantic](https://docs.pydantic.dev) | Output schema and validation | MIT |
| [Altair](https://altair-viz.github.io), [pandas](https://pandas.pydata.org) | Dashboard charts and tables | BSD-3 |
| [pytest](https://pytest.org), [ruff](https://docs.astral.sh/ruff/) | Tests and lint in CI | MIT |
| Claude Code (Anthropic's AI coding assistant) | Wrote most of the code, the 40 synthetic test chats and this README, reviewed and directed by the team | — |
| Data | 40 synthetic chats and customer profiles written for this project with an AI assistant. No real customer or operator data. Retention offers and prices are made up. | — |
| Templates | None | — |

**Project history.** The prototype was started on **2026-10-08** in a separate test repository ([eyyubovsamur240-afk/test](https://github.com/eyyubovsamur240-afk/test)) and merged into this repository on 2026-10-09 with its full commit history and original dates, so the timeline can be checked. Work after the start (automated tests, token and cost logging, this write-up) is in the later commits.

## Known limitations

- **Synthetic data only.** Accuracy on real operator chats is unknown; 40 chats is a small test set.
- **Azerbaijani quality** depends on the model. The agent should always read a reply before sending it, which is why the reply box is editable.
- **No account access.** The copilot only sees the chat. It cannot check balances, charges or tariffs, and is told not to invent amounts.
- **One main category per chat.** With two issues (T15) only the one the customer is most upset about is categorised.
- **Churn risk is a judgement, not a prediction model.** It comes from what the customer writes; the profile is only used for queue order and the offer.
- **Masking is a safety net, not a certified anonymiser.** A name written in an unusual way can slip through.
- **Ratings in the app live only in the browser session.**
- **Latency** depends on the network and API load (gemini-3.8-flash took 35–90 s per chat on the free tier); offline mode is the fallback.
- **Free-tier quota:** 20 Gemini requests a day. Saved answers in `results/gemini_cache.json` cover the sample chats; new chats need quota or a billed key.

## Project structure

| File | What it does |
|---|---|
| `app.py` | Main screen: chat left, analysis right, AI accuracy block below |
| `pages/1_queue.py` | Priority queue with the full analysis of the selected chat |
| `pages/2_stats.py` | Dashboard: charts and FAQ export |
| `copilot_ui.py` | Shared styles, sidebar links and building blocks for the pages |
| `copilot.py` | Masks the chat, calls Gemini once with a JSON schema, saves every answer to `results/gemini_cache.json`, handles quota and model errors, holds the offline fallback |
| `privacy.py` | Rule-based masking of personal data |
| `offers.py` | Rule-based retention offers |
| `prompts.py` | System prompt, vocabularies and 2 few-shot examples |
| `labels_az.py` | Azerbaijani display names (internal codes stay in English) |
| `data/tickets.json` | 40 synthetic chats with profiles and the answer key |
| `eval.py` | Runs the test set, writes accuracy, misses, tokens and cost to `results/` |
| `tests/` | Automated tests |
