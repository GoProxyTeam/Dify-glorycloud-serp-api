# 修改日志

## 2026-11-02

- 修正 README 中五处 SERP API 文档链接，统一跳转至 `https://docs.glorycloud.com/api-reference/SERP-API/?link=1142bb`。
- 为五处 Pricing 文案补充可点击链接，跳转至 `https://www.glorycloud.com/pricing/serp-api/?link=1142bb`。
- 同步更新开发指南中的官方 API 文档地址。
- 从完整源码恢复 Provider、五个独立搜索工具、测试和中文 README。
- 恢复 README 截图及插件图标资源，并同步修正中文 README 中的 API 文档地址。
- 将 `log.md` 和 `.env.example` 加入打包忽略规则，避免开发文件进入插件包。
- 使用 Dify Plugin CLI v0.6.14 生成 `glorycloud-serp-api-0.0.1.difypkg`，并核对包内仅包含运行时文件、README、隐私声明和本地化文档。

## 2026-11-03

- 根据 Marketplace 预检反馈，在 `manifest.yaml` 顶层补充维护联系邮箱 `support@glorycloud.com`。
- 重新生成并核对 `glorycloud-serp-api-0.0.1.difypkg`。
