# GitHub Actions Setup Checklist

Quick-start guide for enabling the automated daily ETL pipeline.

## Prerequisites

- [ ] GitHub repository with push access
- [ ] At least one LLM API key (OpenAI, Anthropic, or Google)
- [ ] HuggingFace account and token (recommended)

## Setup Steps

### 1. Configure GitHub Secrets (Required)

Navigate to: **Repository Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add at least one of these:

- [ ] `OPENAI_API_KEY` - OpenAI API key
- [ ] `ANTHROPIC_API_KEY` - Anthropic API key
- [ ] `GOOGLE_API_KEY` - Google Gemini API key
- [ ] `HUGGINGFACE_TOKEN` - HuggingFace token (recommended)

### 2. Verify Workflow File

- [ ] Confirm `.github/workflows/etl-pipeline.yml` exists
- [ ] Review schedule (default: daily at 2:00 AM UTC)
- [ ] Adjust cron schedule if needed

### 3. Enable Workflow

- [ ] Go to **Actions** tab in repository
- [ ] Find **Daily ETL Pipeline** in workflows list
- [ ] Ensure workflow is enabled (not disabled)

### 4. Test Manual Run

- [ ] Click on **Daily ETL Pipeline** workflow
- [ ] Click **Run workflow** button
- [ ] Select options (or leave defaults)
- [ ] Click **Run workflow**
- [ ] Wait for completion (~5-10 minutes)
- [ ] Verify success (green checkmark)

### 5. Verify Artifacts

- [ ] Click on successful workflow run
- [ ] Scroll to **Artifacts** section
- [ ] Confirm `etl-database-{run-number}` artifact exists
- [ ] Download and inspect database (optional)

## Getting API Keys

### OpenAI

1. Visit https://platform.openai.com/api-keys
2. Sign in or create account
3. Click **Create new secret key**
4. Copy key immediately (won't be shown again)
5. Add as GitHub secret

### Google Gemini (Free Tier Available)

1. Visit https://aistudio.google.com/app/apikey
2. Sign in with Google account
3. Click **Get API key** or **Create API key**
4. Copy the key
5. Add as GitHub secret

### Anthropic

1. Visit https://console.anthropic.com/settings/keys
2. Sign in or create account
3. Click **Create Key**
4. Copy the key
5. Add as GitHub secret

### HuggingFace

1. Visit https://huggingface.co/settings/tokens
2. Sign in or create account
3. Click **New token**
4. Select **Write** access
5. Copy the token
6. Add as GitHub secret

## Monitoring

### Check Workflow Status

- [ ] Go to **Actions** tab regularly
- [ ] Review recent runs for failures
- [ ] Click on runs to see detailed logs

### Enable Email Notifications

- [ ] Go to your GitHub notification settings
- [ ] Enable notifications for **Actions**
- [ ] You'll receive emails on workflow failures

### Download Results

- [ ] Navigate to any successful workflow run
- [ ] Download database artifact from **Artifacts** section
- [ ] Use for analysis or backup

## Troubleshooting

### Workflow doesn't run automatically

- Check workflow is enabled in Actions tab
- Ensure repository has recent activity
- GitHub disables workflows in inactive repositories after 60 days

### Pipeline fails with API key errors

- Verify secrets are configured correctly
- Check secret names match exactly (case-sensitive)
- Ensure API keys are valid and have sufficient credits

### Can't find workflow in Actions tab

- Workflow file might have syntax errors
- Check `.github/workflows/etl-pipeline.yml` exists
- Review YAML syntax (use online YAML validator if needed)

## Next Steps

After successful setup:

1. **Monitor first few runs** - Watch for any issues
2. **Review costs** - Track API usage and GitHub Actions minutes
3. **Adjust schedule** - Change cron timing if needed
4. **Set up notifications** - Configure Slack/Discord webhooks (optional)
5. **Document any customizations** - Update DEPLOYMENT.md with changes

## Support

Full Documentation: [`.github/workflows/DEPLOYMENT.md`](.github/workflows/DEPLOYMENT.md)
ETL Pipeline Details: [`ETL/README.md`](ETL/README.md)
Project Setup: [`Setup.md`](Setup.md)

---
