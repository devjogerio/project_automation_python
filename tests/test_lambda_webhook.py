import json
from src.aws.lambdas.webhook_handler import handler


def test_lambda_webhook_without_bucket():
    event = {"body": {"hello": "world"}}
    res = handler(event, None)
    body = json.loads(res["body"])
    assert res["statusCode"] == 500
    assert "AWS_S3_BUCKET" in body.get("error", "")
