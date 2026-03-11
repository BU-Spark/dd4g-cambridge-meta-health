import sqlite3
import pandas as pd
import json
import os
import time
from datetime import datetime, timezone
from huggingface_hub import InferenceClient

BASE_DIR = os.environ.get("BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "cambridge_metadata.db")

HF_TOKEN = os.environ.get("HF_TOKEN", "")
client   = InferenceClient(token=HF_TOKEN)
MODEL    = "meta-llama/Meta-Llama-3-8B-Instruct"


def ask_llm(prompt: str, retries: int = 4) -> str:
    messages = [{"role": "user", "content": prompt}]
    for attempt in range(retries):
        try:
            response = client.chat_completion(
                model=MODEL,
                messages=messages,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "402" in str(e) or "Payment Required" in str(e):
                print("*** QUOTA EXHAUSTED — wait and rerun ***")
                raise SystemExit(1)
            wait = 15 * (attempt + 1)
            if attempt < retries - 1:
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                return f"ERROR: {str(e)[:100]}"


def parse_json_safe(text: str, fallback) -> any:
    """Strip markdown fences and safely parse JSON from LLM response."""
    try:
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except Exception:
        return fallback


def score_description(name: str, description: str, department: str, category: str) -> tuple:
    prompt = f"""You are auditing metadata quality for a government open data portal.
Evaluate the description quality of ONE dataset and return a JSON object.
STRICT RULES:
- Rate ONLY what is explicitly stated in the description provided
- Do NOT add information about what the dataset SHOULD contain
- Do NOT assume additional details not mentioned
- Do NOT invent population sizes, dates, or statistics
- If information is missing, that's what you rate - not a problem to fix

Metadata:
- Dataset Name: {name}
- Department: {department or "Unknown"}
- Category: {category or "Unknown"}
- Current Description: {description or "(empty)"}

Scoring rubric (integer 1-5):
  1 = Missing, empty, or completely uninformative
  2 = Present but extremely vague (e.g., "This dataset contains data")
  3 = Adequate — mentions the topic but lacks what, who, or when
  4 = Good — clearly states what data is collected, by whom, and for what purpose
  5 = Excellent — precise, complete, useful to a data consumer

Required output (JSON only):
{{
  "score": <integer 1-5>,
  "feedback": "<2-5 words explaining the score>"
}}"""

    raw    = ask_llm(prompt)
    result = parse_json_safe(raw, {"score": 1, "feedback": "Parse failed."})
    score  = result.get("score", 1)
    if score not in [1, 2, 3, 4, 5]:
        score = 1
    return int(score), result.get("feedback", "No feedback")


def suggest_description(name: str, description: str, department: str, category: str, columns: str) -> str:
    prompt = f"""You are a government data documentation specialist.
Write a clear, factual 2-3 sentence description for the dataset below.

STRICT RULES:
- Use ONLY facts present in the metadata provided. Do NOT invent statistics, dates, or coverage areas.
- If the available metadata is insufficient to write a meaningful description,
  return exactly: INSUFFICIENT_DATA

Metadata:
- Dataset Name: {name}
- Department: {department or "Unknown"}
- Category: {category or "Unknown"}
- Existing Description: {description or "(empty)"}
- Column Names: {columns}

Return ONLY the description text or INSUFFICIENT_DATA. No preamble, no explanation."""

    return ask_llm(prompt)


def score_tag_match(name, description, tags):
    if not tags or not str(tags).strip():
        return 1, "No tags suggested"

    prompt = f"""You are evaluating how well a set of tags matches a government dataset.

SCORING GUIDELINES:
- Score 1: Tags are missing, generic, or mostly unrelated
- Score 2: Tags are somewhat related but vague or weak
- Score 3: Tags are broadly correct but not very specific
- Score 4: Tags match the dataset well and are useful
- Score 5: Tags are highly accurate, specific, and clearly aligned with the dataset

STRICT RULES:
- Judge only based on dataset name, description, and the provided tags
- Do NOT assume extra context not written below
- Penalize generic tags like "data", "government", or overly broad labels
- Reward tags that would help a user find this dataset

Dataset Name: {name}
Description: {description or "(empty)"}
Tags: {tags}

Respond in EXACTLY this format:
SCORE: [1-5]
FEEDBACK: [one sentence]"""

    try:
        text = ask_llm(prompt)
        print(f"    Tag score response: {text[:100]}")

        score = None
        feedback = "No feedback"

        for line in text.split("\n"):
            line = line.strip()
            if line.upper().startswith("SCORE:"):
                try:
                    score = int(''.join(filter(str.isdigit, line.split(":")[1])))
                except Exception:
                    pass
            if line.upper().startswith("FEEDBACK:"):
                feedback = line.split(":", 1)[1].strip()

        if score is None or score not in [1, 2, 3, 4, 5]:
            score = 1
            feedback = f"Parse error. Raw: {text[:80]}"

        return score, feedback
    except Exception as e:
        return 1, f"Error: {str(e)[:80]}"


def suggest_tags(name: str, description: str, category: str) -> list:
    prompt = f"""You are tagging government datasets for a public open data portal.
Suggest 3-5 relevant tags for the dataset below.

TAG GUIDELINES - Only use tags that:
- Describe what the dataset ACTUALLY CONTAINS (based on name, description, category)
- Are specific, not generic (e.g., "vaccine-records" NOT "health")
- Are based on explicit information given - do NOT invent topics
- Use lowercase, single words or hyphenated phrases
- Are relevant to people searching for similar datasets

INVALID TAGS - DO NOT SUGGEST:
- Generic terms: "data", "information", "government", "dataset"
- Assumptions about content not mentioned
- Tags that duplicate the category already provided
- Made-up topics not in the name/description/category

Dataset: "{name}"
Category: "{category or "Unknown"}"
Description: "{description or "(empty)"}"

If insufficient info, respond: INSUFFICIENT_DATA
Return ONLY a JSON array of strings. No explanation, no markdown.
Example: ["open-data", "transportation", "cambridge"]"""

    raw    = ask_llm(prompt)
    result = parse_json_safe(raw, [])
    if isinstance(result, list):
        return [str(t).strip() for t in result if t]
    return []


def create_llm_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS llm_results (
            id TEXT PRIMARY KEY,
            llm_desc_score INTEGER,
            llm_desc_feedback TEXT,
            llm_suggested_desc TEXT,
            llm_suggested_tags TEXT,
            llm_tag_alignment_note TEXT,
            llm_status TEXT,
            llm_run_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS human_approvals (
            approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id TEXT,
            approved_description TEXT,
            approved_tags TEXT,
            human_status TEXT,
            reviewed_by TEXT,
            reviewed_at TEXT,
            edit_note TEXT
        )
    """)
    conn.commit()


def update_health_score_with_llm(conn, dataset_id: str, llm_desc_score: int):
    """
    After LLM runs, update desc_score in health_flags with the LLM score
    and recompute the composite health_score.
    LLM score (1-5) -> normalized (0-100): 1->0, 2->25, 3->50, 4->80, 5->100
    """
    score_map = {1: 0.0, 2: 25.0, 3: 50.0, 4: 80.0, 5: 100.0}
    desc_score_normalized = score_map.get(llm_desc_score, 0.0)

    row = conn.execute("""
        SELECT tag_score, license_score, dept_score, category_score,
               freshness_score
        FROM health_flags WHERE id = ?
    """, (dataset_id,)).fetchone()

    if not row:
        return

    tag_s, lic_s, dept_s, cat_s, fresh_s = row

    health = round(
        0.25 * desc_score_normalized +
        0.15 * tag_s +
        0.15 * lic_s +
        0.10 * dept_s +
        0.10 * cat_s +
        0.25 * fresh_s,
        1
    )
    band = "Good" if health >= 80 else "Fair" if health >= 60 else "Poor" if health >= 40 else "Critical"

    conn.execute("""
        UPDATE health_flags
        SET desc_score = ?, health_score = ?, health_band = ?
        WHERE id = ?
    """, (desc_score_normalized, health, band, dataset_id))


def run_llm_enrichment(only_low_scores: bool = True, score_threshold: float = 65.0):
    conn = sqlite3.connect(DB_PATH)
    create_llm_tables(conn)

    query = """
        SELECT d.*, h.health_score
        FROM datasets d
        LEFT JOIN health_flags h ON d.id = h.id
    """
    if only_low_scores:
        query += f" WHERE h.health_score < {score_threshold} OR h.health_score IS NULL"

    df = pd.read_sql(query, conn)
    print(f"  Running LLM on {len(df)} datasets...")

    enriched_count = 0
    for i, row in df.iterrows():
        print(f"  [{i+1}/{len(df)}] {row['name']}")

        columns   = json.loads(row["columns"])  if row["columns"]   else []
        col_names = json.loads(row["col_names"]) if row["col_names"] else []
        columns_str = ", ".join(col_names) if col_names else (", ".join(columns) if columns else "Not available")

        # Step 1 — Score the description
        desc_score, feedback = score_description(
            row["name"], row["description"], row["department"], row["category"]
        )

        # Step 2 — Suggest tags
        suggested_tags_list = suggest_tags(row["name"], row["description"], row["category"])
        suggested_tags_str  = json.dumps(suggested_tags_list)

        # Step 3 — Score the tag alignment
        tag_score, tag_alignment_note = score_tag_match(
            row["name"], row["description"], suggested_tags_str
        )
        print(f"    Tag alignment score: {tag_score}/5 — {tag_alignment_note}")

        # Step 4 — Suggest new description only if score is very poor
        suggested_desc = None
        llm_status     = "reviewed"
        if desc_score <= 2:
            suggested_desc = suggest_description(
                row["name"], row["description"],
                row["department"], row["category"], columns_str
            )
            # Guard only runs when suggest_description was called
            if suggested_desc and suggested_desc.startswith("ERROR:"):
                suggested_desc = None
                llm_status = "pending_review"
            elif suggested_desc == "INSUFFICIENT_DATA":
                suggested_desc = None
                llm_status = "insufficient_data"
            else:
                llm_status = "pending_review"

        # Step 5 — Save to DB
        conn.execute("""
            INSERT OR REPLACE INTO llm_results VALUES (?,?,?,?,?,?,?,?)
        """, (
            row["id"], desc_score, feedback,
            suggested_desc, suggested_tags_str,
            tag_alignment_note,
            llm_status,
            datetime.now(timezone.utc).isoformat()
        ))

        update_health_score_with_llm(conn, row["id"], desc_score)
        conn.commit()
        enriched_count += 1
        time.sleep(15)

    conn.close()
    print(f"  LLM enrichment complete for {enriched_count} datasets.")
    return enriched_count


if __name__ == "__main__":
    run_llm_enrichment(only_low_scores=True, score_threshold=65.0)
