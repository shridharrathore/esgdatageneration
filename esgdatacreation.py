import streamlit as st
import pandas as pd
import os
import re
import PyPDF2
# File paths
METRIC_FILE = "gri_metrics.csv"
TAXONOMY_FILE = "taxonomy.csv"
ONTOLOGY_FILE = "ontology.csv"
st.set_page_config(page_title="ESG Metric Tracker", layout="wide")
tab1, tab2, tab3 = st.tabs(["📥 Extract Metrics", "🗂️ Taxonomy Manager", "🧠 Ontology Builder"])
# ------------------------
# Tab 1: Extract Metrics
# ------------------------
with tab1:
    st.header("📥 Extract ESG Metrics from PDFs")
    uploaded_files = st.file_uploader("Upload one or more GRI PDF files", type="pdf", accept_multiple_files=True)
    if uploaded_files:
        extracted_data = []
        for pdf_file in uploaded_files:
            try:
                reader = PyPDF2.PdfReader(pdf_file)
                text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
                pattern = re.compile(r"Disclosure\s+(\d{3}-\d)\s+(.*)", re.IGNORECASE)
                for line in text.splitlines():
                    match = pattern.search(line)
                    if match:
                        extracted_data.append({
                            "Metric ID": f"GRI {match.group(1)}",
                            "Description": match.group(2).strip(),
                            "Unit": "metric tons CO₂e",
                            "Sector Applicability": "All",
                            "Source": pdf_file.name
                        })
            except Exception as e:
                st.error(f"Failed to read {pdf_file.name}: {e}")
        if extracted_data:
            new_df = pd.DataFrame(extracted_data)
            if os.path.exists(METRIC_FILE):
                existing_df = pd.read_csv(METRIC_FILE)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df.drop_duplicates(subset=["Metric ID", "Source"], inplace=True)
            else:
                combined_df = new_df
            combined_df.to_csv(METRIC_FILE, index=False)
            st.success("✅ Metrics extracted and saved.")
        else:
            st.warning("No ESG metrics found in the uploaded PDFs.")
    if os.path.exists(METRIC_FILE):
        df = pd.read_csv(METRIC_FILE)
        st.markdown(f"### 📊 Total Extracted Metrics: {len(df)}")
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            selected_framework = st.selectbox("📊 Filter by Framework", ["All"] + sorted(set(df["Metric ID"].str.extract(r"^(GRI|BRSR|SASB)")[0].dropna())))
        with filter_col2:
            keyword = st.text_input("🔍 Filter by keyword")
        if selected_framework != "All":
            df = df[df["Metric ID"].str.startswith(selected_framework)]
        if keyword:
            df = df[df.apply(lambda row: keyword.lower() in str(row).lower(), axis=1)]
        st.dataframe(df)
        if keyword:
            df = df[df.apply(lambda row: keyword.lower() in str(row).lower(), axis=1)]
        st.dataframe(df)
        st.text_input("🔍 Filter by keyword", key="tab1_filter")
    st.markdown("---")
    st.subheader("⚙️ Reset Data (Start Over)")
    if st.button("🗑 Delete All Extracted Metrics"):
        if os.path.exists(METRIC_FILE):
            os.remove(METRIC_FILE)
            st.warning("Deleted gri_metrics.csv. Please refresh.")
    if st.button("🗑 Delete Taxonomy File"):
        if os.path.exists(TAXONOMY_FILE):
            os.remove(TAXONOMY_FILE)
            st.warning("Deleted taxonomy.csv. Will regenerate on next visit.")
# ------------------------
# Tab 2: Taxonomy Manager
# ------------------------
with tab2:
    st.header("🗂️ Taxonomy Manager")
    metric_df = pd.DataFrame()
    if os.path.exists(METRIC_FILE):
        metric_df = pd.read_csv(METRIC_FILE)
    if os.path.exists(TAXONOMY_FILE):
        taxonomy_df = pd.read_csv(TAXONOMY_FILE)
        if "Description" not in taxonomy_df.columns and not metric_df.empty:
            metric_map = dict(zip(metric_df["Metric ID"], metric_df["Description"]))
            taxonomy_df["Description"] = taxonomy_df["Metric ID"].map(metric_map)
    else:
        taxonomy_df = pd.DataFrame(columns=["Metric ID", "Description", "Category", "Subcategory"])
    if not metric_df.empty:
        new_metrics = metric_df[["Metric ID", "Description"]].drop_duplicates()
        taxonomy_df = pd.merge(new_metrics, taxonomy_df, on=["Metric ID", "Description"], how="left")
        # === Auto-categorize by keywords ===
        def classify_category(desc):
            desc = desc.lower()
            if "emission" in desc:
                return "Environment", "GHG Emissions"
            elif "energy" in desc:
                return "Environment", "Energy Consumption"
            elif "diversity" in desc or "gender" in desc:
                return "Social", "Gender Diversity"
            elif "training" in desc:
                return "Social", "Training Hours"
            elif "board" in desc:
                return "Governance", "Board Independence"
            elif "corruption" in desc or "anti-corruption" in desc:
                return "Governance", "Anti-Corruption Practices"
            else:
                return "Uncategorized", ""
        taxonomy_df[["Category", "Subcategory"]] = taxonomy_df.apply(
            lambda row: pd.Series(classify_category(row["Description"])), axis=1)
        taxonomy_df["Category"] = taxonomy_df["Category"].fillna("Uncategorized")
        taxonomy_df["Subcategory"] = taxonomy_df["Subcategory"].fillna("")
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            selected_category = st.selectbox("Filter by Category", ["All"] + sorted(taxonomy_df["Category"].dropna().unique()))
        with filter_col2:
            keyword = st.text_input("Search by keyword", "")
        filtered_taxo = taxonomy_df.copy()
        if selected_category != "All":
            filtered_taxo = filtered_taxo[filtered_taxo["Category"] == selected_category]
        if keyword:
            filtered_taxo = filtered_taxo[filtered_taxo.apply(lambda row: keyword.lower() in str(row).lower(), axis=1)]
        st.dataframe(filtered_taxo)
        if st.button("💾 Save Taxonomy"):
            taxonomy_df.to_csv(TAXONOMY_FILE, index=False)
            st.success("Taxonomy saved successfully.")
    else:
        st.info("No metrics available. Please upload PDFs in Tab 1.")
# ------------------------
# Tab 3: Ontology Builder
# ------------------------
with tab3:
    st.header("🧠 Ontology Builder")
    st.info("""
    To create an ontology entry:
    - Select a **Canonical Topic** (usually from the taxonomy Subcategory list)
    - Add **Synonyms** (e.g., "CO₂ emissions, carbon footprint")
    - Add **Related Phrases** (e.g., "climate impact, greenhouse gases")
    - Optionally map corresponding **GRI**, **BRSR**, or **SASB** metric IDs
    - Click **Add to Ontology** to save the entry
    """)
    if os.path.exists(TAXONOMY_FILE):
        taxonomy_df = pd.read_csv(TAXONOMY_FILE)
        topics = sorted(taxonomy_df["Subcategory"].dropna().unique())
    else:
        topics = []
    if os.path.exists(ONTOLOGY_FILE):
        ontology_df = pd.read_csv(ONTOLOGY_FILE)
    else:
        ontology_df = pd.DataFrame(columns=["Canonical Topic", "Synonyms", "Related Phrases", "GRI ID", "BRSR ID", "SASB ID"])
    with st.expander("➕ Add Ontology Entry"):
        col1, col2 = st.columns(2)
        with col1:
            pass  # placeholder for fallback input
        if topics:
            canonical = st.selectbox("Canonical Topic", topics)
        else:
            canonical = st.text_input("Enter Canonical Topic")
            gri_id = st.text_input("GRI ID")
            brsr_id = st.text_input("BRSR ID")
            sasb_id = st.text_input("SASB ID")
        with col2:
            synonyms = st.text_area("Synonyms (comma-separated)")
            related = st.text_area("Related Phrases (comma-separated)")

        # Suggested phrases and matching metric IDs
        st.markdown("**💡 Auto-Suggestions**")
        if os.path.exists("gri_metrics.csv"):
            metrics_df = pd.read_csv("gri_metrics.csv")
            matches = metrics_df[metrics_df["Description"].str.contains(canonical, case=False, na=False)]
            suggested_synonyms = list(matches["Description"].dropna().unique())[:5]
            st.markdown("**🗣 Suggested Synonyms/Related Phrases:**")
            for s in suggested_synonyms:
                st.markdown(f"- {s}")
            st.markdown("**🔗 Matching Metric IDs:**")
            for _, row in matches.iterrows():
                st.markdown(f"- `{row["Metric ID"]}` → {row["Description"]}")
        st.markdown("**💡 Suggestions from Metrics**")
        if os.path.exists("gri_metrics.csv"):
            all_text = pd.read_csv("gri_metrics.csv")["Description"].dropna().str.lower().unique()
            matched = [d for d in all_text if canonical.lower() in d]
            for m in matched[:5]:
                st.markdown(f"- {m}")
        if st.button("Add Ontology Entry"):
            new_entry = {
                "Canonical Topic": canonical,
                "Synonyms": synonyms,
                "Related Phrases": related,
                "GRI ID": gri_id,
                "BRSR ID": brsr_id,
                "SASB ID": sasb_id
            }
            ontology_df = pd.concat([ontology_df, pd.DataFrame([new_entry])], ignore_index=True)
            ontology_df.to_csv(ONTOLOGY_FILE, index=False)
            st.success("Ontology entry added.")
    st.markdown("### 📘 Ontology Table")
    search_filter = st.text_input("🔍 Filter ontology by keyword")
    if search_filter:
        ontology_df = ontology_df[ontology_df.apply(lambda row: search_filter.lower() in str(row).lower(), axis=1)]
    st.dataframe(ontology_df)
    st.text_input("🔍 Filter ontology entries by keyword", key="tab3_filter")
    if st.button("💾 Save Ontology"):
        ontology_df.to_csv(ONTOLOGY_FILE, index=False)
        st.success("Ontology saved.")
