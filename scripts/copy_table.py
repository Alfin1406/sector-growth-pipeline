"""Salin satu tabel dari database SUMBER (lama) ke database TUJUAN (baru). Aman diulang.

Contoh:
  python scripts/copy_table.py --table tabel_berita_ai
  python scripts/copy_table.py --table data_center_news --serial-column id

Sumber dibaca dari SRC_* dan tujuan dari POSTGRES_* di file .env
"""
import argparse
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

TABLES = ["tabel_berita_ai", "data_center_news", "sector3_articles"]


def connect(prefix: str, dbname: str | None = None):
    return psycopg2.connect(
        host=os.environ[f"{prefix}_HOST"],
        port=os.getenv(f"{prefix}_PORT", "5432"),
        dbname=dbname or os.environ[f"{prefix}_DB"],
        user=os.environ[f"{prefix}_USER"],
        password=os.environ[f"{prefix}_PASSWORD"],
        sslmode=os.getenv(f"{prefix}_SSLMODE", "prefer"),
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--table", required=True, choices=TABLES)
    p.add_argument("--src-db", help="Timpa SRC_DB di .env")
    p.add_argument("--serial-column", help="Kolom serial (mis. id) untuk disinkronkan")
    p.add_argument("--yes", action="store_true", help="Lewati konfirmasi")
    a = p.parse_args()
    t = a.table

    src = connect("SRC", a.src_db)
    dst = connect("POSTGRES")
    try:
        print(f"SUMBER : {src.info.host}/{src.info.dbname}.public.{t}")
        print(f"TUJUAN : {dst.info.host}/{dst.info.dbname}.public.{t}")
        if not a.yes and input("Lanjut menyalin? (y/n) ").strip().lower() != "y":
            raise SystemExit("Dibatalkan.")

        with src.cursor() as cs, dst.cursor() as cd:
            cd.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",
                (t,),
            )
            cols = [r[0] for r in cd.fetchall()]
            if not cols:
                raise SystemExit(f"Tabel {t} belum ada di tujuan (jalankan alembic upgrade head).")
            col_sql = ", ".join(f'"{c}"' for c in cols)

            cs.execute(f"SELECT {col_sql} FROM public.{t}")
            rows = cs.fetchall()

            cd.execute(f"SELECT count(*) FROM public.{t}")
            before = cd.fetchone()[0]
            if rows:
                execute_values(
                    cd,
                    f"INSERT INTO public.{t} ({col_sql}) VALUES %s ON CONFLICT DO NOTHING",
                    rows,
                    page_size=200,
                )
            if a.serial_column:
                c = a.serial_column
                cd.execute(
                    f"SELECT setval(pg_get_serial_sequence('public.{t}', '{c}'), "
                    f"COALESCE(MAX({c}), 1), MAX({c}) IS NOT NULL) FROM public.{t}"
                )
            cd.execute(f"SELECT count(*) FROM public.{t}")
            after = cd.fetchone()[0]
        dst.commit()
        print(f"Baris di sumber: {len(rows)} | tujuan sebelum: {before} | sesudah: {after}")
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    main()