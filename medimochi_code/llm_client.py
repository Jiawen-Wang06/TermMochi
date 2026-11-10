import os
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from openai import OpenAI, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

JSON_INSTRUCTION = (
    '\n\nReturn JSON in this exact format: {"terms": [{"term": "term1"}, {"term": "term2"}]}'
)

retry_on_rate_limit = retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)


def clean_url(url: str) -> str:
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if key != "utm_source"]
    return urlunsplit(parts._replace(query=urlencode(query)))


def strip_links(text: str) -> str:
    text = re.sub(r"\s*\(\s*\[[^\]]*\]\([^)]*\)\s*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return text.strip()


class LLMClient:
    def __init__(self, model: str):
        self.model = model
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    @retry_on_rate_limit
    def complete(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        images: list[str] | None = None,
    ) -> tuple[str, int, int]:
        text = prompt + JSON_INSTRUCTION
        content = text
        if images:
            content = [{"type": "text", "text": text}] + [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}", "detail": "high"}}
                for image in images
            ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )
        output = response.choices[0].message.content or ""
        return output, response.usage.prompt_tokens, response.usage.completion_tokens

    @retry_on_rate_limit
    def define(self, prompt: str) -> tuple[str, str, int, int, int]:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            tools=[{"type": "web_search"}],
            tool_choice="required",
            max_output_tokens=1000,
        )
        texts = []
        urls = []
        searches = 0
        for item in response.output:
            if item.type == "web_search_call":
                searches += 1
            elif item.type == "message":
                for part in item.content:
                    if part.type == "output_text":
                        texts.append(part.text)
                        for annotation in part.annotations or []:
                            if annotation.type == "url_citation":
                                urls.append(annotation.url)
        definition = strip_links(" ".join(texts))
        source = clean_url(urls[0]) if urls else ""
        return definition, source, response.usage.input_tokens, response.usage.output_tokens, searches
