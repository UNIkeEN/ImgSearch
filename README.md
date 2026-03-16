# Lost and Found Image Search

本项目提供一个本地 Python 服务端，用于失物招领场景下的图片入库、删除和语义搜索。

核心能力：

- FastAPI RESTful API
- SQLite 存储图片元信息、文件路径、embedding、处理状态
- 基于 Hugging Face 下载并加载 `Qwen/Qwen3-VL-Embedding-2B`
- 通过配置切换到 `8B` 或其他兼容模型
- 对模型调用做了抽象，未来可替换为云端 embedding 服务
- Gradio 页面用于操作添加图片、删除图片、搜索图片

## Quick Start

1. 创建 conda 环境并安装依赖：

```bash
conda create -n imgsearch python=3.11 -y
conda activate imgsearch
pip install -U pip
pip install -e .
```

2. 复制配置：

```bash
cp .env.example .env
```

3. 启动服务：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. 访问：

- OpenAPI Docs: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Gradio: `http://127.0.0.1:8000/gradio`

## Model Notes

- 默认模型：`Qwen/Qwen3-VL-Embedding-2B`
- 切换模型时，仅需修改 `.env` 中的 `MODEL_REPO_ID`
- 当前实现会使用 `huggingface_hub.snapshot_download(...)` 下载模型仓库，然后按模型卡暴露的 `Qwen3VLEmbedder` 接口进行本地加载
- 由于 Qwen3-VL Embedding 仓库依赖远程代码，默认启用了 `TRUST_REMOTE_CODE=true`
- 已提供 `cloud_stub` backend 占位实现，未来接云端模型时优先替换 `app/services/model_backends/` 下的实现

如果后续切换为云端模型，可以只替换 `app/services/model_backends/` 下的 backend 实现，不需要改 API 层。

## Processing Status

图片记录状态：

- `pending`: 已创建，等待处理
- `processing`: 正在计算 embedding
- `ready`: embedding 已可搜索
- `failed`: 处理失败
- `deleted`: 已删除

## API Summary

详细接口说明见 [docs/api.md](/Users/unicorn/code/Projects/Toys/ImgSearch/docs/api.md)。
