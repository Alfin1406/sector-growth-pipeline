
#!/usr/bin/env python3
"""
BPS WebAPI Explorer V2
Project  : Sector Growth Insight Foundation
Personel : 1

Features:
1. Strategic Indicators
2. Dynamic Variables + keyword discovery
3. Dynamic Periods by Variable ID
4. Dynamic Data extraction
5. Decode datacontent into labeled observations
6. Export raw JSON and decoded CSV

API key is loaded from repository-root .env.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import os
import re
import sys

from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from dotenv import load_dotenv


# ============================================================
# 1. CONFIGURATION
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent


def find_repo_root(start: Path) -> Path:
    """Find repository root using .git or root .env."""

    for candidate in (start, *start.parents):
        if (
            (candidate / ".git").exists()
            or (candidate / ".env").is_file()
        ):
            return candidate

    parents = list(start.parents)

    return parents[3] if len(parents) > 3 else start


REPO_ROOT = find_repo_root(SCRIPT_DIR)

ENV_FILE = REPO_ROOT / ".env"
SAMPLES_DIR = SCRIPT_DIR / "samples"

BASE_URL = "https://webapi.bps.go.id/v1/api"

DEFAULT_DOMAIN = "0000"
TIMEOUT = 30

SEARCH_TERMS = [
    "produk domestik bruto",
    "pdb",
    "lapangan usaha",
    "informasi dan komunikasi",
    "pdrb",
]

PAGINATION_KEYS = {
    "page",
    "pages",
    "per_page",
    "count",
    "total",
}


# ============================================================
# 2. GENERAL HELPERS
# ============================================================

def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_name(value: Any) -> str:
    return (
        re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            str(value)
        ).strip("_")
        or "unknown"
    )


def api_key() -> str:
    """Load BPS API Key from repository-root .env."""

    load_dotenv(ENV_FILE)

    key = os.getenv("BPS_API_KEY", "").strip()

    if not key:
        raise RuntimeError(
            f"BPS_API_KEY belum ditemukan. "
            f"Periksa file: {ENV_FILE}"
        )

    return key


# ============================================================
# 3. SAVE OUTPUT
# ============================================================

def save_json(
    payload: Any,
    filename: str
) -> Path:

    SAMPLES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    path = SAMPLES_DIR / filename

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return path


def save_csv(
    rows: list[dict[str, Any]],
    filename: str
) -> Path:

    SAMPLES_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    path = SAMPLES_DIR / filename

    if not rows:
        path.write_text(
            "",
            encoding="utf-8-sig"
        )
        return path

    columns = list(
        dict.fromkeys(
            key
            for row in rows
            for key in row
        )
    )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=columns
        )

        writer.writeheader()
        writer.writerows(rows)

    return path


# ============================================================
# 4. HTTP REQUEST
# ============================================================

def request_json(
    endpoint: str,
    params: dict[str, Any] | None = None
) -> Any:

    url = (
        f"{BASE_URL}/"
        f"{endpoint}/"
        f"key/{quote(api_key(), safe='')}"
    )

    query = {
        "lang": "ind"
    }

    if params:
        query.update(params)

    print("\n" + "=" * 68)
    print("[REQUEST] BPS WebAPI")
    print("=" * 68)

    print("Endpoint :", endpoint)
    print("Method   : GET")
    print("Query    :", query)

    try:

        response = requests.get(
            url,
            params=query,
            headers={
                "Accept": "application/json"
            },
            timeout=TIMEOUT
        )

    except requests.Timeout:

        raise RuntimeError(
            "Request timeout. Periksa koneksi internet."
        ) from None

    except requests.RequestException as exc:

        raise RuntimeError(
            f"Koneksi BPS gagal ({type(exc).__name__})."
        ) from None

    print("HTTP     :", response.status_code)

    print(
        "Content-Type:",
        response.headers.get(
            "Content-Type",
            "unknown"
        )
    )

    try:

        payload = response.json()

    except ValueError:

        raise RuntimeError(
            f"Respons bukan JSON. "
            f"HTTP {response.status_code}: "
            f"{response.text[:300]}"
        ) from None

    if not response.ok:

        raise RuntimeError(
            f"HTTP {response.status_code}: "
            f"{json.dumps(payload, ensure_ascii=False)[:1000]}"
        )

    if (
        isinstance(payload, dict)
        and str(payload.get("status", "")).lower() == "error"
    ):

        raise RuntimeError(
            f"Status API Error: "
            f"{payload.get('message', 'tanpa pesan')}"
        )

    return payload


# ============================================================
# 5. RESPONSE HELPERS
# ============================================================

def find_pagination(
    obj: Any
) -> dict[str, Any] | None:

    if isinstance(obj, dict):

        if PAGINATION_KEYS.issubset(obj):
            return obj

        for value in obj.values():

            found = find_pagination(value)

            if found:
                return found

    elif isinstance(obj, list):

        for value in obj:

            found = find_pagination(value)

            if found:
                return found

    return None


def find_records(
    obj: Any,
    marker: str
) -> list[dict[str, Any]]:

    records = []

    def walk(value: Any):

        if isinstance(value, dict):

            if (
                marker in value
                and not PAGINATION_KEYS.issuperset(value.keys())
            ):
                records.append(value)

            for child in value.values():

                if isinstance(child, (dict, list)):
                    walk(child)

        elif isinstance(value, list):

            for child in value:
                walk(child)

    walk(obj)

    unique = []
    seen = set()

    for row in records:

        fingerprint = json.dumps(
            row,
            sort_keys=True,
            ensure_ascii=False,
            default=str
        )

        if fingerprint not in seen:

            seen.add(fingerprint)
            unique.append(row)

    return unique


def summary(payload: Any) -> None:

    print("\n[RESPONSE SUMMARY]")

    if isinstance(payload, dict):

        print(
            "Top-level keys:",
            list(payload.keys())
        )

        for key in (
            "status",
            "data-availability",
            "last_update",
            "message"
        ):

            if key in payload:
                print(f"{key}: {payload[key]}")

    pagination = find_pagination(payload)

    if pagination:

        print(
            "Pagination:",
            {
                key: pagination.get(key)
                for key in (
                    "page",
                    "pages",
                    "per_page",
                    "count",
                    "total"
                )
            }
        )


# ============================================================
# 6. STRATEGIC INDICATORS
# ============================================================

def get_indicators(domain: str) -> None:

    endpoint = (
        f"list/model/indicators/"
        f"domain/{quote(domain, safe='')}"
    )

    payload = request_json(
        endpoint,
        {"page": 1}
    )

    raw = save_json(
        payload,
        f"{stamp()}_strategic_indicators.json"
    )

    summary(payload)

    print("\n[INDICATOR DATA]")

    print(
        json.dumps(
            payload.get("data", payload),
            ensure_ascii=False,
            indent=2
        )[:5000]
    )

    print("\n[SUCCESS] Strategic Indicators tersimpan.")
    print("[SAVED]", raw)


# ============================================================
# 7. DYNAMIC VARIABLES
# ============================================================

def get_variables(
    domain: str,
    page: int,
    terms: list[str]
) -> None:

    endpoint = (
        f"list/model/var/"
        f"domain/{quote(domain, safe='')}"
    )

    payload = request_json(
        endpoint,
        {"page": page}
    )

    raw = save_json(
        payload,
        f"{stamp()}_dynamic_variables_page_{page}.json"
    )

    summary(payload)

    records = find_records(
        payload,
        "var_id"
    )

    print("\n[DYNAMIC VARIABLE CATALOG]")
    print("Record variabel:", len(records))

    hits = []

    for item in records:

        searchable = json.dumps(
            item,
            ensure_ascii=False
        ).lower()

        matched = [
            term
            for term in terms
            if term.lower() in searchable
        ]

        if matched:
            hits.append((item, matched))

    print("\n[KANDIDAT PDB / SEKTOR]")
    print("-" * 68)

    if not hits:

        print(
            "Tidak ada kandidat pada halaman ini."
        )

        print(
            "Periksa JSON atau lanjutkan ke halaman berikutnya."
        )

    for item, matched in hits:

        print(
            "Variable ID :",
            item.get("var_id")
        )

        print(
            "Nama        :",
            item.get(
                "title",
                item.get("name", item.get("label", "-"))
            )
        )

        print(
            "Keyword     :",
            ", ".join(matched)
        )

        print("-" * 68)

    print("[SAVED]", raw)

    print(
        "Keyword hanya untuk discovery. "
        "Validasi judul, definisi, satuan, dan cakupan "
        "sebelum memilih variabel."
    )


# ============================================================
# 8. DYNAMIC PERIODS
# ============================================================

def get_periods(
    domain: str,
    var_id: str,
    page: int
) -> None:

    endpoint = (
        f"list/model/th/"
        f"domain/{quote(domain, safe='')}"
    )

    payload = request_json(
        endpoint,
        {
            "var": var_id,
            "page": page
        }
    )

    raw = save_json(
        payload,
        (
            f"{stamp()}_periods_"
            f"var_{safe_name(var_id)}_"
            f"page_{page}.json"
        )
    )

    summary(payload)

    records = find_records(
        payload,
        "th_id"
    )

    print("\n[DYNAMIC PERIODS]")
    print("-" * 68)

    for row in records:

        print(
            f"Period ID : {row.get('th_id')} "
            f"| Periode: {row.get('th', row.get('title', '-'))}"
        )

    if not records:

        print(
            "Tidak ada record th_id terdeteksi. "
            "Periksa JSON mentah."
        )

    print("[SAVED]", raw)


# ============================================================
# 9. DECODE DYNAMIC DATA
# ============================================================

def dimension_items(
    payload: dict[str, Any],
    field: str
) -> list[dict[str, Any]]:

    value = payload.get(field)

    if isinstance(value, list) and value:

        valid = [
            item
            for item in value
            if isinstance(item, dict)
        ]

        if valid:
            return valid

    return [
        {
            "val": "0",
            "label": "Tidak ada"
        }
    ]


def dim_val(
    item: dict[str, Any]
) -> str:

    return str(
        item.get("val", "0")
    )


def decode_datacontent(
    payload: dict[str, Any],
    domain: str
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Decode BPS composite datacontent keys.

    Pattern observed and verified against the supplied
    Variable 402 / Year 2023 response:

    vervar + var + turvar + tahun + turtahun

    Each key is matched against dimension metadata
    returned in the same response.

    Unknown or ambiguous keys are retained and flagged.
    """

    content = payload.get("datacontent")

    if not isinstance(content, dict):

        raise RuntimeError(
            "Respons tidak memiliki datacontent "
            "berbentuk dictionary."
        )

    dimensions = {

        "vervar": dimension_items(
            payload,
            "vervar"
        ),

        "var": dimension_items(
            payload,
            "var"
        ),

        "turvar": dimension_items(
            payload,
            "turvar"
        ),

        "tahun": dimension_items(
            payload,
            "tahun"
        ),

        "turtahun": dimension_items(
            payload,
            "turtahun"
        ),
    }

    lookup: dict[
        str,
        list[dict[str, Any]]
    ] = {}

    combinations = itertools.product(
        dimensions["vervar"],
        dimensions["var"],
        dimensions["turvar"],
        dimensions["tahun"],
        dimensions["turtahun"]
    )

    for vv, var, tv, year, subyear in combinations:

        key = "".join(
            map(
                dim_val,
                (
                    vv,
                    var,
                    tv,
                    year,
                    subyear
                )
            )
        )

        lookup.setdefault(
            key,
            []
        ).append({

            "vervar_id": dim_val(vv),
            "vervar_label": vv.get("label", ""),

            "variable_id": dim_val(var),
            "variable_label": var.get("label", ""),

            "turvar_id": dim_val(tv),
            "turvar_label": tv.get("label", ""),

            "period_id": dim_val(year),
            "period_label": year.get("label", ""),

            "subperiod_id": dim_val(subyear),
            "subperiod_label": subyear.get("label", ""),
        })

    subject = payload.get("subject") or []

    subject_label = "; ".join(
        str(item.get("label", ""))
        for item in subject
        if isinstance(item, dict)
    )

    var_meta = dimensions["var"][0]

    rows = []
    warnings = []

    for raw_key, value in content.items():

        candidates = lookup.get(
            str(raw_key),
            []
        )

        if len(candidates) == 1:

            mapped = candidates[0]
            status = "decoded"

        elif len(candidates) > 1:

            mapped = candidates[0]
            status = "ambiguous_key"

            warnings.append(
                f"Key {raw_key}: lebih dari satu kombinasi dimensi."
            )

        else:

            mapped = {

                "vervar_id": "",
                "vervar_label": "",

                "variable_id": "",
                "variable_label": "",

                "turvar_id": "",
                "turvar_label": "",

                "period_id": "",
                "period_label": "",

                "subperiod_id": "",
                "subperiod_label": "",
            }

            status = "unmatched"

            warnings.append(
                f"Key {raw_key}: tidak cocok dengan metadata."
            )

        rows.append({

            "source": "BPS WebAPI",
            "domain": domain,
            "subject": subject_label,

            **mapped,

            "value": value,
            "unit": var_meta.get("unit") or "",
            "last_update": payload.get("last_update", ""),

            "datacontent_key": str(raw_key),
            "decode_status": status,
        })

    return rows, warnings


# ============================================================
# 10. GET DYNAMIC DATA + EXPORT CSV
# ============================================================

def get_data(
    domain: str,
    var_id: str,
    period_id: str
) -> None:

    endpoint = (
        f"list/model/data/"
        f"domain/{quote(domain, safe='')}/"
        f"var/{quote(var_id, safe='')}/"
        f"th/{quote(period_id, safe='')}"
    )

    payload = request_json(endpoint)

    ts = stamp()

    json_path = save_json(
        payload,
        (
            f"{ts}_data_var_{safe_name(var_id)}_"
            f"period_{safe_name(period_id)}.json"
        )
    )

    summary(payload)

    rows, warnings = decode_datacontent(
        payload,
        domain
    )

    csv_path = save_csv(
        rows,
        (
            f"{ts}_data_var_{safe_name(var_id)}_"
            f"period_{safe_name(period_id)}_decoded.csv"
        )
    )

    print("\n[DECODED OBSERVATIONS]")
    print("-" * 100)

    for row in rows:

        print(
            f"{row['period_label']} | "
            f"{row['vervar_label']} | "
            f"{row['value']} {row['unit']} | "
            f"{row['decode_status']}"
        )

    decoded_count = sum(
        row["decode_status"] == "decoded"
        for row in rows
    )

    print("\nJumlah observasi datacontent:", len(rows))
    print("Berhasil decoded            :", decoded_count)

    if warnings:

        print("\n[DECODE WARNINGS]")

        for warning in warnings:
            print("-", warning)

    print("\n[SUCCESS] Dynamic Data berhasil diproses.")

    print("[RAW JSON]", json_path)
    print("[DECODED CSV]", csv_path)

    print(
        "Periksa decode_status dan metadata "
        "sebelum menggunakan CSV untuk analisis."
    )


# ============================================================
# 11. MAIN PROGRAM
# ============================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "BPS WebAPI Explorer — "
            "Sector Growth Insight Personel 1"
        )
    )

    parser.add_argument(
        "--task",
        choices=[
            "overview",
            "indicators",
            "variables",
            "periods",
            "data"
        ],
        default="overview"
    )

    parser.add_argument(
        "--domain",
        default=DEFAULT_DOMAIN
    )

    parser.add_argument(
        "--var-id",
        help="Variable ID dari katalog BPS."
    )

    parser.add_argument(
        "--period-id",
        help="Period ID (th_id) dari List periods."
    )

    parser.add_argument(
        "--page",
        type=int,
        default=1
    )

    parser.add_argument(
        "--search",
        default=",".join(SEARCH_TERMS),
        help="Keyword pencarian, dipisahkan koma."
    )

    args = parser.parse_args()

    if args.page < 1:

        parser.error(
            "--page minimal 1."
        )

    if (
        args.task in {"periods", "data"}
        and not args.var_id
    ):

        parser.error(
            f"--task {args.task} membutuhkan --var-id."
        )

    if (
        args.task == "data"
        and not args.period_id
    ):

        parser.error(
            "--task data membutuhkan --period-id."
        )

    placeholders = {
        "id_variabel",
        "id_periode",
        "variable_id",
        "period_id"
    }

    for value in (
        args.var_id,
        args.period_id
    ):

        if (
            value
            and value.strip().lower() in placeholders
        ):

            parser.error(
                "Ganti placeholder dengan ID aktual dari BPS."
            )

    terms = [
        term.strip()
        for term in args.search.split(",")
        if term.strip()
    ]

    try:

        if args.task == "overview":

            print("\n" + "=" * 68)
            print("BPS WEBAPI EXPLORER — PERSONEL 1")
            print("Sector Growth Insight Foundation")
            print("=" * 68)

            get_indicators(args.domain)

            get_variables(
                args.domain,
                args.page,
                terms
            )

        elif args.task == "indicators":

            get_indicators(args.domain)

        elif args.task == "variables":

            get_variables(
                args.domain,
                args.page,
                terms
            )

        elif args.task == "periods":

            get_periods(
                args.domain,
                args.var_id,
                args.page
            )

        elif args.task == "data":

            get_data(
                args.domain,
                args.var_id,
                args.period_id
            )

    except RuntimeError as exc:

        print("\n[ERROR]", exc)
        sys.exit(1)

    except KeyboardInterrupt:

        print("\n[STOP] Proses dihentikan pengguna.")
        sys.exit(130)


if __name__ == "__main__":
    main()
 