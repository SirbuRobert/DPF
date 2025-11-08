import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

OUT_DIR = "./t5_small_summarizer"   # <- your saved folder
TASK_PREFIX = "summarize: "
MAX_SRC_LEN = 1024

device = torch.device(
    "mps" if torch.backends.mps.is_available()
    else "cuda" if torch.cuda.is_available()
    else "cpu"
)

tok = AutoTokenizer.from_pretrained(OUT_DIR)
model = AutoModelForSeq2SeqLM.from_pretrained(OUT_DIR).to(device)
model.eval()

def summarize(texts, max_new_tokens=1000, num_beams=16):
    if isinstance(texts, str):
        texts = [texts]
    enc = tok([TASK_PREFIX + t for t in texts],
              return_tensors="pt", padding=True, truncation=True,
              max_length=MAX_SRC_LEN).to(device)
    with torch.no_grad():
        out = model.generate(
            **enc,
            max_new_tokens=max_new_tokens,
            num_beams=num_beams,
            length_penalty=0.3,
        )
    return [tok.decode(o, skip_special_tokens=True) for o in out]

# Example
with open("./data/text.txt") as f:
    text = f.read()

def keep_complete_sentences(text: str) -> str:
    t = text.rstrip()
    idx = max(t.rfind("."), t.rfind("!"), t.rfind("?"))
    if idx == -1: return t
    i = idx + 1
    while i < len(t) and t[i] in '"\'”’)]}':
        i += 1
    return t[:i]

summarized = summarize(text, max_new_tokens=1000, num_beams=16)
print(keep_complete_sentences(summarized[0]))
