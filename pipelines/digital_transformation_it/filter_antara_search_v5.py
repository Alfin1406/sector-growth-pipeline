#!/usr/bin/env python3
"""ANTARA Search V5: policy-aligned, title/snippet-only audit.

This script applies an explicit, reviewable set of decisions to the V4 result.
It does NOT fetch article pages. Since ANTARA Search snippets are truncated,
uncertain cases remain in Perlu Tinjau rather than being promoted by keyword alone.

Default paths (when run from the project root):
  input : data/processed/antara_search_all_classified_v4.csv
  output: data/processed/*_v5.csv

Optional:
  python 04_filtering/filter_antara_search_v5.py --input <csv> --output-dir <dir>
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

TOPIC = {
    "antara_5721756": "Enterprise Software",  # Boomi data/workflow use at HEB Construction
    "antara_5615964": "Cloud Enterprise",     # IONext.ai enterprise AI cloud platform
    "antara_5590344": "Enterprise Software",  # Hyland content/agentic enterprise solution
    "antara_5547475": "Cloud Enterprise",     # enterprise infrastructure for AI workloads
    "antara_5662008": "Enterprise Software",  # Geene 2.0 / AI commerce business platform
    "antara_5636701": "Cyber Security",       # EUCC-certified network camera product
    "antara_5630400": "Digital Transformation", # digital border-monitoring pilot
    "antara_5752812": "Digital Transformation", # Huawei SCALE partner enablement system
    "antara_5694857": "Digital Transformation", # deployed JAKI public-service application
    "antara_5386274": "Digital Transformation", # Lintasarta LAMPU digital platform
    "antara_5684424": "Cloud Enterprise",     # data-storage solution portfolio for AI
}
PROMOTE_TO_RELEVANT = {
    "antara_5721756": "Snippet describes HEB Construction establishing a workforce-data source of truth to produce tender responses; concrete enterprise data/workflow use case.",
    "antara_5615964": "Title and snippet identify a named cloud AI platform designed for enterprise implementation.",
    "antara_5590344": "Title and snippet identify a concrete content-based agentic enterprise solution involving Hyland and AWS.",
    "antara_5547475": "Snippet explicitly identifies Altos as an enterprise-infrastructure provider and describes an ecosystem for AI workloads.",
    "antara_5662008": "Title identifies the launch of Geene 2.0 and an AI-commerce business ecosystem; retained as enterprise software with moderate confidence.",
    "antara_5636701": "Snippet identifies a specific network-camera product and EUCC security certification; concrete product-security evidence.",
    "antara_5630400": "Title identifies a digital border-monitoring initiative being developed with ITB; concrete digital-system pilot.",
    "antara_5752812": "Snippet identifies Huawei SCALE as a newly introduced partner-support system to accelerate enterprise AI adoption.",
    "antara_5694857": "Snippet reports adoption of the named JAKI public-service application with a quantified download count; concrete deployed digital service.",
    "antara_5386274": "Snippet identifies Lintasarta LAMPU as a named integrated AI-based digital platform introduced to the market.",
    "antara_5684424": "Snippet identifies a named provider's data-storage product/solution portfolio positioned for AI scenarios; infrastructure product evidence is present, but confidence remains moderate.",
}

# Existing V4 Relevant items downgraded because the snippet indicates a topic or
# risk discussion, but not a concrete technology, solution, deployment, product,
# or infrastructure implementation.
DEMOTE_TO_REVIEW = {
    "antara_5830487": "Expert commentary about digital espionage and strategic-data protection; no concrete security implementation is visible in the snippet.",
    "antara_5820399": "Governmental cooperation against cross-border cyber threats is described, but no concrete security system or implementation is identified.",
    "antara_5790669": "General anticipation of quantum-computing risks to data security; no concrete protective solution is identified.",
    "antara_5759716": "Data-center electricity consumption is an industry metric, not evidence of a specific cloud/data-center solution or deployment.",
    "antara_5693099": "General statement about AI changing the cyber-attack landscape; no concrete security product or implementation is identified.",
    "antara_5688080": "Official commentary about quantum-related cyber threats; no concrete mitigation technology or implementation is identified.",
    "antara_5631581": "Phishing trend statistics are relevant background, but the snippet does not identify a concrete security solution or implementation.",
    "antara_5629444": "A bank's strategic priority to optimize cybersecurity is not, by itself, evidence of a concrete technology or deployment.",
    "antara_5539189": "A future target to deploy AI agents by 2028 is a plan rather than a demonstrated implementation in the available snippet.",
    "antara_5767045": "General discussion of enterprise-software integration needs; no named product, deployment, or concrete implementation is described.",
}

# Clearly outside the four Sector 3 topics based on the available title/snippet:
# awards, general policy/commentary, events/conferences, education/talent, or
# unrelated business/financial topics without a concrete in-scope technology.
MOVE_TO_OOS = {
    "antara_5819615": "Policy/expert recommendation about algorithm transparency; no concrete enterprise technology or implementation is identified.",
    "antara_5817191": "Award announcement; the snippet does not describe a concrete technology or digital-system implementation.",
    "antara_5806255": "General executive commentary about the AI-orchestrator role; no specific product or implementation is identified.",
    "antara_5776926": "General business-transformation result without a specific in-scope technology, product, system, or infrastructure.",
    "antara_5770025": "Open-source gadget project is not shown to address the four Sector 3 enterprise/cloud/cyber/digital-transformation topics.",
    "antara_5768443": "Education-program coverage about digital security, not a technology solution or deployment.",
    "antara_5762035": "General cooperative-development program; no in-scope digital technology or system is identified.",
    "antara_5762920": "Conference/event coverage about cybersecurity and agentic AI; no concrete solution or implementation is described in the snippet.",
    "antara_5751573": "General government-industry collaboration statement about digital transformation, without a concrete system or implementation.",
    "antara_5751167": "High-level ministry strategy coverage; the snippet does not identify a specific digital system or technology implementation.",
    "antara_5739931": "Conference announcement for a shared-services/outsourcing event, without a concrete in-scope technology implementation.",
    "antara_5735229": "Legal/policy commentary about personal-data protection for UMKM, without a concrete cybersecurity product or implementation.",
    "antara_5727220": "Academic degree/research coverage, not a concrete technology product or enterprise implementation.",
    "antara_5711447": "General technology-talent development statement, not a technology solution or deployment.",
    "antara_5705205": "Cybersecurity workforce/talent commentary, without a specific security system or product.",
    "antara_5704871": "General investment-interest coverage unrelated to a concrete Sector 3 technology or implementation.",
    "antara_5689557": "Investment and technology-transfer agenda around a summit; no specific product or implementation is identified.",
    "antara_5683396": "General policy statement about comprehensive digital development, without a concrete system or solution.",
    "antara_5682168": "Conference/exhibition coverage about digital connectivity; no concrete solution or deployment is identified.",
    "antara_5657688": "Regional discussion/forum about AI-based connectivity strategy, not a specific product or implementation.",
    "antara_5658295": "General financial-center ecosystem statement without an in-scope technology or digital-system implementation.",
    "antara_5647861": "Scholarship and talent-development coverage, not a technology solution or deployment.",
    "antara_5640912": "Policy planning for creative-industry talent and competitiveness, without a concrete Sector 3 technology.",
    "antara_5635725": "Commentary about the duties of an online-gambling task force; no concrete cybersecurity technology is identified.",
    "antara_5635707": "Commentary about coordination of an online-gambling task force; no concrete cybersecurity technology is identified.",
    "antara_5616399": "Conference coverage about child safety in the digital era, without a concrete Sector 3 technology implementation.",
    "antara_5598873": "Announcement of a business summit, not a concrete enterprise technology or implementation.",
    "antara_5552009": "Cloud-AI use for creator content production is outside the defined enterprise/cloud infrastructure focus based on the available snippet.",
    "antara_5540252": "Market outlook about global companies' digital presence in Indonesia, without a concrete cloud product or deployment.",
    "antara_5571619": "General statement of readiness to support BUMN transformation with cloud and AI; no specific solution or deployment is described.",
    "antara_5667115": "General discussion of IT downtime as an industry problem; no specific remediation technology or implementation is described.",
}


def main() -> None:
    project_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=project_root / "data/processed/antara_search_all_classified_v4.csv")
    parser.add_argument("--output-dir", type=Path, default=project_root / "data/processed")
    args = parser.parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"Input V4 tidak ditemukan: {args.input}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input)
    required = {"article_id", "title", "summary", "relevance_level", "sector3_topic"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan: {sorted(missing)}")
    if df["article_id"].duplicated().any():
        raise ValueError("article_id duplikat ditemukan; hentikan sebelum klasifikasi V5.")

    df["relevance_level_v4"] = df["relevance_level"]
    df["sector3_topic_v4"] = df["sector3_topic"]
    df["v5_audit_action"] = "Dipertahankan dari V4"
    df["v5_audit_note"] = "Dipertahankan; tidak ada bukti snippet yang cukup kuat untuk mengubah keputusan V4."

    indexed = df.set_index("article_id", drop=False)
    ids = set(indexed.index.astype(str))
    declared = set(PROMOTE_TO_RELEVANT) | set(DEMOTE_TO_REVIEW) | set(MOVE_TO_OOS)
    unknown = declared - ids
    if unknown:
        print("\nPERINGATAN: Keputusan manual dilewati karena ID tidak ditemukan pada V4:")
    for aid in sorted(unknown):
        print(f"- {aid}")
    overlap = (set(PROMOTE_TO_RELEVANT) & set(DEMOTE_TO_REVIEW)) | (set(PROMOTE_TO_RELEVANT) & set(MOVE_TO_OOS)) | (set(DEMOTE_TO_REVIEW) & set(MOVE_TO_OOS))
    if overlap:
        raise ValueError(f"Ada keputusan V5 yang saling tumpang tindih: {sorted(overlap)}")

    for aid, note in PROMOTE_TO_RELEVANT.items():
        m = df.article_id.eq(aid)
        df.loc[m, "relevance_level"] = "Relevan"
        df.loc[m, "sector3_topic"] = TOPIC[aid]
        df.loc[m, "classification_confidence"] = "Sedang"
        df.loc[m, "review_priority"] = "Low"
        df.loc[m, "manual_review_recommended"] = False
        df.loc[m, "classification_reason"] = note
        df.loc[m, "classification_evidence"] = f"title={df.loc[m, 'title'].iloc[0]} | summary={df.loc[m, 'summary'].iloc[0]}"
        df.loc[m, "classification_rule_override"] = "v5_scope_evidence_promotion"
        df.loc[m, "classification_rule_evidence"] = note
        df.loc[m, "v5_audit_action"] = "Promosi Review → Relevan"
        df.loc[m, "v5_audit_note"] = note

    for aid, note in DEMOTE_TO_REVIEW.items():
        m = df.article_id.eq(aid)
        df.loc[m, "relevance_level"] = "Perlu Tinjau"
        df.loc[m, "classification_confidence"] = "Rendah"
        df.loc[m, "review_priority"] = "Medium"
        df.loc[m, "manual_review_recommended"] = True
        df.loc[m, "classification_reason"] = note
        df.loc[m, "classification_rule_override"] = "v5_scope_evidence_demotion"
        df.loc[m, "classification_rule_evidence"] = note
        df.loc[m, "v5_audit_action"] = "Turun Relevan → Perlu Tinjau"
        df.loc[m, "v5_audit_note"] = note

    for aid, note in MOVE_TO_OOS.items():
        m = df.article_id.eq(aid)
        df.loc[m, "relevance_level"] = "Di Luar Cakupan"
        df.loc[m, "sector3_topic"] = "Di Luar Cakupan"
        df.loc[m, "classification_confidence"] = "Sedang"
        df.loc[m, "review_priority"] = "Low"
        df.loc[m, "manual_review_recommended"] = False
        df.loc[m, "classification_reason"] = note
        df.loc[m, "classification_rule_override"] = "v5_scope_evidence_out_of_scope"
        df.loc[m, "classification_rule_evidence"] = note
        df.loc[m, "v5_audit_action"] = "Perlu Tinjau → Di Luar Cakupan"
        df.loc[m, "v5_audit_note"] = note

    df["classification_version"] = "v5"
    df["classification_method"] = "title_summary_scope_audit_v5"
    # Recompute derived audit flags and retain all original source/cleaning fields.
    df["manual_review_recommended"] = df["relevance_level"].eq("Perlu Tinjau")

    stem = "antara_search_"
    paths = {
        "all": args.output_dir / f"{stem}all_classified_v5.csv",
        "filtered": args.output_dir / f"{stem}filtered_v5.csv",
        "review": args.output_dir / f"{stem}review_v5.csv",
        "oos": args.output_dir / f"{stem}out_of_scope_v5.csv",
        "audit": args.output_dir / f"{stem}review_audit_v5.csv",
        "report": args.output_dir / f"{stem}filter_report_v5.csv",
        "comparison": args.output_dir / f"{stem}filter_comparison_v4_v5.csv",
        "decisions": args.output_dir / f"{stem}v5_audit_decisions.csv",
    }
    df.to_csv(paths["all"], index=False, encoding="utf-8-sig")
    rel = df[df.relevance_level.eq("Relevan")].copy()
    rev = df[df.relevance_level.eq("Perlu Tinjau")].copy()
    oos = df[df.relevance_level.eq("Di Luar Cakupan")].copy()
    rel.to_csv(paths["filtered"], index=False, encoding="utf-8-sig")
    rev.to_csv(paths["review"], index=False, encoding="utf-8-sig")
    oos.to_csv(paths["oos"], index=False, encoding="utf-8-sig")

    audit_cols = [c for c in ["article_id", "title", "summary", "url", "published_at", "search_query", "sector3_topic", "relevance_level", "classification_confidence", "review_priority", "classification_reason", "classification_evidence", "v5_audit_action", "v5_audit_note", "manual_relevance", "manual_topic", "audit_notes"] if c in rev.columns]
    audit = rev[audit_cols].copy()
    for c in ["manual_relevance", "manual_topic", "audit_notes"]:
        if c not in audit.columns:
            audit[c] = ""
    audit.to_csv(paths["audit"], index=False, encoding="utf-8-sig")

    rows = [{"metric": "total_articles", "value": len(df)}]
    for status in ["Relevan", "Perlu Tinjau", "Di Luar Cakupan"]:
        n = int(df.relevance_level.eq(status).sum())
        rows.append({"metric": f"status_{status}", "value": n})
    for topic, n in rel.sector3_topic.value_counts().items():
        rows.append({"metric": f"relevant_topic_{topic}", "value": int(n)})
    rows.extend([
            {"metric": "promoted_review_to_relevant", "value": int(df["v5_audit_action"].eq("Promosi Review → Relevan").sum())},
            {"metric": "demoted_relevant_to_review", "value": int(df["v5_audit_action"].eq("Turun Relevan → Perlu Tinjau").sum())},
            {"metric": "moved_review_to_out_of_scope", "value": int(df["v5_audit_action"].eq("Perlu Tinjau → Di Luar Cakupan").sum())},
            {"metric": "summary_truncated_rows", "value": int(df.get("summary_truncated_indicator", pd.Series(False, index=df.index)).fillna(False).astype(bool).sum())},
            {"metric": "duplicate_article_id", "value": int(df.article_id.duplicated().sum())},
            {"metric": "duplicate_url", "value": int(df.url.duplicated().sum()) if "url" in df else 0},
    ])
    pd.DataFrame(rows).to_csv(paths["report"], index=False, encoding="utf-8-sig")
    comp = pd.crosstab(df["relevance_level_v4"], df["relevance_level"]).reset_index()
    comp.to_csv(paths["comparison"], index=False, encoding="utf-8-sig")
    changed = df[df["v5_audit_action"].ne("Dipertahankan dari V4")][["article_id", "title", "relevance_level_v4", "relevance_level", "sector3_topic_v4", "sector3_topic", "v5_audit_action", "v5_audit_note"]].copy()
    changed.to_csv(paths["decisions"], index=False, encoding="utf-8-sig")

    # Strong partition checks.
    if len(rel) + len(rev) + len(oos) != len(df):
        raise AssertionError("Partisi status V5 tidak lengkap.")
    if set(rel.article_id) & set(rev.article_id) or set(rel.article_id) & set(oos.article_id) or set(rev.article_id) & set(oos.article_id):
        raise AssertionError("Ada article_id yang masuk lebih dari satu status.")

    print("=== ANTARA SEARCH V5 SELESAI ===")
    print(f"Input       : {args.input}")
    print(f"Total       : {len(df)}")
    print(f"Relevan     : {len(rel)}")
    print(f"Review      : {len(rev)}")
    print(f"Out of Scope: {len(oos)}")
    print("Topik Relevan:")
    print(rel.sector3_topic.value_counts().to_string())
    print(f"Promosi     : {len(PROMOTE_TO_RELEVANT)}")
    print(f"Demosi      : {len(DEMOTE_TO_REVIEW)}")
    print(f"Review→OOS  : {len(MOVE_TO_OOS)}")
    print("\nFile output:")
    for name, p in paths.items():
        print(f"- {p}")

if __name__ == "__main__":
    main()
