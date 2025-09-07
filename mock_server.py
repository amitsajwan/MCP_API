#!/usr/bin/env python3
"""
Simple Mock Server
Basic mock API server for testing.
"""

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, format, *args):
        logger.info(f"Mock Server: {format % args}")

def main():
    parser = argparse.ArgumentParser(description="Simple Mock API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=9001, help="Port to bind to")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), MockHandler)
    logger.info(f"Mock server running on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Mock server stopped")

if __name__ == "__main__":
    main()
