
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator


# Folder project di dalam Docker
PROJECT_DIR = "/opt/airflow/sector-growth-pipeline/pipelines/digital_transformation_it"


def project_command(script: str, *args: str) -> str:
    command = " ".join([f"python {script}", *args])
    return f"set -euo pipefail\ncd {PROJECT_DIR}\n{command}\n"


def dag_bash(task_id: str, script: str, *args: str, **kwargs) -> BashOperator:
    return BashOperator(
        task_id=task_id,
        bash_command=project_command(script, *args),
        **kwargs,
    )


default_args = {
    "owner": "atha",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


with DAG(
    dag_id="sector3_pipeline",
    description="Sector 3 Digital Transformation & IT Enterprise Pipeline",
    start_date=datetime(2026, 10, 8),
    schedule_interval="@weekly",
    catchup=False,
    default_args=default_args,
    tags=["sector3", "digital-transformation", "antara", "detik", "katadata"],
) as dag:

    # START
    start = EmptyOperator(task_id="start_pipeline")

    # ========================================================
    # ANTARA SEARCH
    # ========================================================
    antara_scrape = dag_bash(
        "antara_scrape",
        "scrape_antara_search.py",
    )

    antara_prepare = dag_bash(
        "antara_prepare_summary",
        "prepare_antara_search_summary.py",
    )

    antara_clean = dag_bash(
        "antara_clean",
        "clean_antara_search.py",
    )

    antara_filter_v4 = dag_bash(
        "antara_filter_v4",
        "filter_antara_search_v4.py",
    )

    antara_filter_v5 = dag_bash(
        "antara_filter_v5",
        "filter_antara_search_v5.py",
    )

    antara_validate = dag_bash(
        "antara_validate_postgres_input",
        "load_antara_search_to_postgres.py",
        "--dry-run",
    )

    antara_load = dag_bash(
        "antara_load_postgres",
        "load_antara_search_to_postgres.py",
    )

    # ========================================================
    # KATADATA
    # ========================================================
    katadata_scrape = dag_bash(
        "katadata_scrape",
        "scrape_katadata_enterprise.py",
    )

    katadata_clean = dag_bash(
        "katadata_clean",
        "clean_katadata_enterprise_updated.py",
    )

    katadata_filter = dag_bash(
        "katadata_filter",
        "filter_katadata_enterprise_updated.py",
    )

    katadata_insight = dag_bash(
        "katadata_insight",
        "extract_enterprise_insight.py",
    )

    katadata_load = dag_bash(
        "katadata_load_postgres",
        "load_katadata_to_postgres.py",
    )

    # ========================================================
    # DETIK.COM
    # ========================================================
    detik_scrape = dag_bash(
        "detik_scrape",
        "scrape_detik_sector3.py",
    )

    detik_clean = dag_bash(
        "detik_clean",
        "clean_detik_sector3.py",
    )

    detik_filter = dag_bash(
        "detik_filter_v5",
        "filter_detik_sector3_v5.py",
    )

    detik_normalize = dag_bash(
        "detik_normalize_four_topics_v5",
        "normalize_detik_four_topics_v5.py",
    )

    detik_insight = dag_bash(
        "detik_insight_four_topics_v5",
        "extract_detik_insight_four_topics_v5.py",
    )

    detik_validate = dag_bash(
        "detik_validate_postgres_input",
        "load_detik_to_postgres.py",
        "--dry-run",
    )

    detik_load = dag_bash(
        "detik_load_postgres",
        "load_detik_to_postgres.py",
    )

    # END
    pipeline_done = EmptyOperator(task_id="pipeline_done")

    # ANTARA dependency
    (
        start
        >> antara_scrape
        >> antara_prepare
        >> antara_clean
        >> antara_filter_v4
        >> antara_filter_v5
        >> antara_validate
        >> antara_load
    )

    # KATADATA dependency
    (
        start
        >> katadata_scrape
        >> katadata_clean
        >> katadata_filter
        >> katadata_insight
        >> katadata_load
    )

    # DETIK dependency
    (
        start
        >> detik_scrape
        >> detik_clean
        >> detik_filter
        >> detik_normalize
        >> detik_insight
        >> detik_validate
        >> detik_load
    )

    # Finish after all branches succeed
    [antara_load, katadata_load, detik_load] >> pipeline_done