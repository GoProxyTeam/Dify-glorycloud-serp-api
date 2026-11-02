# glorycloud SERP API

在 Dify 工作流中搜索 Google 网页、图片、购物、新闻和地图，获取可供后续节点使用的搜索结果。适用于联网信息查询、内容整理、商品对比和商家查找等场景。

作者：glorycloud

联系邮箱：[support@glorycloud.com](mailto:support@glorycloud.com)。

源码仓库：[GoProxyTeam/Dify-glorycloud-serp-api](https://github.com/GoProxyTeam/Dify-glorycloud-serp-api)。

## 使用前准备

1. 前往 [GloryCloud 账户设置](https://www.glorycloud.com/dashboard/settings/?link=1142bb)，获取自己的 SERP API Key。
2. 确认账户已开通所需搜索类型，并有可用额度。
3. 在 Dify 中安装 **glorycloud SERP API**。

## 配置授权

1. 打开插件的授权配置。
2. 新建凭据，填写便于识别的名称，并输入 **GloryCloud API Key**。
3. 选择谁可以使用该凭据，保存配置。

保存时只检查 Key 的基本格式，不执行搜索。账户权限和可用额度会在调用工具时检查；保存成功不代表已经确认能够搜索。

## 在工作流中使用

1. 打开 Dify 工作流，在工具列表中展开 **glorycloud SERP API**，选择下方对应的独立工具。
2. 选择已保存的授权凭据。
3. 填写**搜索关键词**，也可以通过变量选择器绑定上游节点的字符串变量。
4. 填写该工具的参数，具体说明可查看 [官网 API 文档](https://docs.glorycloud.com/api-reference/SERP-API/Use?link=1142bb)。
5. 运行节点，查看 `json` 输出，再将结果连接到输出节点，或交给后续模型、代码节点处理。

### 选择工具

五个工具共用已保存的 GloryCloud API Key，每个工具分别提供适用的参数。

| 工具 | 用途 |
|---|---|
| 网页搜索 | 查询网页和联网信息。 |
| 图片搜索 | 查找图片、缩略图和来源信息。 |
| 购物搜索 | 查询商品列表、价格和商家信息。 |
| 新闻搜索 | 查询新闻，可按时间范围筛选。 |
| 地图搜索 | 查询地点与商家信息。 |

### 示例：查询网页信息

| 配置项 | 示例填写 |
|---|---|
| 工具 | 网页搜索 |
| 搜索关键词 | `GloryCloud` |
| 界面语言 | `en` |
| 结果数上限 | `5` |
| 搜索地区 | `California,United States` |
| Google 域名后缀 | `com` |
| 页码 | `1` |
| 结果格式 | 结构化结果（JSON） |

运行后可在节点输出中查看搜索结果和请求 ID。结果数上限只是最多返回多少条，不保证一定有足够的匹配结果。

## 搜索参数

五个工具分别对应网页、图片、购物、新闻和地图接口，参数各不相同。请前往 [GloryCloud SERP API 文档](https://docs.glorycloud.com/api-reference/SERP-API/Use?link=1142bb) 查看对应接口的参数说明、必填项和请求示例。

使用时，请按所选接口的文档，在 Dify 工具节点中填写对应参数。

## 如何使用返回结果

插件每次返回一个 JSON 响应对象。Dify 工具节点的 `json` 输出是一个数组，先取第一项，即 `json[0]`；下表路径均从该响应对象开始。

| 字段 | 说明 |
|---|---|
| `code` | 为 `0` 表示成功。 |
| `data.requestId` | 本次请求 ID，遇到问题时可提供给客服排查。 |
| `data.engine` | 本次使用的搜索类型。 |
| `data.resultCount` | 结果条数；服务无法确定条数时可能为 `null`。 |
| `data.result` | 完整搜索结果，不同搜索类型的内部字段不同。 |

网页结果位于 `data.result.organicResults`，其中 `organic_results` 是自然搜索列表；图片列表为 `data.result.imageResults`，购物列表为 `data.result.shoppingResults`，新闻列表为 `data.result.newsResults`，地图地点列表为 `data.result.places`。读取具体字段时，请兼容字段缺失或为空的情况。

如需在代码节点中提取结果，新增输入变量 `search_output`，绑定本工具节点的 `json` 输出；再配置输出变量 `result`（Object 类型）和 `request_id`（String 类型）：

```python
def main(search_output: list) -> dict:
    response = search_output[0]
    return {
        "result": response["data"]["result"],
        "request_id": response["data"]["requestId"],
    }
```

## 常见问题

| 遇到的问题 | 处理方式 |
|---|---|
| 授权能保存，但搜索失败 | 检查 Key、账户状态、搜索类型权限和可用额度；保存授权不会调用搜索服务。 |
| 提示参数错误 | 检查参数的适用搜索类型和数值范围；地图经纬度须一起填写。 |
| 没有结果，或结果不足设定数量 | 尝试调整关键词、减少筛选条件；结果数上限不代表保证返回条数，空结果也可能是成功查询。 |
| 提示超过频率限制 | 降低并发，等待后再使用。 |
| 提示查询超时 | 不要立即重复提交，搜索任务可能仍会完成并计费；请先检查用量。插件不会自动重试。 |
| 后续节点找不到搜索内容 | 绑定工具节点的 `json` 输出，取第一项后读取 `data.result`。 |

实际搜索遵循账户的用量和计费规则。减少返回结果条数不会减少本次搜索的调用次数。

## V0.0.1 首次发布

本版本为首次市场发版，连接正式环境 `https://serpapi.glorycloud.com`，提供五个独立工具，共用已保存的 GloryCloud API Key。此前本地开发包 0.2.0 的独立工具及参数保持一致，已有独立工具节点可继续使用。
