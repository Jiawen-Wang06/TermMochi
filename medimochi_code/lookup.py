import click
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAIError
from config import LOOKUP_WORKERS


def build_prompt(term: str, field: str) -> str:
    return (
        f'Search the web and define "{term}" in one or two sentences, as the term is used in this field: "{field}". '
        "Prefer authoritative sources such as official bodies, regulators, standards organizations and "
        "established reference works for that field. "
        "Answer with the definition only. Do not include links or citations in the text."
    )


def lookup_term(client, term: str, field: str):
    in_total = 0
    out_total = 0
    searches_total = 0
    definition = ""
    source = ""
    for _ in range(2):
        definition, source, in_tokens, out_tokens, searches = client.define(build_prompt(term, field))
        in_total += in_tokens
        out_total += out_tokens
        searches_total += searches
        if definition and source:
            break
    if not definition:
        raise ValueError("the search returned no answer")
    entry = {"term": term, "definition": definition, "source": source}
    return entry, in_total, out_total, searches_total


def safe_lookup(client, term: str, field: str):
    try:
        return lookup_term(client, term, field), None
    except (OpenAIError, ValueError) as e:
        return None, str(e)


def define_terms(client, terms: list[str], field: str):
    results = []
    failed = []
    in_total = 0
    out_total = 0
    searches_total = 0

    def handle(position: int, term: str, outcome) -> None:
        nonlocal in_total, out_total, searches_total
        found, error = outcome
        if found is None:
            failed.append((term, error))
            click.echo(f"  [{position}/{len(terms)}] {term}: failed ({error})", err=True)
            return
        entry, in_tokens, out_tokens, searches = found
        results.append(entry)
        in_total += in_tokens
        out_total += out_tokens
        searches_total += searches
        marker = "" if entry["source"] else " (no web source found)"
        click.echo(f"  [{position}/{len(terms)}] {term}{marker}")

    first = (lookup_term(client, terms[0], field), None)
    handle(1, terms[0], first)

    with ThreadPoolExecutor(max_workers=LOOKUP_WORKERS) as pool:
        rest = terms[1:]
        outcomes = pool.map(lambda term: safe_lookup(client, term, field), rest)
        for position, (term, outcome) in enumerate(zip(rest, outcomes), start=2):
            handle(position, term, outcome)

    return results, failed, in_total, out_total, searches_total
