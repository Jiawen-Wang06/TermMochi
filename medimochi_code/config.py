MODELS = {
    "gpt-4o-mini": {
        "cost": {"input": 0.00000015, "output": 0.00000060},
        "image_tokens": {"base": 2833, "tile": 5667},
    },
    "gpt-4o": {
        "cost": {"input": 0.0000025, "output": 0.00001},
        "image_tokens": {"base": 85, "tile": 170},
    },
}

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_FIELD = "software in the medical field"
TEMPERATURE = 0.2
MAX_TOKENS = 4000
LOOKUP_WORKERS = 5
WEB_SEARCH_COST_PER_CALL = 0.01
EXTRACTION_OUTPUT_TOKENS = 500
LOOKUP_INPUT_TOKENS = 8200
LOOKUP_OUTPUT_TOKENS = 100
