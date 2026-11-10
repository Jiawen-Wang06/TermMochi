import click
import json
import os
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import BadRequestError
from llm_client import LLMClient
from lookup import define_terms
from relevance import filter_terms
from config import MODELS, DEFAULT_MODEL, DEFAULT_FIELD, TEMPERATURE, MAX_TOKENS, WEB_SEARCH_COST_PER_CALL
from utils import calculate_cost, format_cost
from export import parse_terms, save_terms_csv, dedupe_terms, check_terms_csv_writable
from pdf_reader import open_pdf, classify_pages, chunk_text_pages, batch_pages, render_page

load_dotenv()

SEPARATOR = "─" * 50


def save_results(results, field, document):
    try:
        return save_terms_csv(results, field, document), "terms.csv"
    except OSError:
        backup = f"terms_{datetime.now():%Y%m%d_%H%M%S}.csv"
        click.echo(
            f"Could not write terms.csv (is it open in another program?). Saving to {backup} instead.", err=True
        )
        return save_terms_csv(results, field, document, path=backup), backup


def build_instruction(field: str) -> str:
    return (
        f'List the terms in this document that are related to the following field or topic: "{field}". '
        "Be thorough: include the terms specific to that field, terms commonly used in it, and the standards, "
        "regulations, laws, guidance documents and procedures that apply to it (use a standard's identifier as "
        "its term, for example ISO 9001). When a term could reasonably belong to this field, include it rather "
        "than miss it. Leave out only terms that clearly belong to an unrelated field. If nothing in the "
        "document relates to this field, return an empty list. Only use terms that appear in the document. "
        "Return only the term names, written as they appear in the document, without definitions."
    )


def page_label(pages: list[int]) -> str:
    if len(pages) == 1:
        return f"page {pages[0]}"
    return f"pages {pages[0]}-{pages[-1]}"


def build_text_prompt(instruction: str, file_name: str, chunk: list[tuple[int, str]]) -> str:
    body = "\n\n".join(f"[Page {number}]\n{text}" for number, text in chunk)
    return f'{instruction}\n\nThe document "{file_name}" follows.\n\n{body}'


def build_image_prompt(instruction: str, file_name: str, pages: list[int]) -> str:
    numbers = ", ".join(str(number) for number in pages)
    return f'{instruction}\n\nThe attached images are page(s) {numbers} of the document "{file_name}", in order.'


def request_terms(client, prompt, images, label):
    text, in_tokens, out_tokens = client.complete(prompt, TEMPERATURE, MAX_TOKENS, images=images)
    try:
        terms = parse_terms(text)
    except (ValueError, KeyError, TypeError) as e:
        click.echo(f"  {label}: could not parse model output ({e}); this part was skipped.", err=True)
        return [], in_tokens, out_tokens
    click.echo(f"  {label}: {len(terms)} term(s)")
    return terms, in_tokens, out_tokens


def run_document(client, file_path, model, instruction):
    doc = open_pdf(file_path)
    text_pages, image_pages = classify_pages(doc)
    if text_pages:
        text_chunks = chunk_text_pages(text_pages, model)
        image_batches = []
        summary = f"reading the text of {len(text_pages)} page(s)"
        if image_pages:
            summary += f", skipping {len(image_pages)} page(s) with no text (figures or scans)"
    else:
        text_chunks = []
        image_batches = batch_pages(image_pages)
        summary = f"no text found, reading {len(image_pages)} page(s) as images"
    total = len(text_chunks) + len(image_batches)
    if total == 0:
        raise click.ClickException(f"{file_path} has no pages.")

    click.echo(f"{file_path.name}: {doc.page_count} page(s); {summary}; {total} request(s) to find terms")

    all_terms = []
    in_total = 0
    out_total = 0

    for chunk in text_chunks:
        pages = [number for number, _ in chunk]
        prompt = build_text_prompt(instruction, file_path.name, chunk)
        terms, in_tokens, out_tokens = request_terms(client, prompt, None, page_label(pages))
        all_terms += terms
        in_total += in_tokens
        out_total += out_tokens

    for pages in image_batches:
        images = [render_page(doc, number) for number in pages]
        prompt = build_image_prompt(instruction, file_path.name, pages)
        terms, in_tokens, out_tokens = request_terms(client, prompt, images, page_label(pages) + " (image)")
        all_terms += terms
        in_total += in_tokens
        out_total += out_tokens

    return dedupe_terms(all_terms), in_total, out_total


@click.command()
@click.argument("field", default=DEFAULT_FIELD)
@click.option("--file", "file_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="PDF to extract terms from")
@click.option("--model", default=DEFAULT_MODEL, type=click.Choice(list(MODELS.keys())), help="Model to use")
def main(field, file_path, model):
    """Find terms about FIELD in a PDF (default: software in the medical field), look up their meanings
    on the web, and save them to terms.csv."""
    try:
        check_terms_csv_writable()
    except ValueError as e:
        raise click.ClickException(str(e))

    if not os.environ.get("OPENAI_API_KEY"):
        raise click.ClickException(
            "OPENAI_API_KEY is not set. Add it to a .env file in the MediMochi folder "
            "(OPENAI_API_KEY=your-key) or set it as an environment variable. See the README."
        )

    config = MODELS[model]
    client = LLMClient(model)
    click.echo(f"Using model: {model}")
    click.echo(f"Field: {field}\n")

    start = time.perf_counter()
    extracted, in_tokens, out_tokens = run_document(client, file_path, model, build_instruction(field))

    results = []
    failed = []
    searches = 0
    names = []
    if extracted:
        names = [item["term"].strip() for item in extracted]
        click.echo(f'\nChecking which of {len(names)} term(s) belong to "{field}"...')
        names, check_in, check_out = filter_terms(client, names, field)
        in_tokens += check_in
        out_tokens += check_out
        click.echo(f"  {len(names)} of {len(extracted)} term(s) kept")
        kept_lower = {name.lower() for name in names}
        removed = [item["term"].strip() for item in extracted if item["term"].strip().lower() not in kept_lower]
        if removed:
            click.echo(f"  Removed as unrelated: {', '.join(removed)}")
    if names:
        click.echo(f"\nLooking up {len(names)} term(s) on the web...")
        try:
            results, failed, look_in, look_out, searches = define_terms(client, names, field)
        except BadRequestError as e:
            raise click.ClickException(
                f"The web search lookup was rejected for {model}: {e.message}. "
                "Check that this model supports the web search tool."
            )
        in_tokens += look_in
        out_tokens += look_out

    latency = time.perf_counter() - start

    click.echo()
    if results:
        click.echo(json.dumps({"terms": results}, indent=2, ensure_ascii=False))
        saved, filename = save_results(results, field, file_path.name)
        note = " (replacing any previous file)" if filename == "terms.csv" else ""
        click.echo(f"\nSaved {saved} term(s) to {filename}{note}")
    else:
        if failed:
            click.echo("No terms were saved; terms.csv was left unchanged.")
        else:
            click.echo(f'No terms related to "{field}" were found in this document; terms.csv was left unchanged.')

    unsourced = [item["term"] for item in results if not item["source"]]
    if unsourced:
        click.echo(f"No web source was found for: {', '.join(unsourced)}", err=True)
    if failed:
        click.echo(f"Lookup failed, not saved: {', '.join(term for term, _ in failed)}", err=True)

    token_cost = calculate_cost(in_tokens, out_tokens, config["cost"]["input"], config["cost"]["output"])
    search_cost = searches * WEB_SEARCH_COST_PER_CALL
    click.echo(f"\n{SEPARATOR}")
    click.echo(f"Latency:       {latency:.2f}s")
    click.echo(f"Input tokens:  {in_tokens}")
    click.echo(f"Output tokens: {out_tokens}")
    click.echo(f"Web searches:  {searches} ({format_cost(search_cost)})")
    click.echo(f"Cost:          {format_cost(token_cost + search_cost)} (tokens {format_cost(token_cost)} + searches)")
    click.echo(f"Total tokens:  {in_tokens + out_tokens}")


if __name__ == "__main__":
    main()
