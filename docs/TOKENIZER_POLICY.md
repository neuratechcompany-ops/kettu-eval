# Tokenizer Policy

Every token metric must include: tokenizer_id, tokenizer_version, model_family, counting_method, estimated flag.

Supported tokenizers: cl100k_base (tiktoken), heuristic fallback (len//3).

If exact tokenizer unavailable → estimated=true.
