# API Docs

基础地址：`http://127.0.0.1:8000`

FastAPI 也会自动生成：

- Swagger UI: `/docs`
- ReDoc: `/redoc`

## 1. 添加图片

- 方法：`POST`
- 路径：`/api/images`
- Content-Type：`multipart/form-data`

表单字段：

- `name`: 图片名称，必填
- `file`: 图片文件，必填

响应示例：

```json
{
  "id": 1,
  "name": "black-wallet",
  "filename": "wallet.jpg",
  "file_url": "/uploads/9e4e.../wallet.jpg",
  "status": "pending",
  "embedding_elapsed_ms": null,
  "error_message": null,
  "created_at": "2026-03-16T16:40:00",
  "updated_at": "2026-03-16T16:40:00"
}
```

说明：

- 接口会先保存记录和文件，再异步生成 embedding
- 可通过查询列表或模型状态接口看到是否已经变成 `ready`

## 2. 删除图片

- 方法：`DELETE`
- 路径：`/api/images/{image_id}`

响应示例：

```json
{
  "success": true,
  "message": "Image deleted."
}
```

## 3. 文本搜索图片

- 方法：`POST`
- 路径：`/api/images/search`
- Content-Type：`application/x-www-form-urlencoded` 或 `multipart/form-data`

字段：

- `query`: 文本查询，必填
- `top_k`: 返回数量，选填，默认 5

响应示例：

```json
{
  "status": "success",
  "query_status": "ready",
  "elapsed_ms": 123.45,
  "embedding_ms": 98.76,
  "retrieval_ms": 24.69,
  "results": [
    {
      "id": 1,
      "name": "black-wallet",
      "filename": "wallet.jpg",
      "file_url": "/uploads/9e4e.../wallet.jpg",
      "score": 0.9321,
      "status": "ready"
    }
  ]
}
```

## 4. 查询图片列表

- 方法：`GET`
- 路径：`/api/images`

用于查看当前库中的图片及其处理状态。

## 5. 查询模型状态

- 方法：`GET`
- 路径：`/api/model/status`

响应示例：

```json
{
  "backend": "local_huggingface_qwen",
  "repo_id": "Qwen/Qwen3-VL-Embedding-2B",
  "configured_device": "cpu",
  "actual_device": "cpu",
  "loaded": true,
  "healthy": true,
  "busy": false,
  "message": "Model is ready."
}
```

## 状态码约定

- `200`: 成功
- `201`: 创建成功
- `404`: 资源不存在
- `422`: 参数校验失败
- `500`: 模型或存储层处理失败
