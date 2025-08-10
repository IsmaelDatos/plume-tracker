from http.server import BaseHTTPRequestHandler
from io import BytesIO
from plume_tracker.app import app

class VercelHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.do_request('GET')
    
    def do_POST(self):
        self.do_request('POST')

    def do_request(self, method):
        # Crear un entorno WSGI compatible
        environ = {
            'REQUEST_METHOD': method,
            'PATH_INFO': self.path,
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.input': BytesIO(),
            'wsgi.errors': sys.stderr,
            'wsgi.version': (1, 0),
            'wsgi.run_once': False,
            'wsgi.url_scheme': 'http',
            'wsgi.multithread': False,
            'wsgi.multiprocess': False
        }

        # Ejecutar la aplicación Flask
        response = app(environ, self.start_response)
        self.send_response(self.status_code)
        
        # Enviar headers
        for header, value in self.headers.items():
            self.send_header(header, value)
        self.end_headers()
        
        # Enviar cuerpo de la respuesta
        for data in response:
            self.wfile.write(data)

def handler(request, context):
    # Adaptador para la función Lambda de Vercel
    return VercelHandler(request, context)