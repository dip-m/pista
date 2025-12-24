import argparse
import csv
import io
import os
import time
import zipfile
from typing import Iterable, List

from tqdm import tqdm

from bgg_client import fetch_thing, BGGError
from parser import parse_game_item
from backend.db import db_connection, ensure_schema, upsert_game, upsert_links


import logging
from logging.handlers import RotatingFileHandler

def init_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Log format
    fmt = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler (rotates at 5MB, keeps 5 files)
    fh = RotatingFileHandler("pista.log", maxBytes=5_000_000, backupCount=5)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger

ID_COLUMN_CANDIDATES = ["BGGId", "bgg_id", "id", "game_id"]


def _detect_id_column(fieldnames: List[str]) -> str:
    if not fieldnames:
        raise RuntimeError("CSV appears to have no header / field names.")
    for candidate in ID_COLUMN_CANDIDATES:
        if candidate in fieldnames:
            return candidate
    raise RuntimeError(
        f"Could not find an id column. Tried: {ID_COLUMN_CANDIDATES}. "
        f"Available columns: {fieldnames}"
    )


def _iter_ids_from_csv_file(file_obj: io.TextIOBase) -> Iterable[int]:
    reader = csv.DictReader(file_obj)
    id_col = _detect_id_column(reader.fieldnames or [])
    for row in reader:
        val = row.get(id_col)
        if not val:
            continue
        try:
            yield int(val)
        except ValueError:
            continue


def iter_bgg_ids_from_input(path: str) -> Iterable[int]:
    lower = path.lower()

    if lower.endswith(".zip"):
        with zipfile.ZipFile(path, "r") as z:
            csv_names = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                raise RuntimeError("ZIP file does not contain any .csv files.")

            def score_name(name: str) -> int:
                lname = name.lower()
                score = 0
                for kw in ["boardgames", "boardgame", "games", "ranks"]:
                    if kw in lname:
                        score += 1
                return score

            csv_names.sort(key=score_name, reverse=True)

            for csv_name in csv_names:
                with z.open(csv_name, "r") as f:
                    text_stream = io.TextIOWrapper(f, encoding="utf-8", newline="")
                    reader = csv.DictReader(text_stream)
                    try:
                        _ = _detect_id_column(reader.fieldnames or [])
                    except RuntimeError:
                        continue
                    zfp = z.open(csv_name, "r")
                    text_stream2 = io.TextIOWrapper(zfp, encoding="utf-8", newline="")
                    yield from _iter_ids_from_csv_file(text_stream2)
                    zfp.close()
                    return

            raise RuntimeError("No CSV in the ZIP had a usable id column.")
    else:
        with open(path, "r", encoding="utf-8", newline="") as f:
            yield from _iter_ids_from_csv_file(f)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ETL: build/update BGG semantic DB from ranks CSV using XML API2 /thing."
    )
    parser.add_argument("--input", required=True, help="Path to boardgames_ranks.csv or a ZIP containing it.")
    parser.add_argument("--db", required=True, help="Path to SQLite DB; created if missing.")
    parser.add_argument("--start", type=int, default=0, help="Start index in the list of BGG ids (0-based).")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of games to process from the start index.")
    parser.add_argument("--sleep-seconds", type=float, default=3.0, help="Seconds to sleep between API calls.")
    parser.add_argument("--override", type=int, default=0, help="If 1, re-fetch and update existing ids as well.")
    logger = init_logging()
    args = parser.parse_args()
    override = bool(args.override)

    all_ids: List[int] = list(iter_bgg_ids_from_input(args.input))
    if not all_ids:
        print("No BGG ids found in input.")
        return

    start = max(0, args.start)
    end = len(all_ids) if args.limit is None else min(len(all_ids), start + args.limit)
    ids_to_process = all_ids[start:end]

    print(f"Loaded {len(all_ids)} ids; processing {len(ids_to_process)} ids [{start}:{end}].")

    db_dir = os.path.dirname(os.path.abspath(args.db))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    with db_connection(args.db) as conn:
        ensure_schema(conn)

        for gid in tqdm(ids_to_process, desc="Processing games"):
            try:
                if not override:
                    cur = conn.execute("SELECT 1 FROM games WHERE id = ?", (gid,))
                    if cur.fetchone() is not None:
                        continue

                item = fetch_thing(gid, thing_type="boardgame", stats=True)
                parsed = parse_game_item(item)
                upsert_game(conn, parsed["game"])
                upsert_links(conn, parsed["game"]["id"], parsed["links"])
            except BGGError as e:
                logging.error(f"BGGError for id={gid}: {e}")
                logging.debug(f"BGGError debug for id={gid}", exc_info=True)                
            except Exception as e:
                logging.error(f"Unexpected error for id={gid}: {e}")
                logging.debug(f"Unexpected exception detail for id={gid}", exc_info=True)
            time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    main()
