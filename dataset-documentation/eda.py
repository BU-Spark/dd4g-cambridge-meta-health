import pandas as pd

df = pd.read_csv("datasets.csv")

print(f"Total datasets: {len(df)}")
print(f"\nDataset types:\n{df['type'].value_counts()}")
print(f"\nMissing values:\n{df.isnull().sum()}")
print(f"\nUpdate frequencies:\n{df['updateFrequency'].value_counts(dropna=False)}")
print(f"\nLicenses:\n{df['license'].value_counts(dropna=False)}")

df["tag_count"] = df["tags"].apply(
    lambda x: len(eval(x)) if isinstance(x, str) else len(x)
)
print(f"\nTag count stats:\n{df['tag_count'].describe()}")
print(f"Datasets with less than 3 tags: {(df['tag_count'] < 3).sum()}")

print(f"\nCategories:\n{df['category'].value_counts(dropna=False)}")

df["dataUpdatedAt"] = pd.to_datetime(df["dataUpdatedAt"], errors="coerce", utc=True)
df["days_since_update"] = (pd.Timestamp.now(tz="UTC") - df["dataUpdatedAt"]).dt.days
print(f"\nDays since update:\n{df['days_since_update'].describe()}")
print(f"Not updated in 1+ year: {(df['days_since_update'] > 365).sum()}")
print(f"Not updated in 2+ years: {(df['days_since_update'] > 730).sum()}")