
import os
import json
from http.server import BaseHTTPRequestHandler
from supabase import create_client


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            supabase = create_client(
                os.environ["SUPABASE_URL"],
                os.environ["SUPABASE_SERVICE_ROLE_KEY"]
            )

            result = (
                supabase.table("site_stats")
                .select("student_count")
                .eq("id", 1)
                .single()
                .execute()
            )

            count = result.data["student_count"]

            self.send_response(200)
            self.send_header(
                "Content-Type", "application/json"
            )
            self.send_header(
                "Cache-Control", "no-store"
            )
            self.end_headers()

            self.wfile.write(
                json.dumps({"count": count}).encode()
            )

        except Exception as error:
            print("Student count error:", error)
            self.send_response(500)
            self.end_headers()
