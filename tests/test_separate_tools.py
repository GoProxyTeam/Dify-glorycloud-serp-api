"""Verify the five entries and their real Dify SDK invocation boundaries."""

import copy
import json
import unittest

from dify_plugin.config.config import DifyPluginEnv
from dify_plugin.core.plugin_registration import PluginRegistration

from test_plugin import TEST_KEY, SUCCESS, api_response


EXPECTED = {
    "google_search": {"query", "language", "maxResults", "format", "location", "domain", "page", "domMap"},
    "google_image": {"query", "language", "maxResults", "format", "location", "domain", "page", "domMap"},
    "google_shopping": {"query", "language", "maxResults", "format", "location", "domain", "page", "domMap"},
    "google_news": {"query", "language", "maxResults", "format", "location", "domain", "page", "domMap", "timeRange"},
    "google_maps": {"query", "language", "maxResults", "format", "country", "latitude", "longitude", "zoomLevel",
                    "fetchLimit", "minRating", "openNow", "includeDetails", "pageToken"},
}
LABELS = {"google_search": "网页搜索", "google_image": "图片搜索", "google_shopping": "购物搜索",
          "google_news": "新闻搜索", "google_maps": "地图搜索"}


class SeparateToolTests(unittest.TestCase):
    def registration(self):
        registration = PluginRegistration(DifyPluginEnv())
        self.assertEqual(set(registration.tools_mapping), {"glorycloud-serp-api"})
        provider, provider_class, tools = registration.tools_mapping["glorycloud-serp-api"]
        self.assertEqual(set(tools), set(EXPECTED), "The provider must expose exactly five independent tools")
        return provider, provider_class, tools

    def test_provider_exposes_five_individually_named_entries_with_one_credential(self):
        provider, _, tools = self.registration()
        self.assertEqual(provider.identity.label.zh_hans, "glorycloud SERP API")
        self.assertEqual({credential.name for credential in provider.credentials_schema}, {"api_key"})
        self.assertEqual({name: config.identity.label.zh_hans for name, (config, _) in tools.items()}, LABELS)

    def test_each_form_exposes_only_its_applicable_parameters_without_engine(self):
        _, _, tools = self.registration()
        for name, (config, _) in tools.items():
            with self.subTest(tool=name):
                self.assertEqual({p.name for p in config.parameters}, EXPECTED[name])
                self.assertNotIn("engine", {p.name for p in config.parameters})
                self.assertEqual({p.name for p in config.parameters if p.required}, {"query"})

    def test_each_tool_has_a_fixed_route_and_returns_the_full_json_envelope(self):
        _, _, tools = self.registration()
        for name, (_, cls) in tools.items():
            with self.subTest(tool=name), api_response() as requests:
                messages = list(cls.from_credentials({"api_key": TEST_KEY}).invoke({"query": "test"}))
                self.assertEqual(len(requests), 1)
                self.assertEqual(str(requests[0].url), "https://serpapi.glorycloud.com/api/serp/" + name)
                self.assertEqual(json.loads(requests[0].content), {"query": "test"})
                self.assertEqual(len(messages), 1)
                expected = copy.deepcopy(SUCCESS)
                expected["data"]["engine"] = name
                self.assertEqual(messages[0].message.json_object, expected)

    def test_parameters_cannot_reroute_an_independent_tool(self):
        _, _, tools = self.registration()
        for name, (_, cls) in tools.items():
            with self.subTest(tool=name), api_response() as requests:
                supplied_engine = "google_maps" if name != "google_maps" else "google_search"
                list(cls.from_credentials({"api_key": TEST_KEY}).invoke({"query": "test", "engine": supplied_engine}))
                self.assertEqual(requests[0].url.path, "/api/serp/" + name)
                self.assertNotIn("engine", json.loads(requests[0].content))

    def test_each_registered_form_default_serializes_only_its_own_options(self):
        _, _, tools = self.registration()
        for name, (config, cls) in tools.items():
            defaults = {p.name: p.default for p in config.parameters if p.default is not None}
            with self.subTest(tool=name), api_response() as requests:
                list(cls.from_credentials({"api_key": TEST_KEY}).invoke({**defaults, "query": "test"}))
                expected = {"format": ["json"]}
                if name == "google_maps":
                    expected.update(openNow=False, includeDetails=True)
                else:
                    expected["domMap"] = False
                self.assertEqual(json.loads(requests[0].content), {"query": "test", "options": expected})

    def test_maps_limit_and_paging_are_independent_of_web_paging(self):
        _, _, tools = self.registration()
        maps = tools["google_maps"][1].from_credentials({"api_key": TEST_KEY})
        with api_response() as requests:
            with self.assertRaises(ValueError):
                list(maps.invoke({"query": "cafe", "maxResults": 41}))
            self.assertEqual(requests, [])
        with api_response() as requests:
            list(maps.invoke({"query": "cafe", "pageToken": "next", "maxResults": 40}))
            self.assertEqual(json.loads(requests[0].content), {"query": "cafe", "maxResults": 40,
                "options": {"pageToken": "next"}})

    def test_shared_credential_save_does_not_make_a_search(self):
        _, provider_class, _ = self.registration()
        with api_response() as requests:
            provider_class().validate_credentials({"api_key": TEST_KEY})
        self.assertEqual(requests, [])


if __name__ == "__main__":
    unittest.main()
