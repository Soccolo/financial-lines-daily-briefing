# Financial Lines Daily Briefing

An automated daily email for a London-based Financial Lines pricing actuary. It selects **7â€“8** material
industry developments, explains their pricing relevance, and adds a rotating tutorial covering pricing
models, data science, LLMs, or actuarial practice.

The workflow runs on GitHub Actions, so your computer and Codex do not need to remain open.

## What it does

- Searches fresh public news across actuarial/pricing, cyber, M&A, D&O, PI, FI, Accident & Health,
  insurance industry news, and legislation/regulation.
- Ranks and deduplicates stories locally before using the model.
- Fetches up to 14 short article extracts and makes **one OpenAI API call per day**.
- Produces exactly 8 stories by default, five executive bullets, pricing implications, direct sources,
  2â€“3 watch items, and one worked tutorial.
- Checks the previous seven days of Gmail Sent mail and excludes previously used URLs when IMAP is available.
- Sends a multipart plain-text and HTML email through Gmail.

## Token and cost controls

The default model is `gpt-5.6-luna`, OpenAI's current model for cost-sensitive, high-volume workloads. The code
does the expensive-looking workâ€”search, ranking, deduplication, article fetching and trimmingâ€”without a
model. Only 14 extracts of at most 2,200 characters enter one request, and the output is capped at 5,000
tokens. If absolute minimum spend matters more than capability, `gpt-5-nano` is cheaper; however, it may be
less reliable for nuanced pricing implications and mathematical tutorials.

## One-time setup

### 1. Create an OpenAI API key

Create a key in the [OpenAI API dashboard](https://platform.openai.com/api-keys). API billing is separate
from a ChatGPT subscription.

### 2. Create a Gmail app password

1. Enable 2-Step Verification on the Gmail account used to send the briefing.
2. Open [Google App Passwords](https://myaccount.google.com/apppasswords).
3. Create an app password named `Financial Lines Briefing`.
4. Save the 16-character password; use it as `GMAIL_APP_PASSWORD`, not your normal Gmail password.

### 3. Add GitHub Actions secrets

In this repository, open **Settings â†’ Secrets and variables â†’ Actions â†’ New repository secret** and add:

| Secret | Value |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `GMAIL_USERNAME` | The Gmail address that sends the email |
| `GMAIL_APP_PASSWORD` | The Gmail app password |
| `EMAIL_TO` | The recipient email address |

No secrets or email addresses should be committed to the repository.

### 4. Send a test briefing

Open **Actions â†’ Daily Financial Lines Briefing â†’ Run workflow**. The scheduled job runs daily at around
07:00 Europe/London. GitHub may start scheduled workflows a few minutes late.

## Configuration

Optional repository variables can be added under **Settings â†’ Secrets and variables â†’ Actions â†’ Variables**:

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_MODEL` | `gpt-5.6-luna` | Model used for the single daily generation call |

Set `ARTICLE_COUNT` in the workflow to `7` if you prefer seven articles. The default is eight.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements-dev.txt -e .
pytest -q
python -m briefing.main
```

Copy `.env.example` values into your shell environment before a local run. The application intentionally
does not auto-load `.env`, reducing the chance of accidentally using a local secret in automation.

## Reliability notes

- Google News RSS and publisher pages can change or block automated access. Failed pages fall back to the
  RSS snippet; a single publisher failure does not abort the whole briefing.
- Some stories may be behind paywalls. The email links to the source but does not attempt to bypass access controls.
- Gmail IMAP deduplication is best-effort. If it is unavailable, within-run title deduplication still applies.
- The output is an intelligence aid, not actuarial, legal, underwriting, or investment advice. Verify material
  developments against primary sources before business use.

