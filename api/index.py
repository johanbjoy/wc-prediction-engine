import sys
import os
from http.server import BaseHTTPRequestHandler

# Ensure the root directory is accessible so we can import dashboard.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard import generate_html

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        try:
            # Vercel has read-only filesystem except for /tmp
            tmp_path = "/tmp/dashboard.html"
            generate_html(tmp_path)
            
            with open(tmp_path, "r", encoding="utf-8") as f:
                html = f.read()
                
            self.wfile.write(html.encode('utf-8'))
        except Exception as e:
            error_msg = f"<!DOCTYPE html><html><body><h1>Error generating dashboard</h1><p>{str(e)}</p></body></html>"
            self.wfile.write(error_msg.encode('utf-8'))
