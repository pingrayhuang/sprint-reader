import sys
import os
import asyncio
from io import BytesIO

path = '/home/rayhuang/sprint-reader'
if path not in sys.path:
    sys.path.insert(0, path)
os.chdir(path)

from app.db import init_migrations
init_migrations()

from app.main import app as asgi_app

STATUS_PHRASES = {
    200: "OK", 201: "Created", 204: "No Content",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
    404: "Not Found", 405: "Method Not Allowed", 422: "Unprocessable Entity",
    500: "Internal Server Error",
}


def application(environ, start_response):
    method = environ['REQUEST_METHOD']
    path_info = environ.get('PATH_INFO', '/')
    query_string = environ.get('QUERY_STRING', '').encode('latin-1')

    headers = []
    for key, value in environ.items():
        if key.startswith('HTTP_'):
            name = key[5:].lower().replace('_', '-').encode('latin-1')
            headers.append((name, value.encode('latin-1')))
    if environ.get('CONTENT_TYPE'):
        headers.append((b'content-type', environ['CONTENT_TYPE'].encode('latin-1')))
    if environ.get('CONTENT_LENGTH'):
        headers.append((b'content-length', environ['CONTENT_LENGTH'].encode('latin-1')))

    content_length = int(environ.get('CONTENT_LENGTH') or 0)
    body = environ['wsgi.input'].read(content_length) if content_length > 0 else b''

    scope = {
        'type': 'http',
        'asgi': {'version': '3.0'},
        'http_version': '1.1',
        'method': method,
        'headers': headers,
        'path': path_info,
        'query_string': query_string,
        'root_path': environ.get('SCRIPT_NAME', ''),
        'server': (environ.get('SERVER_NAME', 'localhost'),
                   int(environ.get('SERVER_PORT', 80))),
    }

    async def handle():
        resp_status = [None]
        resp_headers = [None]
        resp_body = BytesIO()

        async def receive():
            return {'type': 'http.request', 'body': body, 'more_body': False}

        async def send(message):
            if message['type'] == 'http.response.start':
                resp_status[0] = message['status']
                resp_headers[0] = message['headers']
            elif message['type'] == 'http.response.body':
                resp_body.write(message.get('body', b''))

        await asgi_app(scope, receive, send)
        return resp_status[0], resp_headers[0], resp_body.getvalue()

    try:
        status_code, resp_headers, body_bytes = asyncio.run(handle())
        phrase = STATUS_PHRASES.get(status_code, 'Unknown')
        status_str = f'{status_code} {phrase}'
        str_headers = [
            (k.decode('latin-1') if isinstance(k, bytes) else k,
             v.decode('latin-1') if isinstance(v, bytes) else v)
            for k, v in (resp_headers or [])
        ]
        start_response(status_str, str_headers)
        return [body_bytes]
    except Exception as e:
        import traceback
        traceback.print_exc()
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [f'Internal Server Error: {e}'.encode()]
