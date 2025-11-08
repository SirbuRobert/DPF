# inspect_and_save_openstax_paragraphs.py
from datasets import load_dataset, Dataset
from pprint import pprint

raw = load_dataset("HuggingFaceTB/openstax_paragraphs", split="train")

# --- A) Visualize structure of the first book ---
b0 = raw[0]
print("Book title:", b0.get("book_title"))
print("Language:", b0.get("language"))

def print_tree(chapter, indent=0, max_sections=3):
    print("  " * indent + f"- {chapter.get('title')!r}")
    secs = chapter.get("sections") or []
    for s in secs[:max_sections]:
        t = (s.get("title") or "")[:60]
        print("  " * (indent+1) + f"• section: {t!r}")
    if len(secs) > max_sections:
        print("  " * (indent+1) + f"• ... ({len(secs)-max_sections} more sections)")
    for child in (chapter.get("chapters") or []):
        print_tree(child, indent+1, max_sections)

print("\nOutline preview (first book):")
for ch in (b0.get("chapters") or [])[:5]:
    print_tree(ch, indent=0)

# --- B) Build chapter → summary pairs ---
SUMMARY_KEYS = ["summary","chapter summary","section summary","overview","chapter review","key concepts","key terms"]

def extract_pairs(book_row):
    pairs = []
    def walk(ch):
        secs = ch.get("sections") or []
        # full chapter text
        chapter_text = "\n\n".join(s["paragraph"] for s in secs if s.get("paragraph"))
        # summary from special sections
        summary_text = "\n".join(
            s["paragraph"] for s in secs
            if s.get("title") and any(k in s["title"].lower() for k in SUMMARY_KEYS) and s.get("paragraph")
        )
        if chapter_text and summary_text:
            pairs.append({
                "book_title": book_row.get("book_title"),
                "chapter_title": ch.get("title"),
                "document": chapter_text,
                "summary": summary_text,
            })
        for c in (ch.get("chapters") or []):
            walk(c)
    for c in (book_row.get("chapters") or []):
        walk(c)
    return pairs

all_pairs = []
for row in raw:
    all_pairs.extend(extract_pairs(row))

print(f"\nBuilt {len(all_pairs)} (document → summary) pairs.")
pprint(all_pairs[0] if all_pairs else {})

# --- C) Save to Parquet/CSV for training ---
pairs_ds = Dataset.from_list(all_pairs)
pairs_ds.to_parquet("data/openstax_chapter_summaries.parquet")
pairs_ds.to_csv("data/openstax_chapter_summaries.csv")
print("Saved to data/openstax_chapter_summaries.parquet and .csv")
