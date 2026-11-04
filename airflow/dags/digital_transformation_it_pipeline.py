
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator


# Folder project di dalam Docker
PROJECT_DIR = "/opt/airflow/sector-growth-pipeline/pipelines/digital_transformation_it"


def project_command(script: str, *args: str) -> str:
    """Build a fail-fast Bash command executed from the project root."""
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
    tags=["sector3", "digital-transformation", "detik", "katadata", "bisnis-cyber"],
) as dag:

    # ========================================================
    # START
    # ========================================================
    start = EmptyOperator(task_id="start_pipeline")

    # ========================================================
    # BISNIS.COM CYBER SECURITY
    # ========================================================
    bisnis_scrape = dag_bash(
        "bisnis_scrape",
        "scrape_bisnis_cyber.py",
    )

    bisnis_content = dag_bash(
        "bisnis_content",
        "scrape_bisnis_cyber_content.py",
    )

    bisnis_clean = dag_bash(
        "bisnis_clean",
        "clean_bisnis_cyber.py",
    )

    bisnis_filter = dag_bash(
        "bisnis_filter",
        "filter_bisnis_cyber.py",
    )

    bisnis_insight = dag_bash(
        "bisnis_insight",
        "extract_cyber_insight.py",
    )

    bisnis_load = dag_bash(
        "bisnis_load_postgres",
        "load_cyber_to_postgres.py",
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

    # ========================================================
    # END
    # ========================================================
    pipeline_done = EmptyOperator(task_id="pipeline_done")

    # Bisnis.com Cyber Security
    (
        start
        >> bisnis_scrape
        >> bisnis_content
        >> bisnis_clean
        >> bisnis_filter
        >> bisnis_insight
        >> bisnis_load
    )

    # Katadata
    (
        start
        >> katadata_scrape
        >> katadata_clean
        >> katadata_filter
        >> katadata_insight
        >> katadata_load
    )

    # Detik.com
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
    [bisnis_load, katadata_load, detik_load] >> pipeline_done
