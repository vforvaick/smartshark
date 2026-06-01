# AI Context Redaction and Provider Policy

Smartshark will be LLM-provider agnostic and will not send full capture files to AI models by default. Hosted models may be used in the MVP when explicitly configured, but AI requests should use tool-grounded summaries, selected fields, redacted snippets, opt-in raw sharing, and request provenance so sensitive packet data is not exposed accidentally and the system can later support local or self-hosted models.
