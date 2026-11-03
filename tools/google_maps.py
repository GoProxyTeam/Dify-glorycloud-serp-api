from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from glorycloud_client import search


class GoogleMapsSearchTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        result = search(self.runtime.credentials.get("api_key"), {**tool_parameters, "engine": "google_maps"})
        yield self.create_json_message(result)
