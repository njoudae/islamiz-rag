"""Question embedding through a hosted copy of the index's own model.

Used on small hosts that cannot hold BAAI/bge-m3 in memory. The stored index is unchanged:
only the question is embedded remotely, then compared with the stored vectors as usual.
"""
from __future__ import annotations

import httpx


class CloudflareBgeM3:
    """BAAI/bge-m3 dense (CLS) vectors from Cloudflare Workers AI."""

    model_name = "BAAI/bge-m3"

    def __init__(self, account_id: str, api_token: str, timeout: float = 30.0) -> None:
        if not account_id or not api_token:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required for hosted embeddings")
        self._url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/baai/bge-m3"
        self._client = httpx.Client(headers={"Authorization": f"Bearer {api_token}"}, timeout=timeout)

    def embed_query(self, text: str) -> list[float]:
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                response = self._client.post(self._url, json={"text": [text]})
                response.raise_for_status()
                return response.json()["result"]["data"][0]
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
                last_error = error
        raise RuntimeError(f"Hosted embedding request failed: {type(last_error).__name__}") from last_error


class CloudflareReranker:
    """Cross-encoder scores from Cloudflare Workers AI (@cf/baai/bge-reranker-base).

    Optional and off by default. On the 40-question benchmark this model lowered Arabic
    retrieval quality, so it is here to be tried, not as a recommended setting.
    """

    model_name = "@cf/baai/bge-reranker-base"

    def __init__(self, account_id: str, api_token: str, timeout: float = 20.0) -> None:
        if not account_id or not api_token:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required for the hosted reranker")
        self._url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{self.model_name}"
        self._client = httpx.Client(headers={"Authorization": f"Bearer {api_token}"}, timeout=timeout)

    def scores(self, query: str, passages: list[str]) -> list[float]:
        """One score per passage, in the order given. Raises if the service does not answer."""
        response = self._client.post(self._url, json={"query": query, "contexts": [{"text": text} for text in passages]})
        response.raise_for_status()
        result = response.json()["result"]
        items = result["response"] if isinstance(result, dict) else result
        scores = [float("-inf")] * len(passages)
        for item in items:
            scores[int(item["id"])] = float(item["score"])
        return scores

