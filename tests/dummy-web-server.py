#!/usr/bin/python3
"""
Very simple HTTP server in python (Updated for Python 3.7)

Usage:

    ./dummy-web-server.py -h
    ./dummy-web-server.py -l localhost -p 8000

Send a GET request:

    curl http://localhost:8000

Send a HEAD request:

    curl -I http://localhost:8000

Send a POST request:

    curl -d 'foo=bar&bin=baz' http://localhost:8000

This code is available for use under the MIT license.

----

Copyright 2021 Brad Montgomery

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the 'Software'), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial
portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
import argparse
import os.path as op
import sys
from urllib.parse import unquote
from http.server import HTTPServer, BaseHTTPRequestHandler
queries = {}
queries_octo = {}
comments = {}


class S(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def _html(self, message):
        """This just generates an HTML document that includes `message`
        in the body. Override, or re-write this do do more interesting stuff.

        """
        content = "<html><body><h1>{}</h1></body></html>".format(message)
        return content.encode("utf8")  # NOTE: must return a bytes object!

    def do_GET(self):
        get_data = unquote(self.path)[2:]
        self._set_headers()
        if get_data in queries_octo:
            self.wfile.write(queries_octo[get_data].encode("utf8"))
            print("Known octo query "+comments[get_data])
        else:
            get_data = get_data.replace('%7E', '~')
            if get_data in queries_octo:
                self.wfile.write(queries_octo[get_data].encode("utf8"))
                print("Known query (7E replaced) "+comments[get_data])
            else:
                print('Unknown query, {}'.format(get_data))
                content = "<html><body><h1>GET!</h1><pre>{}</pre></body></html>".format(get_data)
                self.wfile.write(content.encode("utf8"))
        sys.stdout.flush()

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])  # <--- Gets the size of data
        post_data = self.rfile.read(content_length).decode('utf8')  # <--- Gets the data itself
        self._set_headers()
        if post_data in queries:
            self.wfile.write(queries[post_data].encode("utf8"))
            print("Known query "+comments[post_data])
        else:
            post_data = post_data.replace('%7E', '~')
            if post_data in queries:
                self.wfile.write(queries[post_data].encode("utf8"))
                print("Known query (7E replaced) "+comments[post_data])
            else:
                data = unquote(post_data.replace('+', ' '))
                print('Unknown query, len={}\n{}\n{}'.format(content_length, post_data, data))
                content = "<html><body><h1>POST!</h1><pre>{}</pre></body></html>".format(post_data)
                self.wfile.write(content.encode("utf8"))
        sys.stdout.flush()


def load_queries(file):
    global queries
    with open(file, 'rt') as f:
        is_query = True
        last_comment = None
        id = 1
        for line in f:
            line = line[:-1]
            if line[0] == '#':
                last_comment = line[1:].strip()
                id = 1
            elif is_query:
                query = line
                # Octopart changed it. It was before we collected the queries.
                # To avoid collecting all of them we currently patch the queries.
                query = query.replace('Arrow+Electronics%2C+Inc.', 'Arrow+Electronics')
                is_query = False
            else:
                # print(query)
                # print(len(query))
                queries[query] = line
                comments[query] = '{} ({})'.format(last_comment, id)
                id += 1
                is_query = True


def load_octo_queries(file):
    global queries_octo
    with open(file, 'rb') as f:
        is_query = True
        last_comment = None
        id = 1
        for line in f:
            line = line.decode('latin1')
            if line[0] == '#':
                last_comment = line[1:-1].strip()
                id = 1
            elif is_query:
                query = line[:-1]
                is_query = False
                reply = ''
            elif line[0] == '}':
                queries_octo[query] = reply + line
                comments[query] = '{} ({})'.format(last_comment, id)
                id += 1
                is_query = True
            else:
                # print(query)
                # print(len(query))
                reply += line


def run(server_class=HTTPServer, handler_class=S, addr="localhost", port=8000):
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)
    load_queries(op.join(op.dirname(__file__), 'kitspace_queries.txt'))
    load_octo_queries(op.join(op.dirname(__file__), 'octopart_queries.txt'))

    print("Starting httpd server on {}:{}".format(addr, port))
    httpd.serve_forever()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run a simple HTTP server")
    parser.add_argument(
        "-l",
        "--listen",
        default="localhost",
        help="Specify the IP address on which the server listens",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Specify the port on which the server listens",
    )
    args = parser.parse_args()
    run(addr=args.listen, port=args.port)
