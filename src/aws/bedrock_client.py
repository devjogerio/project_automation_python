import os
import json
from typing import Optional, Dict, Any


class BedrockClient:
    """Cliente Amazon Bedrock."""

    def __init__(
        self,
        region_name: Optional[str] = None,
        model_id: Optional[str] = None,
    ):
        self.region = region_name or os.getenv("AWS_REGION") or "us-east-1"
        self.model_id = model_id or os.getenv("BEDROCK_MODEL_ID") or ""
        try:
            import boto3  # type: ignore
            self._runtime = boto3.client(
                "bedrock-runtime",
                region_name=self.region,
            )
        except Exception:
            self._runtime = None

    def is_configured(self) -> bool:
        """Retorna se há runtime e `model_id`."""
        return bool(self._runtime and self.model_id)

    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 128,
    ) -> Dict[str, Any]:
        """Invoca o modelo e normaliza resposta."""
        if not self.is_configured():
            return {
                "error": "Bedrock não configurado",
                "region": self.region,
                "model": self.model_id,
            }
        try:
            body = json.dumps({
                "prompt": prompt,
                "max_tokens": max_tokens,
            })
            resp = self._runtime.invoke_model(
                modelId=self.model_id,
                body=body,
            )
            parsed = resp
            try:
                if isinstance(resp, dict) and "body" in resp:
                    raw = resp["body"]
                    if hasattr(raw, "read"):
                        data = raw.read()
                    else:
                        data = raw
                    if isinstance(data, (bytes, bytearray)):
                        data = data.decode("utf-8", errors="ignore")
                    parsed = json.loads(data)
            except Exception:
                parsed = resp
            return {"ok": True, "response": parsed}
        except Exception as e:
            return {"error": str(e)}
