import json
import boto3
import os
import logging
import requests  # <-- Include in Layer 

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns = boto3.client('sns')

# Environment variables
TOPIC_ARN = os.environ.get('TOPIC_ARN') # Stored in AWS Lambda environment variables
RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY') # stored in AWS Lambda environment variables
ALLOWED_ORIGINS = ["https://aseintech.com"]

def verify_recaptcha_v2(token: str, remote_ip: str = None):
    """
    Verify reCAPTCHA v2 token with Google's siteverify endpoint.
    """
    url = "https://www.google.com/recaptcha/api/siteverify"
    payload = {
        "secret": RECAPTCHA_SECRET_KEY,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        response = requests.post(url, data=payload, timeout=5)
        result = response.json()
        logger.info(f"reCAPTCHA verification result: {result}")
        return result
    except Exception as e:
        logger.exception("Error verifying reCAPTCHA")
        return {"success": False, "error": str(e)}


def lambda_handler(event, context):
    logger.info("Lambda triggered")
    logger.info(f"Event: {json.dumps(event)}")

    if not TOPIC_ARN:
        logger.error("TOPIC_ARN not set in environment variables.")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "SNS topic not configured"}),
        }

    try:
        origin = event.get('headers', {}).get('origin', '')
        cors_origin = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]

        # --- Handle CORS preflight requests ---
        if event.get('httpMethod') == 'OPTIONS':
            logger.info("OPTIONS preflight request")
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": cors_origin,
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                },
                "body": ""
            }

        # --- Parse JSON body ---
        body = json.loads(event.get('body', '{}'))
        name = body.get('name', 'Anonymous')
        email = body.get('email', 'No email')
        message = body.get('message', '')
        token = body.get('token')

        if not token:
            logger.warning("No reCAPTCHA token provided.")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing reCAPTCHA token"}),
                "headers": {
                    "Access-Control-Allow-Origin": cors_origin,
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                }
            }

        # --- Verify reCAPTCHA v2 ---
        remote_ip = event.get("requestContext", {}).get("identity", {}).get("sourceIp", "")
        verification = verify_recaptcha_v2(token, remote_ip)

        if not verification.get("success"):
            logger.warning(f"reCAPTCHA verification failed: {verification}")
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "reCAPTCHA verification failed"}),
                "headers": {
                    "Access-Control-Allow-Origin": cors_origin,
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                }
            }

        # --- SNS Publish ---
        logger.info(f"Publishing message to SNS topic: {TOPIC_ARN}")
        sns.publish(
            TopicArn=TOPIC_ARN,
            Subject=f"Portfolio Contact Form: {name}",
            Message=f"From: {name} <{email}>\n\nMessage:\n{message}"
        )

        logger.info("SNS publish successful")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Form submitted successfully!"}),
            "headers": {
                "Access-Control-Allow-Origin": cors_origin,
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        }

    except Exception as e:
        logger.exception("Exception occurred during processing")

        friendly_message = (
            "Something went wrong while sending your message. "
            "Please try again later or reach out via LinkedIn instead."
        )

        return {
            "statusCode": 500,
            "body": json.dumps({"error": friendly_message}),
            "headers": {
                "Access-Control-Allow-Origin": ALLOWED_ORIGINS[0],
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        }
