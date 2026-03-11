import requests
import pandas as pd
import json

url = "https://api.us.socrata.com/api/catalog/v1"
params = {
    "domains": "data.cambridgema.gov",
    "only": "datasets",
    "limit": 100,
    "offset": 0
}

# ─── FETCH ───
all_results = []
while True:
    response = requests.get(url, params=params)
    data = response.json()
    results = data.get("results", [])
    if not results:
        break
    all_results.extend(results)
    params["offset"] += 100
    print(f"Fetched {len(all_results)} datasets so far...")

with open("raw_data.json", "w") as f:
    json.dump(all_results, f)

# ─── PARSE ───
records = []  # ← THIS WAS MISSING
for item in all_results:  # ← THIS WAS MISSING
    resource       = item.get("resource", {})
    classification = item.get("classification", {})
    metadata       = item.get("metadata", {})

    records.append({
        "id":            resource.get("id"),
        "name":          resource.get("name"),
        "description":   resource.get("description"),
        "department":    resource.get("attribution"),
        "type":          resource.get("type"),
        "createdAt":     resource.get("createdAt"),
        "updatedAt":     resource.get("updatedAt"),
        "dataUpdatedAt": resource.get("data_updated_at"),
        "tags":          classification.get("domain_tags", []),
        "category":      classification.get("domain_category"),
        "license":       metadata.get("license"),
        "updateFrequency": next(
            (item["value"] for item in classification.get("domain_metadata", [])
             if item["key"] == "Maintenance-Plan_Estimated-Update-Frequency"),
            None
        ),
        "pageViewsTotal": resource.get("page_views", {})
                                  .get("page_views_total"),
    })

# ─── SAVE ───
df = pd.DataFrame(records)
df.to_csv("datasets.csv", index=False)
print(f"\nDone! {len(df)} datasets saved to datasets.csv")
print(df.shape)
print(df.head())
