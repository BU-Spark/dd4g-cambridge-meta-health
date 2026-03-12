# ETL Pipeline GitHub Actions Workflow

This document describes the automated daily ETL pipeline deployment using GitHub Actions.

## Overview

The ETL pipeline is configured to run automatically every day at 2:00 AM UTC. The workflow:

- Fetches the latest dataset metadata from the Cambridge Open Data Portal (Socrata API)
- Evaluates dataset health using both static checks and AI-powered metadata analysis
- Stores results in a SQLite database
- Archives database snapshots as GitHub artifacts

## Workflow File

**Location:** `.github/workflows/etl-pipeline.yml`

## Schedule

The pipeline runs daily at **2:00 AM UTC** (9:00 PM EST / 6:00 PM PST).

To modify the schedule, edit the cron expression in the workflow file:

```yaml
schedule:
  - cron: "0 2 * * *" # minute hour day month day-of-week
```

**Cron syntax examples:**

- `0 2 * * *` - Daily at 2:00 AM UTC
- `0 */6 * * *` - Every 6 hours
- `0 0 * * 0` - Weekly on Sunday at midnight
- `0 0 1 * *` - Monthly on the 1st at midnight

**Tip:** Use [crontab.guru](https://crontab.guru/) to build and validate cron expressions.

## Required GitHub Secrets

The pipeline requires API keys for LLM services used in metadata evaluation. Configure these in your GitHub repository:

### Setting up Secrets

1. Navigate to your GitHub repository
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

| Secret Name         | Description                         | Required?   |
| ------------------- | ----------------------------------- | ----------- |
| `OPENAI_API_KEY`    | OpenAI API key for GPT models       | Optional\*  |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models | Optional\*  |
| `GOOGLE_API_KEY`    | Google API key for Gemini models    | Optional\*  |
| `HUGGINGFACE_TOKEN` | HuggingFace token for model access  | Recommended |

**\*At least one LLM API key is required** for the evaluation step to work properly. The pipeline will use whichever LLM service you have configured.

### Getting API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/settings/keys
- **Google (Gemini)**: https://aistudio.google.com/app/apikey
- **HuggingFace**: https://huggingface.co/settings/tokens

## Manual Execution

You can manually trigger the workflow from the GitHub UI with custom options:

1. Go to **Actions** tab in your repository
2. Select **Daily ETL Pipeline** from the workflows list
3. Click **Run workflow** button
4. Configure options:
   - **ingest_only**: Only fetch data from Socrata API
   - **evaluate_only**: Only run evaluations on existing data
   - **dry_run**: Preview changes without saving to database
5. Click **Run workflow**

## Workflow Steps

The automated workflow performs the following steps:

### 1. Environment Setup

- Checks out the repository code
- Sets up Python 3.11
- Installs dependencies from `ETL/requirements.txt`
- Creates necessary data directories

### 2. Pipeline Execution

Runs the ETL pipeline with the following stages:

- **Ingest**: Fetches latest catalog from Socrata Discovery API
- **Evaluate**: Performs health checks and AI metadata evaluation

### 3. Artifact Management

- **On Success**: Uploads the SQLite database as an artifact (retained for 30 days)
- **On Failure**: Uploads logs and database state for debugging (retained for 7 days)

## Monitoring

### Viewing Workflow Runs

1. Navigate to the **Actions** tab in your GitHub repository
2. Click on **Daily ETL Pipeline**
3. View the list of workflow runs with status indicators:

- Green checkmark: Success
- Red X: Failed
- Yellow circle: In progress

### Checking Logs

To view detailed logs:

1. Click on a specific workflow run
2. Click on the **Execute ETL Pipeline** job
3. Expand individual steps to see their output

### Downloading Artifacts

To download the database or logs:

1. Scroll to the bottom of a workflow run page
2. Find the **Artifacts** section
3. Click on the artifact name to download:
   - `etl-database-{run-number}`: Successful pipeline database
   - `etl-logs-failed-{run-number}`: Logs from failed runs

## Troubleshooting

### Common Issues

#### Pipeline fails with "API key not found"

**Issue:** Missing or incorrect API key configuration.

**Solution:**

1. Verify secrets are configured in GitHub repository settings
2. Ensure secret names match exactly (case-sensitive)
3. Check that at least one LLM API key is valid

#### Pipeline fails during ingest step

**Issue:** Socrata API is unavailable or rate-limited.

**Solution:**

1. Check Socrata API status
2. Review API rate limits
3. Consider adding retry logic or adjusting schedule

#### Database artifact is empty or corrupted

**Issue:** Pipeline crashed before database commit.

**Solution:**

1. Check full logs for Python exceptions
2. Ensure data directory has write permissions
3. Review SQLite database initialization

#### Workflow doesn't run on schedule

**Issue:** Repository may be inactive or workflow is disabled.

**Solution:**

1. Check that workflow is enabled in Actions tab
2. Ensure repository has recent activity (GitHub may disable workflows in inactive repos)
3. Manually trigger workflow to re-enable scheduling

## Notifications

To receive notifications when the pipeline fails:

### Email Notifications

By default, GitHub sends email notifications to repository admins when workflows fail. Configure this in your GitHub notification settings.

### Slack/Discord Integration

Add a notification step to the workflow:

```yaml
- name: Notify Slack on failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
    payload: |
      {
        "text": "ETL Pipeline failed on run ${{ github.run_number }}"
      }
```

## Database Persistence

The workflow creates a fresh database on each run. If you need persistent storage:

### Option 1: Use GitHub Artifacts (Current)

- Database is saved as artifact after each run
- Retained for 30 days
- Download manually when needed

### Option 2: External Database

Modify the pipeline to connect to an external database:

- PostgreSQL on AWS RDS / Azure Database
- Cloud-hosted SQLite (Turso, LiteFS)
- S3/Azure Blob Storage for database file persistence

### Option 3: Repository Commit

Add a step to commit the database back to the repository:

```yaml
- name: Commit database
  run: |
    git config user.name github-actions
    git config user.email github-actions@github.com
    git add ETL/data/cambridge_metadata.db
    git commit -m "Update database from ETL run ${{ github.run_number }}" || true
    git push
```

**Warning:** This increases repository size over time. Consider `.gitignore` entries and periodic cleanup.

## Cost Considerations

### GitHub Actions Minutes

- **Free tier**: 2,000 minutes/month for public repositories
- **Free tier**: 500 minutes/month for private repositories
- This workflow uses approximately 5-10 minutes per run
- Daily runs = ~300 minutes/month

### API Costs

Be aware of costs for:

- **OpenAI GPT models**: ~$0.50-$2.00 per 1M tokens
- **Anthropic Claude**: ~$3.00-$15.00 per 1M tokens
- **Google Gemini**: Free tier available, then ~$0.35 per 1M tokens
- **HuggingFace Inference API**: Free tier available

**Tip:** Start with Google Gemini (free tier) or HuggingFace for cost-effective evaluation.

## Local Testing

Before relying on the automated workflow, test locally:

```bash
# Set environment variables
export OPENAI_API_KEY="your-key-here"
export GOOGLE_API_KEY="your-key-here"

# Navigate to ETL directory
cd ETL

# Run full pipeline
python pipeline.py

# Run specific steps
python pipeline.py --ingest-only
python pipeline.py --evaluate-only

# Test without saving
python pipeline.py --dry-run
```

## Maintenance

### Updating Dependencies

1. Update `ETL/requirements.txt` with new versions
2. Test locally with `pip install -r ETL/requirements.txt`
3. Commit changes - workflow will use new dependencies on next run

### Disabling the Workflow

To temporarily disable the scheduled runs:

1. Go to **Actions** tab
2. Click **Daily ETL Pipeline**
3. Click the **...** menu → **Disable workflow**

To re-enable, follow the same steps and select **Enable workflow**.

## Support

For issues or questions:

- Check workflow logs in the Actions tab
- Review `ETL/README.md` for pipeline-specific documentation
- Open an issue in the repository
- Contact repository maintainers (see `COLLABORATORS` file)

---

**Last Updated:** March 2026
