
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Konfigurasi dasar DAG
default_args = {
    "owner": "ai_data_platform",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

# Lokasi folder pipeline Alfin di dalam container Airflow
PIPELINE_DIR = "/opt/airflow/sector-growth-pipeline/pipelines/ai_data_platform"

with DAG(
    dag_id="ai_data_platform_pipeline",
    default_args=default_args,
    schedule_interval="0 22 * * 0",
    catchup=False,
    description="AI Data Platform ETL Pipeline",
    tags=["ai_data_platform", "finops"],
) as dag:

    # Tahap 1: Tiga scraper berjalan paralel
    task_scrape_cnbc = BashOperator(
        task_id="scrape_cnbc_tech",
        bash_command=f"cd {PIPELINE_DIR} && python scraper_ai_cnbc.py",
    )

    task_scrape_detik = BashOperator(
        task_id="scrape_detik_inet",
        bash_command=f"cd {PIPELINE_DIR} && python scraper_detik.py",
    )

    task_scrape_rundown = BashOperator(
        task_id="scrape_therundown_ai",
        bash_command=f"cd {PIPELINE_DIR} && python scraper_therundown.py",
    )

    # Tahap 2: AI Enrichment
    task_ai_enrichment = BashOperator(
        task_id="ai_enrichment_filter",
        bash_command=f"cd {PIPELINE_DIR} && python ai_enrichment.py",
    )

    # Tahap 3: Load ke Neon PostgreSQL
    task_load_db = BashOperator(
        task_id="load_to_postgres",
        bash_command=f"cd {PIPELINE_DIR} && python load_to_db.py",
    )

    # Dependency: 3 scraper paralel -> enrichment -> load
    [
        task_scrape_cnbc,
        task_scrape_detik,
        task_scrape_rundown,
    ] >> task_ai_enrichment >> task_load_db
