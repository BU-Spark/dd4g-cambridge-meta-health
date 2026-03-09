# Dataset Documentation — Cambridge Open Data Meta Health Dashboard

---

## Project Information

**What is the project name?**
Cambridge Open Data Meta Health Dashboard

**What is the link to your project's GitHub repository?**
https://github.com/BU-Spark/dd4g-cambridge-meta-health

**What is the link to your project's Google Drive folder?**
https://bushare-my.sharepoint.com/personal/zcranmer_bu_edu/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fzcranmer%5Fbu%5Fedu%2FDocuments%2FMassMutual%20%2D%20CDS%20Shared%20Folder%2FData%20Days%20for%20Good%20Spring%202026%2FAll%20Projects%20Folders%20%26%20Student%20Resources%2FCambridge%20META%20Data%20Health%20Dashboard&viewid=f9451973%2Db410%2D4275%2Dacd7%2D0184b75f6d22&sharingv2=true&fromShare=true&at=9&CID=4f418103%2D4aa4%2D4781%2D8af8%2Df05107f7d136&FolderCTID=0x0120005FAA7B880FD4E7499A455090FAE751E3&view=0

**In your own words, what is this project about? What is the goal of this project?**
The Cambridge Open Data Portal hosts hundreds of publicly accessible datasets spanning transportation, public safety, housing, and more. Currently there is no systematic way to monitor the health of this repository over time. This project builds an automated health dashboard that audits the portal via the Socrata API, flags datasets with quality issues such as missing metadata, stale updates, inconsistent tags, and missing licenses, and presents findings in an interactive web dashboard that can be run on a schedule. The goal is to help the Open Data Program proactively address data quality issues before they affect residents, researchers, and policymakers.

**Who is the client for the project?**
City of Cambridge Open Data Program

**Who are the client contacts for the project?**
- Reinhard Engels (Open Data Program Manager) — primary contact
- Alexandra Epstein (Open Data Program) — additional contact

**What class was this project part of?**
DS594

---

## Dataset Information

**What datasets did you use in your project?**
Cambridge Open Data Portal Metadata — fetched via the Socrata Discovery API:
https://api.us.socrata.com/api/catalog/v1?domains=data.cambridgema.gov

Raw data saved to: `raw_data.json`
Parsed data saved to: `datasets.csv`

**Please provide a link to any data dictionaries for the datasets in this project.**

| Field | Description | Type |
|---|---|---|
| id | Unique dataset identifier | String |
| name | Name of the dataset | String |
| description | Text description of the dataset | String |
| department | City department that owns the dataset | String |
| type | Type of resource (dataset, map, chart) | String |
| createdAt | Date the dataset was created | Datetime |
| updatedAt | Date the metadata was last updated | Datetime |
| dataUpdatedAt | Date the actual data was last updated | Datetime |
| tags | List of tags/keywords associated with the dataset | List |
| category | Category the dataset belongs to | String |
| license | License associated with the dataset | String |
| updateFrequency | How often the dataset is expected to be updated | String |
| pageViewsTotal | Total number of page views | Integer |

**What keywords or tags would you attach to the dataset?**
open data, metadata, data quality, civic tech, data auditing, Socrata, Cambridge, government data

**Domain(s) of Application:**
- Civic Tech
- Anomaly Detection
- NLP (for LLM-based quality checks)

---

## Motivation

**For what purpose was the dataset created?**
The metadata dataset was created as part of this project to systematically audit the quality of the Cambridge Open Data Portal. The specific gap being addressed is the lack of any automated monitoring system for the portal — currently data quality issues go undetected until someone manually notices them. This dataset enables automated health checks across all 282 publicly available datasets on the portal.

---

## Composition

**What do the instances represent?**
Each instance represents one dataset listed on the Cambridge Open Data Portal. The data is tabular — each row is one dataset and each column is a metadata field about that dataset.

**How many instances are there in total?**
282 datasets (all of type "dataset")

**Does the dataset contain all possible instances or is it a sample?**
This is a complete snapshot — it contains all datasets publicly available on the Cambridge Open Data Portal at the time of collection (March 2026). It is not a sample.

**What data does each instance consist of?**
Each instance consists of metadata fields — not the actual data content of the datasets. Fields include name, description, tags, license, department, category, update frequency, and timestamps.

**Is there any information missing from individual instances?**

| Field | Missing Count | Notes |
|---|---|---|
| updateFrequency | 282/282 | Field appears empty for all datasets in this API response |
| license | 74/282 | Some datasets have no license assigned |
| department | 56/282 | Some datasets have no department attribution |
| category | 14/282 | Some datasets have no category assigned |
| description | 1/282 | One dataset is missing a description entirely |
| tags | 282/282 | Tags appear empty for all datasets — may be stored in a different API field |

**Are there any errors, sources of noise, or redundancies in the dataset?**
- Tags and update frequency fields appear empty for all 282 datasets — this may indicate these fields are stored in a different part of the API response that requires further investigation
- Some datasets are intentionally no longer being updated (e.g., historical COVID-19 datasets) but will appear stale in automated checks — these need special handling

**Is the dataset self-contained?**
No — it links to the live Cambridge Open Data Portal via the Socrata API. The data reflects a snapshot of the portal at the time of collection and will change as datasets are added, updated, or removed.

**Does the dataset contain confidential data?**
No — all metadata is publicly available via the Cambridge Open Data Portal.

**Is it possible to identify individuals from the dataset?**
No — this is metadata about datasets, not data about individuals.

---

## Dataset Snapshot

| Attribute | Value |
|---|---|
| Size of dataset | ~150 KB (datasets.csv) |
| Number of instances | 282 |
| Number of fields | 13 |
| Labeled classes | N/A |
| Number of labels | N/A |

---

## Collection Process

**What mechanisms were used to collect the data?**
Data was collected via the Socrata Discovery API using paginated HTTP GET requests in batches of 100 results. The API is publicly accessible and requires no authentication for the Cambridge Open Data Portal.

```
Endpoint: https://api.us.socrata.com/api/catalog/v1
Parameters: domains=data.cambridgema.gov, limit=100, offset=0 (paginated)
```

**Over what timeframe was the data collected?**
Data was collected in March 2026. The metadata itself spans datasets created from as early as 2012 through 2026.

---

## Preprocessing / Cleaning / Labeling

**Was any preprocessing done?**
Yes — the raw nested JSON response from the API was parsed and flattened into a clean tabular format.

**What transformations were applied?**
- Nested JSON fields (resource, classification, metadata) were extracted and mapped to individual columns
- Tags extracted as lists from the classification field
- Timestamps kept as ISO format strings for later datetime conversion
- Raw JSON saved separately before any transformation

**Was raw data saved?**
Yes — saved as `raw_data.json` in the project Google Drive folder

**Is the preprocessing code available?**
Yes — `fetch_data.py` in the GitHub repository:
https://github.com/BU-Spark/dd4g-cambridge-meta-health

---

## Uses

**What tasks has the dataset been used for so far?**
- Exploratory data analysis to understand the structure and quality of the portal metadata
- Identifying missing fields across all 282 datasets
- Identifying datasets that have not been updated in over a year

**What other tasks could the dataset be used for?**
- Training or evaluating LLM-based metadata quality scoring models
- Trend analysis of portal health over time if collected periodically
- Benchmarking data quality against other city open data portals

**Are there tasks for which the dataset should not be used?**
This dataset should not be used to make conclusions about the content quality of individual datasets — it only reflects the quality of metadata, not the underlying data itself.

---

## Distribution

**Access type:**
External Open Access — all data is already publicly available via the Cambridge Open Data Portal and Socrata API.

---

## Maintenance

**Is there a mechanism to extend or update the dataset?**
Yes — the `fetch_data.py` script can be re-run at any time to collect a fresh snapshot of the portal metadata. The health dashboard is designed to run on a schedule so the dataset can be refreshed automatically.

---

## Other

The tags and update frequency fields were found to be empty for all 282 datasets in the initial API response. This is a known issue that requires further investigation — these fields may be accessible through a different API endpoint or stored in a different part of the JSON response. This will be resolved in Milestone 2 before the health check script is finalized.

