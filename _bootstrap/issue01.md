## 问题

`GET /api/raster_tiles/<data_id>/<z>/<x>/<y>.png` 对通过认证的请求永远返回 404，即使瓦片已由上传流程生成。

## 根因

- 生成端 `generate_raster_tiles()`（testrealend/resource/raster_resource.py）把瓦片写为嵌套目录：
  `<UPLOAD_FOLDER>/tiles/<data_id>/<z>/<x>/<y>.png`
- 读取端 `RasterTilesResource.get` 按平铺文件名查找：
  `<UPLOAD_FOLDER>/tiles/<data_id>/{z}_{x}_{y}.png`

两边命名规则不一致，匹配永远失败。该问题在 v2.4.0 之前即已存在，并非近期改动引入。

## 影响

栅格瓦片预览（例如栅格水印嵌入页的地图预览）无法加载瓦片。
注：即使路径对齐，浏览器端仍有一个独立的鉴权问题（瓦片端点挂在 JWT 校验下，而前端以裸 XYZ URL 加载瓦片）——另行跟踪。

## 修复

见对应 PR：读取端对齐生成端的嵌套路径，并新增回归测试。
