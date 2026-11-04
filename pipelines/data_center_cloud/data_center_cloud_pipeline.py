from datetime import datetime

import psycopg2

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator


PIPELINE_DIR = "/opt/airflow/data-center-pipeline"


# ==========================================
# UPDATE WAKTU PIPELINE DI DATA_CENTER_NEWS
# ==========================================

def update_pipeline_status():
    conn = psycopg2.connect(
        host="host.docker.internal",
        port=5432,
        dbname="data_center_insight",
        user="postgres",
        password="12345",
    )

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE public.data_center_news
                SET pipeline_last_updated = NOW();
            """)

            updated_rows = cursor.rowcount

        conn.commit()

        print(
            f"Waktu pembaruan pipeline berhasil disimpan. "
            f"Jumlah baris diperbarui: {updated_rows}"
        )

        if updated_rows == 0:
            print(
                "PERINGATAN: data_center_news kosong, "
                "tidak ada baris untuk menyimpan waktu pembaruan."
            )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


with DAG(
    dag_id="data_center_pipeline",
    start_date=datetime(2026, 9, 21),
    schedule_interval="@weekly",
    catchup=False,
    tags=["data-center", "multi-source", "subtopic"],
) as dag:

    # ==========================================
    # ANTARA
    # ==========================================

    scrape_antara = BashOperator(
        task_id="scrape_antaranews",
        bash_command=f"cd {PIPELINE_DIR} && python antaranews_scraping.py",
    )

    content_antara = BashOperator(
        task_id="content_antaranews",
        bash_command=f"cd {PIPELINE_DIR} && python antaranews_article_scraping.py",
    )

    clean_antara = BashOperator(
        task_id="clean_antaranews",
        bash_command=f"cd {PIPELINE_DIR} && python clean_filter_antaranews.py",
    )

    filter_antara = BashOperator(
        task_id="filter_current_antaranews",
        bash_command=f"cd {PIPELINE_DIR} && python filter_current_antaranews.py",
    )

    insight_antara = BashOperator(
        task_id="insight_antaranews",
        bash_command=f"cd {PIPELINE_DIR} && python extract_business_insight.py",
    )

    classify_antara = BashOperator(
        task_id="classify_subtopic_antaranews",
        bash_command=(
            f"cd {PIPELINE_DIR} && "
            "python classify_subtopic_pipeline.py antaranews"
        ),
    )

    load_antara = BashOperator(
        task_id="load_antaranews",
        bash_command=f"cd {PIPELINE_DIR} && python load_postgresql.py",
    )

    # ==========================================
    # KATADATA
    # ==========================================

    scrape_katadata = BashOperator(
        task_id="scrape_katadata",
        bash_command=f"cd {PIPELINE_DIR} && python katadata_scraping.py",
    )

    content_katadata = BashOperator(
        task_id="content_katadata",
        bash_command=f"cd {PIPELINE_DIR} && python katadata_article_scraping.py",
    )

    clean_katadata = BashOperator(
        task_id="clean_katadata",
        bash_command=f"cd {PIPELINE_DIR} && python clean_filter_katadata.py",
    )

    filter_katadata = BashOperator(
        task_id="filter_current_katadata",
        bash_command=f"cd {PIPELINE_DIR} && python filter_current_katadata.py",
    )

    insight_katadata = BashOperator(
        task_id="insight_katadata",
        bash_command=(
            f"cd {PIPELINE_DIR} && "
            "python extract_business_insight_katadata.py"
        ),
    )

    classify_katadata = BashOperator(
        task_id="classify_subtopic_katadata",
        bash_command=(
            f"cd {PIPELINE_DIR} && "
            "python classify_subtopic_pipeline.py katadata"
        ),
    )

    load_katadata = BashOperator(
        task_id="load_katadata",
        bash_command=(
            f"cd {PIPELINE_DIR} && python load_katadata_postgresql.py"
        ),
    )

    # ==========================================
    # KOMPAS
    # ==========================================

    scrape_kompas = BashOperator(
        task_id="scrape_kompas",
        bash_command=f"cd {PIPELINE_DIR} && python kompas_scraping.py",
    )

    clean_kompas = BashOperator(
        task_id="clean_kompas",
        bash_command=f"cd {PIPELINE_DIR} && python clean_filter_kompas.py",
    )

    filter_kompas = BashOperator(
        task_id="filter_current_kompas",
        bash_command=f"cd {PIPELINE_DIR} && python filter_current_kompas.py",
    )

    insight_kompas = BashOperator(
        task_id="insight_kompas",
        bash_command=(
            f"cd {PIPELINE_DIR} && "
            "python extract_business_insight_kompas.py"
        ),
    )

    classify_kompas = BashOperator(
        task_id="classify_subtopic_kompas",
        bash_command=(
            f"cd {PIPELINE_DIR} && "
            "python classify_subtopic_pipeline.py kompas"
        ),
    )

    load_kompas = BashOperator(
        task_id="load_kompas",
        bash_command=f"cd {PIPELINE_DIR} && python load_kompas_postgresql.py",
    )

    # ==========================================
    # UPDATE WAKTU SETELAH SEMUA LOADING SUKSES
    # ==========================================

    update_status = PythonOperator(
        task_id="update_pipeline_status",
        python_callable=update_pipeline_status,
    )

    # ==========================================
    # DEPENDENCY ANTARA
    # ==========================================

    (
        scrape_antara
        >> content_antara
        >> clean_antara
        >> filter_antara
        >> insight_antara
        >> classify_antara
        >> load_antara
    )

    # ==========================================
    # DEPENDENCY KATADATA
    # ==========================================

    (
        scrape_katadata
        >> content_katadata
        >> clean_katadata
        >> filter_katadata
        >> insight_katadata
        >> classify_katadata
        >> load_katadata
    )

    # ==========================================
    # DEPENDENCY KOMPAS
    # ==========================================

    (
        scrape_kompas
        >> clean_kompas
        >> filter_kompas
        >> insight_kompas
        >> classify_kompas
        >> load_kompas
    )

    # ==========================================
    # KETIGA LOADING HARUS BERHASIL
    # SEBELUM WAKTU DIPERBARUI
    # ==========================================

    [load_antara, load_katadata, load_kompas] >> update_status