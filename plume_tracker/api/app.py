from http.server import BaseHTTPRequestHandler
from ..core.services import PlumeService
import asyncio
import json

service = PlumeService()

class handler(BaseHTTPRequestHandler):
    async def get_top_earners(self):
        data = await service.get_top_earners()
        return {
            'statusCode': 200,
            'body': json.dumps(data),
            'headers': {'Content-Type': 'application/json'}
        }

    def do_GET(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.get_top_earners())
            self.send_response(result['statusCode'])
            for k, v in result['headers'].items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(result['body'].encode())
        finally:
            loop.close()