
import os
import hmac
import json

from http.server import BaseHTTPRequestHandler
from supabase import create_client


class handler(BaseHTTPRequestHandler):

    def do_POST(self):

        # Check that the webhook knows our secret
        received_secret = self.headers.get(
            "X-Webhook-Secret", ""
        )

        expected_secret = os.environ[
            "STUDENT_WEBHOOK_SECRET"
        ]

        if not hmac.compare_digest(
            received_secret, expected_secret
        ):
            self.send_response(401)
            self.end_headers()
            return

        try:
            # Connect to Supabase with a server-only key
            supabase = create_client(
                os.environ["SUPABASE_URL"],
                os.environ["SUPABASE_SERVICE_ROLE_KEY"]
            )

            # Count the students currently in the table
            result = (
                supabase.table("students")
                .select("*", count="exact", head=True)
                .execute()
            )

            student_count = result.count

            # Save the new count in site_stats
            supabase.table("site_stats").update({
                "student_count": student_count
            }).eq("id", 1).execute()

            # Tell the sender it worked
            response = {
                "success": True,
                "student_count": student_count
            }

            self.send_response(200)
            self.send_header(
                "Content-Type", "application/json"
            )
            self.end_headers()

            self.wfile.write(
                json.dumps(response).encode()
            )

        except Exception as error:
            print("Webhook error:", error)

            self.send_response(500)
            self.end_headers()
