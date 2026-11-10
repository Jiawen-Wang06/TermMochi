import tiktoken


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def calculate_cost(input_tokens: int, output_tokens: int, input_price: float, output_price: float) -> float:
    return input_tokens * input_price + output_tokens * output_price


def format_cost(cost: float) -> str:
    if cost < 0.001:
        return f"${cost:.6f}"
    return f"${cost:.4f}"
