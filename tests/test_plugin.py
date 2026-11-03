"""Exercise the shared HTTP client and credential provider without paid calls."""

import copy
import importlib.util
import json
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import httpx
from dify_plugin.core.utils.yaml_loader import load_yaml_file
from dify_plugin.entities.tool import ToolConfiguration
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from glorycloud_client import search

ROOT = Path(__file__).resolve().parents[1]
TEST_KEY = "example-only-not-a-real-key"
ENGINES = ("google_search", "google_image", "google_shopping", "google_news", "google_maps")
SUCCESS = {"code": 0, "msg": "success", "data": {"requestId": "617582304539287553",
    "engine": "google_search", "resultCount": 1,
    "result": {"organic_results": [{"title": "Example", "link": "https://example.com"}],
               "extra_field": {"nullable": None}}}}


def load_class(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, name)


ProviderClass = load_class("provider/glorycloud-serp-api.py", "GlorycloudSerpApiProvider")


def engine_response(request):
    result = copy.deepcopy(SUCCESS)
    result["data"]["engine"] = request.url.path.rsplit("/", 1)[-1]
    return result


@contextmanager
def api_response(payload=engine_response, status=200, content=None, error=None, headers=None):
    requests = []
    real_client = httpx.Client

    def handle(request):
        requests.append(request)
        if error:
            raise error("Transport detail containing " + TEST_KEY, request=request)
        if content is not None:
            return httpx.Response(status, content=content, headers=headers)
        return httpx.Response(status, json=payload(request) if callable(payload) else payload, headers=headers)

    def client_factory(*args, **kwargs):
        return real_client(*args, transport=httpx.MockTransport(handle), **kwargs)

    with patch("httpx.Client", side_effect=client_factory):
        yield requests


class SearchClientTests(unittest.TestCase):
    def invoke(self, parameters, key=TEST_KEY):
        return search(key, parameters)

    def assert_rejected(self, parameters):
        with api_response() as requests:
            with self.assertRaises(ValueError):
                self.invoke(parameters)
            self.assertEqual(requests, [])

    def test_uses_new_default_path_authentication_and_minimal_body(self):
        with api_response() as requests:
            messages = self.invoke({"query": "GloryCloud"})
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(str(request.url), "https://serpapi.glorycloud.com/api/serp/google_search")
        self.assertEqual(request.headers["X-Api-Key"], TEST_KEY)
        self.assertEqual(request.headers["Content-Type"], "application/json")
        for header in ("apiKey", "Authorization", "X-Biz-Id"):
            self.assertNotIn(header, request.headers)
        self.assertEqual(json.loads(request.content), {"query": "GloryCloud"})
        self.assertNotIn(TEST_KEY, str(request.url) + request.content.decode())
        self.assertEqual(messages, SUCCESS)

    def test_routes_all_five_engines_without_putting_engine_in_the_body(self):
        for engine in ENGINES:
            with self.subTest(engine=engine), api_response() as requests:
                messages = self.invoke({"engine": engine, "query": "cafe"})
                self.assertEqual(str(requests[0].url), "https://serpapi.glorycloud.com/api/serp/" + engine)
                self.assertEqual(json.loads(requests[0].content), {"query": "cafe"})
                self.assertEqual(messages["data"]["engine"], engine)

    def test_serializes_news_parameters_into_the_documented_options(self):
        with api_response() as requests:
            self.invoke({"engine": "google_news", "query": "科技新闻", "language": "zh-CN", "maxResults": 10,
                         "location": "California,United States", "domain": "com", "page": 2,
                         "format": "json+html", "domMap": True, "timeRange": "7d"})
        self.assertEqual(json.loads(requests[0].content), {"query": "科技新闻", "language": "zh-CN", "maxResults": 10,
            "options": {"location": "California,United States", "domain": "com", "page": 2,
                        "format": ["json", "html"], "domMap": True, "timeRange": "7d"}})

    def test_maps_parameters_keep_zero_coordinates_false_values_and_page_token(self):
        with api_response() as requests:
            self.invoke({"engine": "google_maps", "query": "cafe", "language": "en", "country": "us",
                         "maxResults": 20, "latitude": 0, "longitude": 0, "zoomLevel": 0,
                         "fetchLimit": 20, "minRating": 0, "openNow": False, "includeDetails": False,
                         "pageToken": "next-page-token", "format": "html"})
        self.assertEqual(json.loads(requests[0].content), {"query": "cafe", "language": "en", "country": "us", "maxResults": 20,
            "options": {"latitude": 0.0, "longitude": 0.0, "zoomLevel": 0, "fetchLimit": 20,
                        "minRating": 0.0, "openNow": False, "includeDetails": False,
                        "pageToken": "next-page-token", "format": ["html"]}})

    def test_switching_search_type_omits_inactive_form_values(self):
        shared = {"query": "cafe", "country": "us", "latitude": 1, "longitude": 2, "zoomLevel": 4,
                  "fetchLimit": 10, "minRating": 4, "openNow": True, "includeDetails": False,
                  "pageToken": "old-map-token", "location": "London", "domain": "co.uk",
                  "page": 2, "domMap": True, "timeRange": "7d"}
        with api_response() as requests:
            self.invoke({**shared, "engine": "google_maps"})
            self.invoke({**shared, "engine": "google_image"})
        self.assertEqual(json.loads(requests[0].content), {"query": "cafe", "country": "us",
            "options": {"latitude": 1.0, "longitude": 2.0, "zoomLevel": 4, "fetchLimit": 10,
                        "minRating": 4.0, "openNow": True, "includeDetails": False, "pageToken": "old-map-token"}})
        self.assertEqual(json.loads(requests[1].content), {"query": "cafe",
            "options": {"location": "London", "domain": "co.uk", "page": 2, "domMap": True}})

    def test_accepts_real_sdk_defaults_for_the_independent_maps_form(self):
        config = ToolConfiguration(**load_yaml_file(str(ROOT / "tools/google_maps.yaml")))
        parameters = {p.name: p.default for p in config.parameters if p.default is not None}
        parameters.update(query="cafe", engine="google_maps")
        with api_response() as requests:
            self.invoke(parameters)
        body = json.loads(requests[0].content)
        self.assertNotIn("domMap", body.get("options", {}))
        self.assertNotIn("latitude", body.get("options", {}))
        self.assertNotIn("country", body)
        self.assertEqual(body["options"]["format"], ["json"])

    def test_omits_blank_optional_inputs_without_inventing_server_defaults(self):
        with api_response() as requests:
            self.invoke({"query": "x", "language": " ", "location": "", "domain": None,
                         "page": "", "maxResults": None, "format": ""})
        self.assertEqual(json.loads(requests[0].content), {"query": "x"})

    def test_preserves_query_text_and_enforces_utf8_byte_limit(self):
        for query in ("  cafe  ", "a" * 2048, "中" * 682 + "ab"):
            with api_response() as requests:
                self.invoke({"query": query})
                self.assertEqual(json.loads(requests[0].content)["query"], query)
        for query in ("a" * 2049, "中" * 683, "", " \t\n", None, 42, "\ud800"):
            self.assert_rejected({"query": query})

    def test_rejects_unknown_engines_and_path_injection_before_http(self):
        for engine in ("", None, "bing", "../google_search", "google_maps?key=secret", "https://example.com", 2):
            self.assert_rejected({"query": "x", "engine": engine})

    def test_rejects_legacy_or_unknown_parameters_with_reconfiguration_advice(self):
        for field in ("gl", "lang", "hostLang", "retry", "options", "unexpected"):
            with self.subTest(field=field), api_response() as requests:
                with self.assertRaisesRegex(ValueError, "[Rr]econfigur"):
                    self.invoke({"query": "x", field: "old-value"})
                self.assertEqual(requests, [])

    def test_max_results_uses_each_engine_limit_and_zero_means_no_truncation(self):
        for engine, limit in (("google_search", 100), ("google_image", 100), ("google_shopping", 100),
                              ("google_news", 100), ("google_maps", 40)):
            for value in (0, limit):
                with api_response() as requests:
                    self.invoke({"query": "x", "engine": engine, "maxResults": value})
                    self.assertEqual(json.loads(requests[0].content)["maxResults"], value)
            self.assert_rejected({"query": "x", "engine": engine, "maxResults": limit + 1})
        for value in (-1, 1.5, True, float("nan"), float("inf"), "bad"):
            self.assert_rejected({"query": "x", "maxResults": value})

    def test_accepts_integral_workflow_numbers_without_legacy_page_100_cap(self):
        with api_response() as requests:
            self.invoke({"query": "x", "page": "101", "maxResults": 1.0})
        body = json.loads(requests[0].content)
        self.assertEqual(body, {"query": "x", "maxResults": 1, "options": {"page": 101}})
        self.assertIs(type(body["maxResults"]), int)
        for page in (0, -1, 1.5, True, "bad", float("inf")):
            self.assert_rejected({"query": "x", "page": page})

    def test_maps_rejects_unpaired_or_out_of_range_coordinates(self):
        for options in ({"latitude": 0}, {"longitude": 0}, {"latitude": 91, "longitude": 0},
                        {"latitude": 0, "longitude": -181}, {"latitude": float("nan"), "longitude": 0},
                        {"latitude": True, "longitude": 0}):
            self.assert_rejected({"query": "x", "engine": "google_maps", **options})
        for latitude, longitude in ((-90, -180), (90, 180)):
            with api_response() as requests:
                self.invoke({"query": "x", "engine": "google_maps", "latitude": latitude, "longitude": longitude})
                self.assertEqual(json.loads(requests[0].content)["options"], {"latitude": float(latitude), "longitude": float(longitude)})

    def test_maps_validates_country_zoom_count_and_rating(self):
        for field, bad in (("country", "USA"), ("zoomLevel", -1), ("zoomLevel", 22), ("zoomLevel", 1.5),
                           ("fetchLimit", 0), ("fetchLimit", 41), ("minRating", -0.1), ("minRating", 5.1)):
            self.assert_rejected({"query": "x", "engine": "google_maps", field: bad})

    def test_news_accepts_only_documented_time_ranges(self):
        for value in ("1h", "1d", "7d", "1m", "1y"):
            with api_response() as requests:
                self.invoke({"query": "x", "engine": "google_news", "timeRange": value})
                self.assertEqual(json.loads(requests[0].content)["options"]["timeRange"], value)
        self.assert_rejected({"query": "x", "engine": "google_news", "timeRange": "30d"})

    def test_serializes_each_result_format_as_an_array(self):
        for value, expected in (("json", ["json"]), ("html", ["html"]), ("json+html", ["json", "html"])):
            with api_response() as requests:
                self.invoke({"query": "x", "format": value})
                self.assertEqual(json.loads(requests[0].content)["options"]["format"], expected)
        self.assert_rejected({"query": "x", "format": "xml"})

    def test_sdk_boolean_numbers_and_string_false_have_boolean_meanings(self):
        for value, expected in ((0, False), (1, True), ("false", False), ("true", True)):
            with api_response() as requests:
                self.invoke({"query": "x", "domMap": value})
                self.assertIs(json.loads(requests[0].content)["options"]["domMap"], expected)
        for value in (2, "maybe", 1.5):
            self.assert_rejected({"query": "x", "domMap": value})

    def test_rejects_nonstring_optional_text_and_oversized_request_before_http(self):
        for field in ("language", "location", "domain"):
            self.assert_rejected({"query": "x", field: {"wrong": "type"}})
        self.assert_rejected({"query": "x", "location": "a" * 65536})

    def test_preserves_complete_results_html_locations_and_unrecognized_fields(self):
        expected = copy.deepcopy(SUCCESS)
        expected["data"]["result"]["organicResults"] = {"page_html": "<html>test</html>"}
        expected["data"]["result"]["organic_results"][0]["loc"] = {"item": "[data-x='1']", "fields": {"title": "h3"}}
        with api_response(expected):
            messages = self.invoke({"query": "x", "domMap": True})
        self.assertEqual(messages, expected)

    def test_accepts_empty_results_and_unknown_result_count(self):
        for count in (0, None):
            expected = copy.deepcopy(SUCCESS)
            expected["data"].update(resultCount=count, result={})
            with api_response(expected):
                messages = self.invoke({"query": "x"})
                self.assertEqual(messages, expected)

    def test_reports_business_failure_even_when_http_is_200(self):
        with api_response({"code": 1506, "msg": "quota exhausted", "data": {"requestId": "123"}}):
            with self.assertRaises(ValueError) as raised:
                self.invoke({"query": "x"})
        for detail in ("1506", "quota", "123"):
            self.assertIn(detail, str(raised.exception))

    def test_http_errors_include_safe_service_code_and_request_id_without_retry(self):
        for status, code in ((400, 1501), (401, 1502), (403, 1506), (429, 1507), (503, 1511)):
            with self.subTest(status=status), api_response({"code": code, "msg": "problem " + TEST_KEY,
                    "data": {"requestId": "12345"}}, status=status) as requests:
                with self.assertRaises(ValueError) as raised:
                    self.invoke({"query": "x"})
                for detail in (str(status), str(code), "12345"):
                    self.assertIn(detail, str(raised.exception))
                self.assertNotIn(TEST_KEY, str(raised.exception))
                self.assertEqual(len(requests), 1)

    def test_timeout_warns_about_billing_and_does_not_retry(self):
        with api_response({"code": 1517, "msg": "timeout", "data": {"requestId": "123"}}, status=504) as requests:
            with self.assertRaises(ValueError) as raised:
                self.invoke({"query": "x", "engine": "google_shopping"})
            self.assertEqual(len(requests), 1)
        self.assertIn("1517", str(raised.exception))
        self.assertIn("bill", str(raised.exception).lower())
        self.assertIn("retry immediately", str(raised.exception).lower())

    def test_error_messages_are_bounded_redacted_and_single_line(self):
        with api_response({"code": 1501, "msg": "bad\n" + TEST_KEY + "x" * 5000,
                           "data": {"requestId": TEST_KEY + "\n123"}}, status=400):
            with self.assertRaises(ValueError) as raised:
                self.invoke({"query": "x"})
        text = str(raised.exception)
        self.assertIn("1501", text)
        self.assertNotIn(TEST_KEY, text)
        self.assertNotIn("\n", text)
        self.assertLess(len(text), 900)

    def test_rejects_invalid_success_envelopes(self):
        for payload in ([], {}, {"code": False, "data": {}}, {"code": "0", "data": {}}, {"code": 0},
                        {"code": 0, "data": []}, {"code": 0, "data": {}}, {"code": 200, "data": SUCCESS["data"]}):
            with self.subTest(payload=payload), api_response(payload):
                with self.assertRaises(ValueError):
                    self.invoke({"query": "x"})
        for field, value in (("result", []), ("result", None), ("requestId", None), ("engine", "google_maps"),
                             ("resultCount", -1), ("resultCount", True)):
            payload = copy.deepcopy(SUCCESS)
            payload["data"][field] = value
            with self.subTest(field=field, value=value), api_response(payload):
                with self.assertRaises(ValueError):
                    self.invoke({"query": "x"})

    def test_non_json_http_error_remains_actionable_without_echoing_body(self):
        for status in (200, 401, 502):
            with api_response(content=("<html>" + TEST_KEY + "</html>").encode(), status=status):
                with self.assertRaises(ValueError) as raised:
                    self.invoke({"query": "x"})
                self.assertNotIn(TEST_KEY, str(raised.exception))
                if status != 200:
                    self.assertIn(str(status), str(raised.exception))

    def test_transport_failures_do_not_leak_credentials_or_repeat_searches(self):
        for error in (httpx.ReadTimeout, httpx.ConnectError):
            with api_response(error=error) as requests:
                with self.assertRaises(ValueError) as raised:
                    self.invoke({"query": "x"})
                self.assertNotIn(TEST_KEY, str(raised.exception))
                self.assertEqual(len(requests), 1)
                if error is httpx.ReadTimeout:
                    self.assertIn("retry immediately", str(raised.exception).lower())

    def test_does_not_forward_credentials_to_redirect_targets(self):
        with api_response(status=307, headers={"Location": "https://example.com/untrusted"}) as requests:
            with self.assertRaises(ValueError):
                self.invoke({"query": "x"})
            self.assertEqual(len(requests), 1)

    def test_rejects_missing_or_header_injection_keys_without_http(self):
        for key in (None, "", "  ", "bad\r\nX-Header: value", "中文"):
            with api_response() as requests:
                with self.assertRaises(ValueError):
                    self.invoke({"query": "x"}, key=key)
                self.assertEqual(requests, [])


class CredentialTests(unittest.TestCase):
    def test_saving_credentials_does_not_search_or_consume_quota(self):
        with api_response() as requests:
            ProviderClass().validate_credentials({"api_key": TEST_KEY})
        self.assertEqual(requests, [])

    def test_rejects_missing_or_malformed_credentials_without_http(self):
        for key in (None, "", "  ", "bad\r\nX-Header: value", "中文"):
            with api_response() as requests:
                with self.assertRaises(ToolProviderCredentialValidationError):
                    ProviderClass().validate_credentials({"api_key": key})
                self.assertEqual(requests, [])

    def test_expired_key_is_checked_at_tool_use_not_when_saving(self):
        with api_response({"code": 1502, "msg": "unauthorized", "data": {"requestId": "123"}}, status=401) as requests:
            ProviderClass().validate_credentials({"api_key": TEST_KEY})
            self.assertEqual(requests, [])
            with self.assertRaises(ValueError):
                search(TEST_KEY, {"query": "x"})
        self.assertEqual(len(requests), 1)


if __name__ == "__main__":
    unittest.main()
