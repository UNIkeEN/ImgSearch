# Lost and Found Image Search

本项目提供一个本地 Python 服务端，用于失物招领场景下的图片入库、删除和语义搜索。

核心能力：

- FastAPI RESTful API
- SQLite 存储图片元信息、文件路径、embedding、处理状态
- 基于 Hugging Face 下载并加载 `Qwen/Qwen3-VL-Embedding-2B`
- 通过配置切换到 `8B` 或其他兼容模型
- 对模型调用做了抽象，未来可替换为云端 embedding 服务
- Gradio 页面用于操作添加图片、删除图片、文本搜索图片

## Quick Start

1. 创建 conda 环境并安装依赖：

```bash
conda create -n imgsearch python=3.11 -y
conda activate imgsearch
pip install -U pip
pip install -e .
```

如果你之前已经装过旧版本依赖，先升级关键包：

```bash
pip install -U "transformers>=4.57.0" "qwen-vl-utils>=0.0.14" "torch>=2.8.0"
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
- 当前实现默认只从本地 Hugging Face 缓存读取模型；如果你已经提前下载好模型，不会再主动联网探测
- 也可以通过 `.env` 中的 `MODEL_LOCAL_PATH` 直接指定模型目录
- 当前 Qwen 适配层优先按官方 `Qwen3VLEmbedder.process([{...}])` 接口调用文本和图片 embedding
- 为兼容不同版本的 Qwen 远程代码，加载逻辑会优先尝试最小构造参数，再在实例创建后迁移到目标设备
- 服务启动时会主动预加载模型；如果预加载失败，服务仍会启动，但可通过 `/api/model/status` 查看失败信息
- 预加载成功后，服务启动阶段会自动重试数据库中所有 `pending` 和 `failed` 的图片 embedding
- 由于 Qwen3-VL Embedding 仓库依赖远程代码，默认启用了 `TRUST_REMOTE_CODE=true`
- 已提供 `cloud_stub` backend 占位实现，未来接云端模型时优先替换 `app/services/model_backends/` 下的实现
- Qwen 官方模型卡当前给出的依赖要求是 `transformers>=4.57.0`、`qwen-vl-utils>=0.0.14`、`torch==2.8.0`
- 关键模型加载、embedding 失败、启动重试等日志会直接输出到 uvicorn 日志

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

## Current Behavior

- 添加图片：上传图片后异步生成图片 embedding
- 搜索图片：当前为“文本搜图”，即输入文字查询，返回语义最接近的已入库图片
