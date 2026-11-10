import base64
import math
from pathlib import Path

import pymupdf

from utils import count_tokens

CHUNK_TOKENS = 6000
IMAGE_BATCH_PAGES = 2
RENDER_ZOOM = 2.0
MIN_TEXT_CHARS = 30


def open_pdf(path: Path) -> pymupdf.Document:
    return pymupdf.open(str(path))


def classify_pages(doc: pymupdf.Document) -> tuple[list[tuple[int, str]], list[int]]:
    text_pages = []
    image_pages = []
    for index, page in enumerate(doc):
        number = index + 1
        text = page.get_text().strip()
        if len(text) >= MIN_TEXT_CHARS:
            text_pages.append((number, text))
        else:
            image_pages.append(number)
    return text_pages, image_pages


def chunk_text_pages(text_pages: list[tuple[int, str]], model: str, limit: int = CHUNK_TOKENS) -> list[list[tuple[int, str]]]:
    chunks = []
    current = []
    current_tokens = 0
    for number, text in text_pages:
        tokens = count_tokens(text, model)
        if current and current_tokens + tokens > limit:
            chunks.append(current)
            current = []
            current_tokens = 0
        current.append((number, text))
        current_tokens += tokens
    if current:
        chunks.append(current)
    return chunks


def batch_pages(numbers: list[int], size: int = IMAGE_BATCH_PAGES) -> list[list[int]]:
    return [numbers[i:i + size] for i in range(0, len(numbers), size)]


def image_tokens_for_page(doc: pymupdf.Document, number: int, base: int, tile: int) -> int:
    rect = doc[number - 1].rect
    width = rect.width * RENDER_ZOOM
    height = rect.height * RENDER_ZOOM
    scale = min(1.0, 2048 / max(width, height))
    width *= scale
    height *= scale
    scale = min(1.0, 768 / min(width, height))
    width *= scale
    height *= scale
    tiles = math.ceil(width / 512) * math.ceil(height / 512)
    return base + tile * tiles


def render_page(doc: pymupdf.Document, number: int) -> str:
    pixmap = doc[number - 1].get_pixmap(matrix=pymupdf.Matrix(RENDER_ZOOM, RENDER_ZOOM))
    return base64.b64encode(pixmap.tobytes("png")).decode("ascii")
