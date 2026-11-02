from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from glorycloud_client import GloryCloudError, validate_api_key


class GlorycloudSerpApiProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            # Saving credentials must not send a search or consume service quota.
            validate_api_key(credentials.get("api_key"))
        except GloryCloudError as error:
            raise ToolProviderCredentialValidationError(str(error)) from None
