"""03 · Tokens made visible — what you actually pay for.

Runs the real tokenizer, so the counts are exact rather than estimated. Watch what
happens to Romanian versus English, and to rare terminology versus common words.

    uv run python examples/03_tokens.py
"""
from __future__ import annotations

from _bootstrap import banner

banner("03 · tokens are the unit of everything")

SAMPLES = [
    "The card is blocked.",
    "Cardul este blocat.",
    "Retrieval-augmented generation",
    "Împrumut ipotecar cu dobândă variabilă",
    "A mortgage loan with a variable interest rate",
    "IBAN RO49AAAA1B31007593840000",
]

try:
    import tiktoken
    enc = tiktoken.get_encoding("o200k_base")   # the family behind recent GPT models
except Exception as e:
    print(f"tiktoken unavailable ({e}) — falling back to the chars/4 estimate.\n")
    enc = None


def count(text: str) -> tuple[int, list[str]]:
    if enc is None:
        return max(1, round(len(text) / 4)), []
    ids = enc.encode(text)
    return len(ids), [enc.decode([i]) for i in ids]


print(f"{'tokens':>6}  {'chars':>5}  text")
print("─" * 72)
for text in SAMPLES:
    n, pieces = count(text)
    print(f"{n:>6}  {len(text):>5}  {text}")
    if pieces:
        print(f"{'':>13} → {' | '.join(pieces)}")

print("\nWhy this matters:")
print("  · cost      — providers bill per token, input and output separately")
print("  · latency   — every OUTPUT token is a full pass through the model")
print("  · capacity  — the context window is measured in tokens, not characters")
print("\nNotice that Romanian needs more tokens than the equivalent English, and that an")
print("IBAN shatters into many pieces. For a Romanian bank, that is a real cost line.")
