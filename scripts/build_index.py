"""One command: raw CSV -> cleaned CSV (with description column) -> Chroma + BM25.

    .venv/bin/python scripts/build_index.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag import clean, index  # noqa: E402

t0 = time.time()
df = clean.build()
stats = df.attrs["stats"]
clean.save(df)
print(f"cleaned: {stats}")
empty = (df.description.str.strip() == "").sum()
print(f"empty descriptions: {empty}")
print(f"product types: {df.product_type.nunique()}  ('Other': {(df.product_type == 'Other').sum()})")

info = index.build(clean.load_clean())
print(f"indexed: {info}  in {time.time() - t0:.1f}s")
