# Privacy disclosure for glorycloud SERP API

This document describes this plugin's implementation. See the [GloryCloud Privacy Policy](https://www.glorycloud.com/privacy/) for the service's privacy terms. GloryCloud's service terms and your Dify deployment's data policies apply separately.

## Data sent to GloryCloud

For each invocation, the plugin sends the configured customer's API key in the `X-Api-Key` header to `https://serpapi.glorycloud.com/api/serp/{engine}`. Service requests use HTTPS. Five independent tools share the saved credential and each uses its own fixed path for Google web, images, shopping, news or maps. The plugin does not follow redirects.

Requests contain the search query and the selected optional language, result limit, result format and search-type-specific settings. These can include a search location, domain, page, DOM mapping, news time range, country, map center coordinates, zoom level, place count, rating filter, opening filter, business-details setting and page token. Coordinates are provided by the workflow; the plugin does not collect a device's location.

Saving credentials performs only local input checks and makes no service request. Account usage and billing rules apply when searches are executed. The plugin does not automatically repeat failed or timed-out searches.

The complete successful response is returned to Dify, including the request ID and any requested original HTML or location selectors. Later forwarding to models or other services depends on the application's configuration.

## Storage and logging

Dify manages saved keys, credential access, workflow inputs and outputs according to its deployment's configuration. This plugin does not independently persist keys, queries or results, create search logs, or contact analytics endpoints.

The plugin reports bounded service explanations with the configured key redacted and control characters removed. It does not echo raw transport exceptions, request headers or raw error response bodies. Error messages may contain the service's explanation of submitted parameters and the request ID.

GloryCloud may keep account usage, billing and service-side request records according to its policies. A timeout does not establish that a search was not executed or billed.

## Retention and deletion

The Dify deployment's policies govern retention of credentials and workflow history. GloryCloud's policies govern service-side records. This plugin defines no independent retention period.

Remove credentials and workflow history through the applicable Dify controls. For account data or service-side deletion requests, contact [support@glorycloud.com](mailto:support@glorycloud.com).

## External destinations

The plugin's service requests go only to `serpapi.glorycloud.com`. Help and account links are opened by users in their browser. Any network proxy used by a Dify deployment is controlled by that deployment's configuration.
