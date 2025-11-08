from datasets import load_dataset
import re, unicodedata
from pprint import pprint

# ===================== CONFIG =====================
SAVE_PARQUET = "data/openstax_text.formatted.parquet"  # set to None to skip
SAVE_CSV     = None                                     # e.g., "data/openstax_text.formatted.csv"
NUM_PROC     = 8                                        # parallel workers for map()
MIN_CHARS    = 50                                       # drop very short lines
ALPHA_RATIO  = 0.4                                      # drop lines with too few letters
ORDER        = "shuffle"                                # "shuffle", "length_asc", "length_desc", or None
PREVIEW_ROWS = 3                                        # how many rows to print after formatting
# ===================================================

def normalize_text(t: str) -> str:
    # Unicode normalize, collapse whitespace, strip
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def alpha_ratio(t: str) -> float:
    if not t: return 0.0
    letters = sum(ch.isalpha() for ch in t)
    return letters / max(1, len(t))

def format_batch(batch):
    texts = batch["text"]
    norm = [normalize_text(t) for t in texts]
    # lengths
    char_len = [len(t) for t in norm]
    word_len = [len(t.split()) for t in norm]
    return {
        "text": norm,
        "char_len": char_len,
        "word_len": word_len,
    }

def filter_row(example):
    t = example["text"]
    if t is None or t == "":
        return False
    if len(t) < MIN_CHARS:
        return False
    if alpha_ratio(t) < ALPHA_RATIO:
        return False
    return True

def main():
    # 1) Load full train split (non-streaming)
    ds = load_dataset("crumb/openstax-text", split="train")
    print(ds)  # shows num_rows & features: ['text']

    # 2) Clean/format + add length features
    ds = ds.map(format_batch, batched=True, num_proc=NUM_PROC)

    # 3) Filter junk/short lines
    ds = ds.filter(filter_row, num_proc=NUM_PROC)

    # 4) Order
    if ORDER == "shuffle":
        ds = ds.shuffle(seed=42)
    elif ORDER == "length_asc":
        ds = ds.sort("char_len")     # shortest → longest
    elif ORDER == "length_desc":
        ds = ds.sort("char_len", reverse=True)  # longest → shortest
    # else: keep original order

    # 5) Preview a few rows
    print("\nSchema / features:")
    pprint(ds.features)
    print(f"\nRows after formatting/filtering: {len(ds)}")
    print("\nSample rows:")
    for r in ds.select(range(min(PREVIEW_ROWS, len(ds)))):
        show = {k: (r[k][:200] + "…") if k == "text" and len(r[k]) > 200 else r[k] for k in r}
        pprint(show)

    # 6) Save
    if SAVE_PARQUET:
        ds.to_parquet(SAVE_PARQUET)  # requires pyarrow
        print(f"\nSaved → {SAVE_PARQUET}")
    if SAVE_CSV:
        ds.to_csv(SAVE_CSV)
        print(f"Saved → {SAVE_CSV}")

if __name__ == "__main__":
    main()