import socketserver
import re
import os
import datetime
import pathlib


class MyWebServer(socketserver.BaseRequestHandler):

    request_line_regex = re.compile("([A-Z]+) (.*) (HTTP\/(.*))")
    allowed_methods = "GET"
    error_html = """<!DOCTYPE html>
<html>
<head>
	<title>Error {}</title>
</head>
<body>
	<div>
		<h1>{}</h1>
	</div>
</body>
</html>"""

    def handle(self):
        self.data = self.request.recv(1024).strip()

        request = self.parse_http_request(self.data)
        response = {"request": request}

        if request["method"] not in self.allowed_methods:
            response["status_code"] = "405"
        else:
            resource_path = pathlib.Path() / "www" / request["uri"][1:]
            if not resource_path.exists():
                response["status_code"] = "404"
            elif resource_path.is_dir():
                if (
                    len(request["uri"]) > 1
                    and request["uri"][len(request["uri"]) - 1] != "/"
                ):
                    response["status_code"] = "301"
                    response["path"] = resource_path
                else:
                    response["status_code"] = "200"
                    resource_path = resource_path / "index.html"
                    response["path"] = resource_path
            else:
                response["status_code"] = "200"
                response["path"] = resource_path

        if (
            response["status_code"] == "200"
            and (pathlib.Path() / "www").resolve().absolute()
            not in response["path"].resolve().absolute().parents
        ):
            response["status_code"] = "404"

        self.send_response(response)

    def parse_http_request(self, request_data):
        request_string = request_data.decode("utf-8")
        lines = request_string.split("\r\n")

        assert len(lines) >= 2

        request = {}

        status_line = lines[0]

        match = re.match(self.request_line_regex, status_line)
        method, uri, version, version_no = match.groups()

        request["method"] = method
        request["uri"] = uri
        request["http_version"] = version_no

        return request

    def send_response(self, response):
        response_lines = []

        if response["status_code"] == "200":
            status = "HTTP/1.1 200 OK"
            
            file_type = response["path"].suffix
            if file_type == ".css":
                content_type_line = "Content-Type: text/css; charset=utf-8"
            elif file_type == ".html":
                content_type_line = "Content-Type: text/html; charset=utf-8"
                
            with open(response["path"], "r") as f:
                body = f.read()
                
        elif response["status_code"] == "301":
            status = "HTTP/1.1 301 Moved Permanently"
            
            hostname, port = self.request.getsockname()
            location_line = "Location: http://{}:{}/{}".format(
                hostname, port, str(response["path"].relative_to("www")) + "/"
            )
            response_lines.append(location_line)
            body = self.error_html.format("301", "301 Moved Permanently")
            content_type_line = "Content-Type: text/html; charset=utf-8"
            
        elif response["status_code"] == "404":
            status = "HTTP/1.1 404 Not Found"
            
            body = self.error_html.format("404", "404 Not Found")
            content_type_line = "Content-Type: text/html; charset=utf-8"
            
        elif response["status_code"] == "405":
            status = "HTTP/1.1 405 Method Not Allowed"
            
            body = self.error_html.format("405", "405 Method Not Allowed")
            content_type_line = "Content-Type: text/html; charset=utf-8"
            
        content_length = "Content-Length: {}".format(
            len(bytearray(body, "utf-8"))
        )
        
        connection = "Connection: Closed"
        
        response_lines = [status] + response_lines + [connection, content_type_line, content_length, "", body]

        response_string = "\r\n".join(response_lines)
        self.request.sendall(bytearray(response_string, "utf-8"))
