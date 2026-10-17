import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=api_key)


def get_llm_response(system_prompt, ticket, customer_data):
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=(
            f"Support ticket:\n{ticket}\n\n"
            f"Supplied synthetic customer data:\n"
            f"{json.dumps(customer_data)}"
        ),
        config={
            "system_instruction": system_prompt,
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "OBJECT",
                "properties": {
                    "proposed_action": {
                        "type": "OBJECT",
                        "properties": {
                            "action": {
                                "type": "STRING",
                                "enum": [
                                    "issue_refund",
                                    "deny_request"
                                ]
                            },
                            "customer_id": {"type": "STRING"},
                            "amount": {"type": "NUMBER"},
                            "reason": {"type": "STRING"}
                        },
                        "required": [
                            "action",
                            "customer_id",
                            "amount",
                            "reason"
                        ]
                    },
                    "explanation": {"type": "STRING"}
                },
                "required": [
                    "proposed_action",
                    "explanation"
                ]
            }
        }
    )

    if not response.text:
        raise ValueError("The LLM returned an empty response")

    return response.text

