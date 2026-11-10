import click
from export import parse_terms
from config import MAX_TOKENS

BATCH_SIZE = 100


def build_prompt(field: str, names: list[str]) -> str:
    listing = "\n".join(f"- {name}" for name in names)
    return (
        f'Field or topic: "{field}"\n\n'
        "Below is a list of candidate terms taken from a document. Keep every term that is related to the "
        f'field "{field}", including terms commonly used in it and standards, regulations or procedures that '
        "apply to it. Remove only the terms that clearly belong to a different, unrelated field. "
        "If a term could reasonably belong to this field, keep it. When in doubt, keep it. "
        "Copy each kept term exactly as written below. Do not add terms.\n\n"
        f"{listing}"
    )


def filter_terms(client, names: list[str], field: str):
    kept = []
    in_total = 0
    out_total = 0
    for start in range(0, len(names), BATCH_SIZE):
        batch = names[start:start + BATCH_SIZE]
        returned = None
        for _ in range(2):
            text, in_tokens, out_tokens = client.complete(build_prompt(field, batch), 0.0, MAX_TOKENS)
            in_total += in_tokens
            out_total += out_tokens
            try:
                returned = {item["term"].strip().lower() for item in parse_terms(text)}
                break
            except (ValueError, KeyError, TypeError):
                continue
        if returned is None:
            raise click.ClickException(
                "Could not read the model's relevance check, so no web searches were run. Please try again."
            )
        kept += [name for name in batch if name.lower() in returned]
    return kept, in_total, out_total
