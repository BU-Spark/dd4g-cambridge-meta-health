import streamlit as st
import sqlite3
import pandas as pd
import json
import os
from datetime import datetime, timezone
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Cambridge Open Data — Health Monitor",
    page_icon="\U0001f3d9\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = os.environ.get("BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "cambridge_metadata.db")

st.markdown("""
<style>
    .main { background-color: #f8f9fb; }
    .block-container { padding-top: 1.5rem; }
    .stMetric { background: white; border-radius: 10px; padding: 12px;
                box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

BAND_COLORS = {"Critical": "#e74c3c", "Poor": "#e67e22", "Fair": "#f1c40f", "Good": "#2ecc71"}
BAND_EMOJI  = {"Critical": "\U0001f534", "Poor": "\U0001f7e0", "Fair": "\U0001f7e1", "Good": "\U0001f7e2"}


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("""
        SELECT
            d.id, d.name, d.description, d.department, d.category,
            d.license, d.tags, d.updatedAt, d.dataUpdatedAt,
            d.updateFrequency, d.createdAt,
            h.health_score, h.health_band,
            h.missing_description, h.missing_tags, h.missing_license,
            h.missing_department, h.missing_category,
            h.is_stale, h.days_overdue, h.freshness_score,
            h.desc_score, h.tag_score, h.license_score,
            h.col_metadata_score,
            l.llm_desc_score, l.llm_desc_feedback,
            l.llm_suggested_desc, l.llm_suggested_tags, l.llm_status
        FROM datasets d
        LEFT JOIN health_flags h ON d.id = h.id
        LEFT JOIN llm_results  l ON d.id = l.id
    """, conn)
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_last_run() -> str:
    try:
        conn = sqlite3.connect(DB_PATH)
        row  = conn.execute(
            "SELECT finished_at, datasets_fetched FROM pipeline_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if row:
            ts = row[0][:19].replace("T", " ") if row[0] else "Unknown"
            return f"Last refresh: {ts} UTC  |  {row[1]} datasets"
        return "No pipeline run recorded yet"
    except Exception:
        return "Pipeline run data unavailable"


def save_approval(dataset_id, approved_desc, approved_tags, status, reviewer, note=""):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS human_approvals (
            approval_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id TEXT, approved_description TEXT,
            approved_tags TEXT, human_status TEXT,
            reviewed_by TEXT, reviewed_at TEXT, edit_note TEXT
        )
    """)
    conn.execute("""
        INSERT INTO human_approvals
        (dataset_id, approved_description, approved_tags,
         human_status, reviewed_by, reviewed_at, edit_note)
        VALUES (?,?,?,?,?,?,?)
    """, (dataset_id, approved_desc, approved_tags, status,
          reviewer, datetime.now(timezone.utc).isoformat(), note))
    conn.commit()
    conn.close()


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### \U0001f3d9\ufe0f Cambridge Open Data\n**Metadata Health Monitor**")
    st.caption(load_last_run())
    st.markdown("---")
    st.markdown("#### Filters")

    search_query = st.text_input("\U0001f50d Search dataset name", "")

    dept_options   = sorted(df["department"].dropna().unique().tolist())
    selected_depts = st.multiselect("Department", dept_options, default=[])

    cat_options   = sorted(df["category"].dropna().unique().tolist())
    selected_cats = st.multiselect("Category", cat_options, default=[])

    selected_bands = st.multiselect(
        "Health Band", ["Critical", "Poor", "Fair", "Good"],
        default=["Critical", "Poor", "Fair", "Good"]
    )

    stale_only   = st.toggle("\u26a0\ufe0f Stale datasets only",  value=False)
    no_lic_only  = st.toggle("\U0001f513 Missing license only",    value=False)
    no_tags_only = st.toggle("\U0001f3f7\ufe0f Missing tags only", value=False)

    st.markdown("---")
    st.caption("Cambridge Open Data Portal\nReinhard Engels, Open Data Program")

# Apply filters
filtered = df.copy()
if search_query:
    filtered = filtered[filtered["name"].str.contains(search_query, case=False, na=False)]
if selected_depts:
    filtered = filtered[filtered["department"].isin(selected_depts)]
if selected_cats:
    filtered = filtered[filtered["category"].isin(selected_cats)]
if selected_bands:
    filtered = filtered[filtered["health_band"].isin(selected_bands)]
if stale_only:
    filtered = filtered[filtered["is_stale"] == 1]
if no_lic_only:
    filtered = filtered[filtered["missing_license"] == 1]
if no_tags_only:
    filtered = filtered[filtered["missing_tags"] == 1]

# ── Header & KPIs ─────────────────────────────────────────────────────────────
st.markdown("## \U0001f3d9\ufe0f Cambridge Open Data — Metadata Health Dashboard")
st.caption(f"Showing **{len(filtered)}** of **{len(df)}** datasets after filters")

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("\U0001f4e6 Total Datasets",    len(filtered))
k2.metric("\U0001f4ca Avg Health Score",  f"{filtered['health_score'].mean():.1f}" if not filtered.empty else "—")
k3.metric("\U0001f534 Critical",          int((filtered["health_band"] == "Critical").sum()))
k4.metric("\u26a0\ufe0f Stale",          int(filtered["is_stale"].sum()))
k5.metric("\U0001f513 Missing License",   int(filtered["missing_license"].sum()))
k6.metric("\U0001f3f7\ufe0f Missing Tags", int(filtered["missing_tags"].sum()))

st.markdown("---")

pending_count = len(filtered[filtered["llm_status"] == "pending_review"])
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "\U0001f4ca Overview",
    "\U0001f6a8 Action Queue",
    f"\U0001f4dd AI Descriptions ({pending_count} pending)",
    "\U0001f3f7\ufe0f AI Tags",
    "\U0001f4cb Spreadsheet View",
    "\U0001f4c8 Trends"
])

# ── TAB 1: OVERVIEW ───────────────────────────────────────────────────────────
with tab1:
    st.subheader("Portal Health Overview")
    c1, c2 = st.columns(2)

    band_counts = filtered["health_band"].value_counts().reset_index()
    band_counts.columns = ["Band", "Count"]
    fig_donut = px.pie(band_counts, names="Band", values="Count",
                       color="Band", color_discrete_map=BAND_COLORS,
                       hole=0.5, title="Health Band Distribution")
    fig_donut.update_traces(textposition="outside", textinfo="percent+label")
    c1.plotly_chart(fig_donut, use_container_width=True)

    missing = {
        "Tags":        int(filtered["missing_tags"].sum()),
        "License":     int(filtered["missing_license"].sum()),
        "Description": int(filtered["missing_description"].sum()),
        "Department":  int(filtered["missing_department"].sum()),
        "Category":    int(filtered["missing_category"].sum()),
    }
    fig_missing = px.bar(x=list(missing.keys()), y=list(missing.values()),
                         labels={"x": "Field", "y": "# Datasets Missing"},
                         title="Missing Metadata Fields",
                         color=list(missing.values()), color_continuous_scale="Reds")
    fig_missing.update_layout(coloraxis_showscale=False)
    c2.plotly_chart(fig_missing, use_container_width=True)

    fig_hist = px.histogram(filtered, x="health_score", nbins=20,
                            title="Health Score Distribution",
                            labels={"health_score": "Health Score"},
                            color_discrete_sequence=["#3498db"])
    fig_hist.add_vline(x=60, line_dash="dash", line_color="orange", annotation_text="Fair threshold")
    fig_hist.add_vline(x=80, line_dash="dash", line_color="green",  annotation_text="Good threshold")
    st.plotly_chart(fig_hist, use_container_width=True)

    if filtered["department"].notna().any():
        dept_health = (filtered.groupby("department")["health_score"]
                       .mean().reset_index()
                       .rename(columns={"health_score": "Avg Health Score"})
                       .sort_values("Avg Health Score").head(20))
        fig_dept = px.bar(dept_health, x="Avg Health Score", y="department",
                          orientation="h",
                          title="Average Health Score by Department (Bottom 20)",
                          color="Avg Health Score",
                          color_continuous_scale="RdYlGn", range_color=[0, 100])
        st.plotly_chart(fig_dept, use_container_width=True)

    stale_freq = (filtered.groupby("updateFrequency")["is_stale"]
                  .agg(["sum", "count"]).reset_index()
                  .rename(columns={"sum": "Stale", "count": "Total",
                                   "updateFrequency": "Frequency"}))
    stale_freq["Pct Stale"] = (stale_freq["Stale"] / stale_freq["Total"] * 100).round(1)
    stale_freq = stale_freq.dropna(subset=["Frequency"]).sort_values("Pct Stale", ascending=False)
    fig_stale = px.bar(stale_freq, x="Frequency", y="Pct Stale",
                       title="% Stale Datasets by Update Frequency",
                       labels={"Pct Stale": "% Stale"},
                       color="Pct Stale", color_continuous_scale="Reds")
    st.plotly_chart(fig_stale, use_container_width=True)

# ── TAB 2: ACTION QUEUE ───────────────────────────────────────────────────────
with tab2:
    st.subheader("\U0001f6a8 Datasets Needing Attention")
    st.caption("Sorted by health score (worst first). Expand a row for details.")
    action_df = filtered.sort_values("health_score").head(50)

    if action_df.empty:
        st.success("No datasets match the current filters.")
    else:
        for _, row in action_df.iterrows():
            emoji = BAND_EMOJI.get(row["health_band"], "\u26aa")
            label = f"{emoji} {row['name']}  —  Score: {row['health_score']}  |  {row['health_band']}"
            with st.expander(label):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Department:** {row['department'] or '\u274c Missing'}")
                c1.markdown(f"**Category:** {row['category'] or '\u274c Missing'}")
                c1.markdown(f"**License:** {row['license'] or '\u274c Missing'}")
                c2.markdown(f"**Update Frequency:** {row['updateFrequency'] or 'Unknown'}")
                c2.markdown(f"**Last Updated:** {str(row['dataUpdatedAt'] or row['updatedAt'] or 'Unknown')[:10]}")
                stale_label = f"\u26a0\ufe0f Yes ({row['days_overdue']} days overdue)" if row["is_stale"] else "\u2705 No"
                c2.markdown(f"**Stale:** {stale_label}")
                c3.markdown(f"**AI Desc Score:** {row['llm_desc_score'] or '—'}/5")
                tag_count = len(json.loads(row["tags"])) if row["tags"] else 0
                c3.markdown(f"**Tag Count:** {tag_count}")

                flags = []
                if row["missing_description"]: flags.append("\U0001f6ab No description")
                if row["missing_tags"]:        flags.append("\U0001f3f7\ufe0f No tags")
                if row["missing_license"]:     flags.append("\U0001f513 No license")
                if row["is_stale"]:            flags.append("\u23f0 Stale")
                if flags:
                    st.markdown("**Issues:** " + "  |  ".join(flags))
                st.markdown(f"**Description:** {row['description'] or '*(empty)*'}")
                if row["llm_desc_feedback"]:
                    st.info(f"\U0001f4ac AI Feedback: {row['llm_desc_feedback']}")

# ── TAB 3: AI DESCRIPTIONS ────────────────────────────────────────────────────
with tab3:
    st.subheader("AI-Suggested Descriptions — Human Review")
    st.caption("Review AI suggestions carefully. Edit before approving if needed.")
    reviewer = st.text_input("Your name (required for audit trail)", key="reviewer_desc")

    needs_review = filtered[filtered["llm_status"] == "pending_review"].sort_values("health_score")

    if needs_review.empty:
        st.info("No descriptions pending review. Run pipeline.py to generate suggestions.")
    else:
        for _, row in needs_review.iterrows():
            emoji = BAND_EMOJI.get(row["health_band"], "\u26aa")
            with st.expander(f"{emoji} {row['name']}  |  AI Score: {row['llm_desc_score']}/5"):
                c1, c2 = st.columns(2)
                c1.markdown("**Original Description:**")
                c1.write(row["description"] or "*(empty)*")
                c2.markdown("**AI Suggested Description:**")
                edited_desc = c2.text_area("Edit before approving:",
                                           value=row["llm_suggested_desc"] or "",
                                           key=f"desc_{row['id']}", height=120)
                if row["llm_desc_feedback"]:
                    st.info(f"\U0001f4ac AI Feedback: {row['llm_desc_feedback']}")
                edit_note = st.text_input("Reviewer note (optional):", key=f"note_{row['id']}")

                ca, cb, cc = st.columns(3)
                if ca.button("\u2705 Approve", key=f"app_{row['id']}"):
                    if not reviewer:
                        ca.warning("Enter your name first.")
                    else:
                        save_approval(row["id"], edited_desc, row["llm_suggested_tags"], "approved", reviewer, edit_note)
                        ca.success("Approved!")
                if cb.button("\u270f\ufe0f Approve Edited", key=f"edit_{row['id']}"):
                    if not reviewer:
                        cb.warning("Enter your name first.")
                    else:
                        save_approval(row["id"], edited_desc, row["llm_suggested_tags"], "edited", reviewer, edit_note)
                        cb.success("Saved as edited!")
                if cc.button("\u274c Reject", key=f"rej_{row['id']}"):
                    save_approval(row["id"], None, None, "rejected", reviewer, edit_note)
                    cc.warning("Rejected.")

# ── TAB 4: AI TAGS ────────────────────────────────────────────────────────────
with tab4:
    st.subheader("\U0001f3f7\ufe0f AI-Suggested Tags — Datasets with Missing Tags")
    reviewer_tags = st.text_input("Your name", key="reviewer_tags")
    tag_df = filtered[filtered["missing_tags"] == 1].sort_values("health_score")

    if tag_df.empty:
        st.success("No datasets with missing tags in current filter.")
    else:
        for _, row in tag_df.iterrows():
            emoji = BAND_EMOJI.get(row["health_band"], "\u26aa")
            with st.expander(f"{emoji} {row['name']}"):
                st.markdown(f"**Category:** {row['category'] or 'Unknown'}  |  **Dept:** {row['department'] or 'Unknown'}")
                st.markdown("**Current Tags:** *(none)*")

                raw_tags = row["llm_suggested_tags"]
                try:
                    tags_list = json.loads(raw_tags) if raw_tags else []
                except Exception:
                    tags_list = [t.strip() for t in str(raw_tags).split(",") if t.strip()]

                if tags_list:
                    st.markdown("**AI Suggested Tags:**")
                    st.code(", ".join(tags_list))
                    ca, cb = st.columns(2)
                    if ca.button("\u2705 Approve Tags", key=f"tappr_{row['id']}"):
                        if not reviewer_tags:
                            ca.warning("Enter your name first.")
                        else:
                            save_approval(row["id"], None, raw_tags, "approved", reviewer_tags)
                            ca.success("Tags approved!")
                    if cb.button("\u274c Reject Tags", key=f"trej_{row['id']}"):
                        save_approval(row["id"], None, None, "rejected", reviewer_tags)
                        cb.warning("Rejected.")
                else:
                    st.info("No AI tag suggestions yet. Run pipeline.py to generate.")

# ── TAB 5: SPREADSHEET VIEW ───────────────────────────────────────────────────
with tab5:
    st.subheader("\U0001f4cb Spreadsheet View — Full Dataset Table")
    st.caption("Reflects your current sidebar filters. Export includes all visible rows.")

    export_cols = [
        "id", "name", "department", "category", "license",
        "tags", "updatedAt", "dataUpdatedAt", "updateFrequency",
        "health_score", "health_band",
        "missing_description", "missing_tags", "missing_license",
        "missing_department", "missing_category",
        "is_stale", "days_overdue",
        "llm_desc_score", "llm_desc_feedback",
        "llm_suggested_desc", "llm_suggested_tags", "llm_status"
    ]
    available_cols = [c for c in export_cols if c in filtered.columns]
    export_df = filtered[available_cols].sort_values("health_score")

    def style_band(val):
        colors = {"Critical": "background-color:#fde8e8",
                  "Poor":     "background-color:#fef0e0",
                  "Fair":     "background-color:#fefde0",
                  "Good":     "background-color:#e8f8ee"}
        return colors.get(val, "")

    st.dataframe(
        export_df.style.map(style_band, subset=["health_band"]),
        use_container_width=True, height=500
    )

    st.download_button(
        label="\u2b07\ufe0f Export Filtered View as CSV (ODP Format)",
        data=to_csv_bytes(export_df),
        file_name=f"cambridge_metadata_health_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        type="primary"
    )

# ── TAB 6: TRENDS ─────────────────────────────────────────────────────────────
with tab6:
    st.subheader("\U0001f4c8 Metadata Health Trends & Analysis")
    c1, c2 = st.columns(2)

    lic_counts = filtered["missing_license"].value_counts().reset_index()
    lic_counts.columns = ["Status", "Count"]
    lic_counts["Status"] = lic_counts["Status"].map({0: "Has License", 1: "Missing License"})
    fig_lic = px.pie(lic_counts, names="Status", values="Count",
                     title="License Coverage (~25% expected missing)",
                     color="Status",
                     color_discrete_map={"Has License": "#2ecc71", "Missing License": "#e74c3c"})
    c1.plotly_chart(fig_lic, use_container_width=True)

    filtered["tag_count"] = filtered["tags"].apply(lambda x: len(json.loads(x)) if x else 0)
    fig_tags = px.histogram(filtered, x="tag_count", nbins=15,
                            title="Tag Count Distribution",
                            labels={"tag_count": "Number of Tags"},
                            color_discrete_sequence=["#9b59b6"])
    fig_tags.add_vline(x=3, line_dash="dash", line_color="green", annotation_text="3-tag target")
    c2.plotly_chart(fig_tags, use_container_width=True)

    dim_scores = {
        "Description":   filtered["desc_score"].mean(),
        "Tags":          filtered["tag_score"].mean(),
        "License":       filtered["license_score"].mean(),
        "Freshness":     filtered["freshness_score"].mean(),
        "Col Metadata":  filtered["col_metadata_score"].mean(),
    }
    fig_dims = go.Figure(go.Bar(
        x=list(dim_scores.keys()),
        y=[round(v, 1) if not pd.isna(v) else 0 for v in dim_scores.values()],
        marker_color=["#3498db","#9b59b6","#2ecc71","#e67e22","#1abc9c"]
    ))
    fig_dims.update_layout(title="Average Sub-Score by Dimension (0-100)",
                           yaxis=dict(range=[0, 100]),
                           xaxis_title="Dimension", yaxis_title="Avg Score")
    st.plotly_chart(fig_dims, use_container_width=True)

    st.markdown("#### \U0001f4c5 Datasets Overdue Relative to Update Frequency")
    two_yr_df = filtered[filtered["days_overdue"] > 0].sort_values("days_overdue", ascending=False)
    if two_yr_df.empty:
        st.success("No datasets are overdue relative to their update frequency.")
    else:
        display_cols = ["name","department","updateFrequency","dataUpdatedAt","days_overdue","health_band"]
        st.dataframe(two_yr_df[[c for c in display_cols if c in two_yr_df.columns]].head(30),
                     use_container_width=True)
