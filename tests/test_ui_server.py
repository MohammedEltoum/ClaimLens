import base64
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

from triage_agent.ui_server import TriageUIHandler, decode_image_data_url


class DecodeImageDataUrlTests(unittest.TestCase):
    def test_decodes_png_data_url(self):
        encoded = base64.b64encode(b"png bytes").decode("ascii")
        image_bytes, suffix = decode_image_data_url(f"data:image/png;base64,{encoded}")

        self.assertEqual(image_bytes, b"png bytes")
        self.assertEqual(suffix, ".png")

    def test_rejects_non_image_data_url(self):
        encoded = base64.b64encode(b"text").decode("ascii")

        with self.assertRaises(ValueError):
            decode_image_data_url(f"data:text/plain;base64,{encoded}")


class TriageUIHandlerTests(unittest.TestCase):
    def test_health_endpoint(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), TriageUIHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            port = server.server_address[1]
            with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))

            self.assertEqual(payload, {"ok": True})
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
