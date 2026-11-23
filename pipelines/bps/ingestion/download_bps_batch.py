"""Batch downloader untuk BPS WebAPI.

Memakai ulang request, decoder, dan fungsi penyimpanan dari cek_api_bps.py.
Tidak mengubah atau menimpa cek_api_bps.py.

Jalankan dari root repository atau direktori mana pun:
    python spikes/Person1/BPS/WebAPI/download_bps_batch.py --dry-run
    python spikes/Person1/BPS/WebAPI/download_bps_batch.py
    python spikes/Person1/BPS/WebAPI/download_bps_batch.py --force

Default manifest berisi kombinasi variabel/periode yang sudah dieksplorasi:
- 2533 dan 2534: periode 122-125 (2022-2025)
- 2775 dan 2776: periode 126 (2026)
- 2836-2840: periode 126 (2026)

File pasangan JSON+CSV yang sudah ada akan dilewati, kecuali memakai --force.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
import shutil
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
CLIENT_PATH = SCRIPT_DIR / "cek_api_bps.py"

# Manifest awal sesuai eksplorasi Personel 1. Ubah di sini bila ada
# penambahan/pengurangan variabel atau periode yang telah diverifikasi.
BATCH_TASKS: list[tuple[str, str]] = [
    ("2533", "122"),
    ("2533", "123"),
    ("2533", "124"),
    ("2533", "125"),
    ("2534", "122"),
    ("2534", "123"),
    ("2534", "124"),
    ("2534", "125"),
    ("2775", "126"),
    ("2776", "126"),
 ]

INDICATOR_TASKS: list[tuple[str, str]] = [
    ("2836", "126"),
    ("2837", "126"),
    ("2838", "126"),
    ("2839", "126"),
    ("2840", "126"),
]


def load_client() -> Any:
    """Import cek_api_bps.py sebagai modul tanpa menjalankan main()."""
    if not CLIENT_PATH.is_file():
        raise FileNotFoundError(
            f"Script API tidak ditemukan: {CLIENT_PATH}"
        )

    spec = importlib.util.spec_from_file_location("bps_api_client", CLIENT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Tidak dapat memuat modul: {CLIENT_PATH}")

    module = importlib.util.module_from_spec(spec)
    # Didaftarkan agar import berbasis spec aman untuk modul yang memakai
    # introspeksi modul atau anotasi tipe.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def matching_existing_files(samples_dir: Path, var_id: str, period_id: str) -> tuple[list[Path], list[Path]]:
    """Cari snapshot terdahulu dengan pola nama timestamped dari explorer."""
    raw_files = list(samples_dir.glob(f"*_data_var_{var_id}_period_{period_id}.json"))
    csv_files = list(samples_dir.glob(f"*_data_var_{var_id}_period_{period_id}_decoded.csv"))
    return raw_files, csv_files


def copy_existing_pair(
    source_dir: Path,
    target_dir: Path,
    var_id: str,
    period_id: str,
) -> bool:
    """Salin pasangan JSON+CSV yang memiliki basename cocok dari cache lama."""
    raw_files, csv_files = matching_existing_files(
        source_dir, var_id, period_id
    )

    csv_by_stem = {
        path.stem.removesuffix("_decoded"): path
        for path in csv_files
        if path.is_file() and path.stat().st_size > 0
    }

    for raw_path in raw_files:
        if not raw_path.is_file() or raw_path.stat().st_size == 0:
            continue

        csv_path = csv_by_stem.get(raw_path.stem)
        if csv_path is None:
            continue

        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(raw_path, target_dir / raw_path.name)
        shutil.copy2(csv_path, target_dir / csv_path.name)
        print(f"[CACHE COPY] {raw_path.name} + {csv_path.name}")
        return True

    return False


def has_complete_existing_pair(samples_dir: Path, var_id: str, period_id: str) -> bool:
    raw_files, csv_files = matching_existing_files(samples_dir, var_id, period_id)
    raw_stems = {
        p.stem for p in raw_files
        if p.is_file() and p.stat().st_size > 0
    }
    csv_stems = {
        p.stem.removesuffix("_decoded") for p in csv_files
        if p.is_file() and p.stat().st_size > 0
    }
    return bool(raw_stems.intersection(csv_stems))


def make_endpoint(domain: str, var_id: str, period_id: str, client: Any) -> str:
    """Bangun endpoint dengan aturan encoding yang sama seperti explorer."""
    quote = client.quote
    return (
        "list/model/data/"
        f"domain/{quote(domain, safe='')}/"
        f"var/{quote(var_id, safe='')}/"
        f"th/{quote(period_id, safe='')}"
    )


def write_batch_summary(samples_dir: Path, records: list[dict[str, Any]]) -> Path:
    """Simpan ringkasan batch dalam CSV yang mudah diperiksa."""
    samples_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output = samples_dir / f"batch_summary_{timestamp}.csv"

    columns = [
        "variable_id",
        "period_id",
        "domain",
        "status",
        "total_rows",
        "decoded_rows",
        "warning_count",
        "duplicate_datacontent_key",
        "raw_json",
        "decoded_csv",
        "message",
    ]

    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    return output


def run_batch(
    *,
    dry_run: bool = False,
    force: bool = False,
    delay: float = 0.5,
    output_dir: Path | None = None,
    existing_dir: Path | None = None,
    include_indicators: bool = False,
) -> int:
    client = load_client()
    samples_dir = (
        Path(output_dir).expanduser().resolve()
        if output_dir else REPO_ROOT / "data" / "bps" / "raw"
    )
    existing_samples_dir = (
        Path(existing_dir).expanduser().resolve()
        if existing_dir else samples_dir
    )
    client.SAMPLES_DIR = samples_dir
    domain: str = client.DEFAULT_DOMAIN
    tasks = BATCH_TASKS + (INDICATOR_TASKS if include_indicators else [])
    if not dry_run:
        samples_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("BPS WEBAPI BATCH DOWNLOADER")
    print("=" * 72)
    print(f"Domain       : {domain}")
    print(f"Output       : {samples_dir}")
    print(f"Existing raw : {existing_samples_dir}")
    print(f"Total tugas  : {len(tasks)}")
    print(f"Indikator tambahan: {include_indicators}")
    print(f"Mode         : {'DRY RUN' if dry_run else 'DOWNLOAD'}")
    print(f"Force        : {force}")

    records: list[dict[str, Any]] = []
    success_count = 0
    skipped_count = 0
    warning_count = 0
    failed_count = 0

    for index, (var_id, period_id) in enumerate(tasks, start=1):
        print("\n" + "-" * 72)
        print(f"[{index}/{len(BATCH_TASKS)}] Variable {var_id} | Period {period_id}")

        existing_found = has_complete_existing_pair(
            existing_samples_dir, var_id, period_id
        )
        output_found = (
            existing_samples_dir != samples_dir
            and has_complete_existing_pair(samples_dir, var_id, period_id)
        )

        if not force and (existing_found or output_found):
            if existing_found and not output_found and existing_samples_dir != samples_dir:
                copied = copy_existing_pair(
                    existing_samples_dir, samples_dir, var_id, period_id
                )
                if not copied:
                    raise RuntimeError(
                        f"Pasangan cache tidak dapat disalin: {var_id}/{period_id}"
                    )
                status = "copied_existing"
                message = "Pasangan JSON+CSV disalin dari cache lama."
            else:
                status = "skipped_existing"
                message = "Pasangan JSON+CSV sudah tersedia di output."

            print(f"[SKIP] {message}")
            skipped_count += 1
            records.append({
                "variable_id": var_id,
                "period_id": period_id,
                "domain": domain,
                "status": status,
                "message": message,
            })
            continue

        if dry_run:
            print("[DRY RUN] Belum ada pasangan JSON+CSV; akan diunduh.")
            records.append({
                "variable_id": var_id,
                "period_id": period_id,
                "domain": domain,
                "status": "would_download",
                "message": "Dry run; tidak ada request ke API.",
            })
            continue

        raw_name = f"batch_data_var_{var_id}_period_{period_id}.json"
        csv_name = f"batch_data_var_{var_id}_period_{period_id}_decoded.csv"

        try:
            endpoint = make_endpoint(domain, var_id, period_id, client)
            payload = client.request_json(endpoint)

            rows, warnings = client.decode_datacontent(payload, domain)
            if not isinstance(rows, list):
                raise TypeError("Decoder tidak mengembalikan list observasi.")

            # Simpan raw dan hasil decode setelah request dan decoding berhasil.
            raw_path = client.save_json(payload, raw_name)
            csv_path = client.save_csv(rows, csv_name)

            decoded_rows = sum(
                str(row.get("decode_status", "")).lower() == "decoded"
                for row in rows
            )
            keys = [
                str(row.get("datacontent_key", ""))
                for row in rows
                if str(row.get("datacontent_key", "")).strip()
            ]
            duplicate_keys = len(keys) - len(set(keys))

            if not rows:
                status = "empty_result"
                warning_count += 1
            elif warnings or decoded_rows != len(rows) or duplicate_keys:
                status = "completed_with_warnings"
                warning_count += 1
            else:
                status = "success"
                success_count += 1

            print(f"Status              : {status}")
            print(f"Total observasi     : {len(rows):,}")
            print(f"Berhasil decoded    : {decoded_rows:,}")
            print(f"Decode warnings     : {len(warnings)}")
            print(f"Duplikasi data key  : {duplicate_keys}")
            print(f"Raw JSON            : {raw_path.name}")
            print(f"Decoded CSV         : {csv_path.name}")

            # Cetak maksimal lima warning agar terminal tetap terbaca.
            for warning in warnings[:5]:
                print(f"[WARNING] {warning}")
            if len(warnings) > 5:
                print(f"[WARNING] ... {len(warnings) - 5} warning lain disimpan tidak ditampilkan.")

            records.append({
                "variable_id": var_id,
                "period_id": period_id,
                "domain": domain,
                "status": status,
                "total_rows": len(rows),
                "decoded_rows": decoded_rows,
                "warning_count": len(warnings),
                "duplicate_datacontent_key": duplicate_keys,
                "raw_json": raw_path.name,
                "decoded_csv": csv_path.name,
                "message": "; ".join(warnings[:5]),
            })

        except Exception as exc:  # satu kegagalan tidak menghentikan tugas berikutnya
            failed_count += 1
            message = f"{type(exc).__name__}: {exc}"
            print(f"[FAILED] {message}")
            records.append({
                "variable_id": var_id,
                "period_id": period_id,
                "domain": domain,
                "status": "failed",
                "message": message,
            })

        if delay > 0 and index < len(tasks):
            time.sleep(delay)

    summary_path = None if dry_run else write_batch_summary(samples_dir, records)

    print("\n" + "=" * 72)
    print("BATCH SUMMARY")
    print("=" * 72)
    print(f"Berhasil              : {success_count}")
    print(f"Dilewati (sudah ada)  : {skipped_count}")
    print(f"Selesai dengan warning: {warning_count}")
    print(f"Gagal                 : {failed_count}")
    if dry_run:
        would_download = sum(r["status"] == "would_download" for r in records)
        print(f"Akan diunduh          : {would_download}")
    print(f"Ringkasan             : {summary_path if summary_path else 'Tidak ditulis (dry-run)'}")

    return 1 if failed_count else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch download BPS WebAPI menggunakan decoder cek_api_bps.py."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Periksa daftar tugas dan file yang sudah ada tanpa request API.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Unduh ulang walaupun pasangan JSON dan CSV sudah tersedia.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Direktori output raw JSON, decoded CSV, dan batch summary.",
    )
    parser.add_argument(
        "--existing-dir",
        type=Path,
        default=None,
        help="Direktori raw JSON dan decoded CSV yang sudah tersedia.",
    )
    parser.add_argument(
        "--include-indicators",
        action="store_true",
        help="Sertakan lima indikator tambahan 2836-2840.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Jeda antar-request dalam detik (default: 0.5).",
    )
    args = parser.parse_args()

    if args.delay < 0:
        parser.error("--delay tidak boleh negatif.")

    try:
        exit_code = run_batch(
            dry_run=args.dry_run,
            force=args.force,
            delay=args.delay,
            output_dir=args.output_dir,
            existing_dir=args.existing_dir,
            include_indicators=args.include_indicators,
        )
    except Exception as exc:
        print(f"[FATAL] {type(exc).__name__}: {exc}", file=sys.stderr)
        exit_code = 1

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
