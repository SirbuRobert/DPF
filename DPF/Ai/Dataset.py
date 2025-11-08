# pip install -U datasets transformers accelerate
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, DataCollatorForSeq2Seq, Trainer, TrainingArguments

raw = load_dataset("HuggingFaceTB/openstax_paragraphs", split="train")

KEYS = ["summary","chapter summary","section summary","overview","chapter review","key concepts","key terms"]
def make_pairs(row):
    pairs = []
    def walk(ch):
        secs = ch.get("sections") or []
        txt = "\n\n".join(s["paragraph"] for s in secs if s.get("paragraph"))
        summ = "\n".join(
            s["paragraph"] for s in secs
            if s.get("title") and any(k in s["title"].lower() for k in KEYS) and s.get("paragraph")
        )
        if txt and summ:
            pairs.append({"document": txt, "summary": summ})
        for c in ch.get("chapters") or []:
            walk(c)
    for c in (row.get("chapters") or []):
        walk(c)
    return {"pairs": pairs}

pairs = []
for r in raw:
    pairs += make_pairs(r)["pairs"]

from datasets import Dataset
ds = Dataset.from_list(pairs).train_test_split(test_size=0.02, seed=42)

model_name = "facebook/bart-base"
tok = AutoTokenizer.from_pretrained(model_name)
def preprocess(batch):
    model_in = tok(batch["document"], max_length=1024, truncation=True)
    with tok.as_target_tokenizer():
        labels = tok(batch["summary"], max_length=256, truncation=True)
    model_in["labels"] = labels["input_ids"]
    return model_in

train = ds["train"].map(preprocess, batched=True, remove_columns=ds["train"].column_names)
val   = ds["test"].map(preprocess, batched=True, remove_columns=ds["test"].column_names)

model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
coll = DataCollatorForSeq2Seq(tok, model=model)

args = TrainingArguments(
    output_dir="openstax-sum-bart",
    learning_rate=2e-5,
    num_train_epochs=2,
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    gradient_accumulation_steps=8,
    save_steps=1000,
    logging_steps=200,
    fp16=True
)
trainer = Trainer(model=model, args=args, train_dataset=train, eval_dataset=val,
                  data_collator=coll, tokenizer=tok)
trainer.train()
