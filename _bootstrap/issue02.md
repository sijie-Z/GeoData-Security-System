## 问题

`/api/raster_tiles/...` 挂了 `@jwt_required()`，但浏览器端 OpenLayers 以裸 XYZ URL（`ol/layer/Tile` + `ol/source/XYZ`）加载瓦片，图片请求不会携带 `Authorization` 头——前端始终收到 401，瓦片预览不可用。

## 现状

- 后端：JWT 仅从 Authorization 头读取（未启用 cookie 或查询参数传递方案）。
- 前端：`RasterWatermarkEmbedding` 等页面直接以 `/api/raster_tiles/...` 作为 XYZ 图层 URL，请求不经过 axios 拦截器，未附加 token。

## 建议方向（可择一或组合，建议结合瓦片服务整体改造一并设计，避免二次返工）

1. 瓦片端点支持短时效签名 URL（token 以查询参数携带，仅对该端点生效）；
2. 或让 JWT 支持从安全 cookie 读取（需整体评估 CSRF 策略）；
3. 结合"按需动态出图"的瓦片服务改造统一设计前端接入方式。
