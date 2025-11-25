import os
import json
import time
from typing import Any, Dict


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Função Lambda para receber webhooks (ex.: WAHA) e armazenar em S3.

    - Lê `AWS_S3_BUCKET` do ambiente
    - Salva o corpo no caminho `webhooks/<timestamp>.json`
    """
    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "AWS_S3_BUCKET não definido"})
        }

    body = event.get("body")
    if isinstance(body, str):
        payload = body
    else:
        payload = json.dumps(body or {})

    key = f"webhooks/{int(time.time())}.json"
    try:
        import boto3  # type: ignore
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket, Key=key, Body=payload.encode("utf-8")
        )
        return {
            "statusCode": 200,
            "body": json.dumps({"stored": True, "key": key})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
