
import os
import json

from http.server import BaseHTTPRequestHandler
from supabase import create_client
from openai import OpenAI


# Connect to Supabase and OpenAI
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"]
)

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)


# Our existing Python tool
def get_student_records(field):
    allowed_fields = [
        "age",
        "grade",
        "skill"
    ]

    if field not in allowed_fields:
        return {"error": "Field not allowed"}

    response = (
        supabase.table("students")
        .select(f"student, {field}")
        .execute()
    )

    return response.data


# Describe the tool to OpenAI
tools = [
    {
        "type": "function",
        "name": "get_student_records",
        "description": (
            "Retrieve a selected field for students "
            "from the Supabase database."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "enum": [
                        "age",
                        "grade",
                        "skill"
                    ]
                }
            },
            "required": ["field"],
            "additionalProperties": False
        },
        "strict": True
    }
]


# Run the AI agent
def ask_agent():
    question = (
        "Tell me which student is the youngest."
    )

    instructions = (
        "Use the student tool to retrieve database "
        "information. Answer only using verified "
        "student records. If data is unavailable, "
        "explain what you could not determine."
        "do not use * marks"
        "After you answer the question, present one sentence 'The data also included NAME: AGE, NAME: AGE etc' with the rest of the students and age data."
        "Guess if names are female or male to decide the pronouns you use."
    )

    response = client.responses.create(
        model="gpt-6-astra",
        instructions=instructions,
        input=question,
        tools=tools,
        tool_choice="auto"
    )

    for _ in range(3):
        tool_calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            return response.output_text or (
                "The model returned no text answer."
            )

        tool_outputs = []

        for item in tool_calls:
            try:
                arguments = json.loads(item.arguments)

                if item.name == "get_student_records":
                    result = get_student_records(
                        arguments["field"]
                    )
                else:
                    result = {"error": "Unknown tool"}

            except Exception as error:
                result = {"error": str(error)}

            tool_outputs.append({
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": json.dumps(result)
            })

        response = client.responses.create(
            model="gpt-6-astra",
            previous_response_id=response.id,
            instructions=instructions,
            input=tool_outputs,
            tools=tools,
            tool_choice="auto"
        )

    if any(
        item.type == "function_call"
        for item in response.output
    ):
        return "Maximum tool rounds reached."

    return response.output_text or "No answer produced."


# Handle requests from the website
class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            result = ask_agent()

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/json"
            )
            self.end_headers()

            self.wfile.write(
                json.dumps({"answer": result}).encode()
            )

        except Exception as error:
            print("Backend error:", error)

            self.send_response(500)
            self.send_header(
                "Content-Type",
                "application/json"
            )
            self.end_headers()

            self.wfile.write(
                json.dumps({
                    "error": "Backend processing failed"
                }).encode()
            )
