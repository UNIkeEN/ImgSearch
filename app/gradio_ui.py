from html import escape
from pathlib import Path

import gradio as gr
import requests


def _api_base_from_request(request: gr.Request | None) -> str:
    if request is None:
        return "http://127.0.0.1:8000"
    return str(request.request.base_url).rstrip("/")


def _build_cards(items: list[dict], api_base_url: str, show_score: bool = False) -> str:
    if not items:
        return "<div style='padding:16px;border:1px dashed #cbd5e1;border-radius:16px;color:#475569;'>暂无数据</div>"

    cards = []
    for item in items:
        image_url = f"{api_base_url}{item['file_url']}"
        score_html = ""
        if show_score and item.get("score") is not None:
            score_html = f"<div><strong>相似度:</strong> {float(item['score']):.4f}</div>"
        error_html = ""
        if item.get("error_message"):
            error_html = f"<div style='color:#b91c1c;'><strong>错误:</strong> {escape(str(item['error_message']))}</div>"

        cards.append(
            f"""
            <div style="display:flex;gap:16px;padding:16px;border:1px solid #dbe4ee;border-radius:18px;background:#fff;box-shadow:0 10px 30px rgba(15,23,42,.06);">
              <img src="{escape(image_url)}" alt="{escape(item['name'])}" style="width:120px;height:120px;object-fit:cover;border-radius:14px;background:#f8fafc;border:1px solid #e2e8f0;" />
              <div style="flex:1;min-width:0;">
                <div style="font-size:18px;font-weight:700;color:#0f172a;margin-bottom:8px;">{escape(item['name'])}</div>
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;font-size:14px;color:#334155;">
                  <div><strong>ID:</strong> {item['id']}</div>
                  <div><strong>状态:</strong> {escape(str(item['status']))}</div>
                  <div><strong>文件名:</strong> {escape(item['filename'])}</div>
                  {score_html}
                </div>
                {error_html}
              </div>
            </div>
            """
        )

    return (
        "<div style='display:grid;gap:14px;background:linear-gradient(180deg,#f8fafc 0%,#eef2ff 100%);padding:12px;border-radius:20px;'>"
        + "".join(cards)
        + "</div>"
    )


def build_gradio_app() -> gr.Blocks:
    with gr.Blocks(title="Lost and Found Image Search") as demo:
        gr.Markdown(
            """
            # Lost and Found Image Search
            使用这个页面操作本地 RESTful API：添加图片、删除图片、文本搜索图片。
            """
        )

        with gr.Tab("添加图片"):
            name_input = gr.Textbox(label="图片名称")
            file_input = gr.File(label="上传图片", type="filepath")
            add_output = gr.JSON(label="API Response")

            def add_image(name: str, file_path: str | None, request: gr.Request):
                if not name.strip():
                    return {"detail": "name is required"}
                if not file_path:
                    return {"detail": "file is required"}
                api_base_url = _api_base_from_request(request)
                with open(file_path, "rb") as file_obj:
                    response = requests.post(
                        f"{api_base_url}/api/images",
                        data={"name": name},
                        files={"file": (Path(file_path).name, file_obj, "application/octet-stream")},
                        timeout=300,
                    )
                return response.json()

            gr.Button("调用添加 API", variant="primary").click(add_image, [name_input, file_input], add_output)

        with gr.Tab("删除图片"):
            delete_id_input = gr.Number(label="图片 ID", precision=0)
            delete_output = gr.JSON(label="API Response")

            def delete_image(image_id: float | None, request: gr.Request):
                if image_id is None:
                    return {"detail": "image_id is required"}
                api_base_url = _api_base_from_request(request)
                response = requests.delete(f"{api_base_url}/api/images/{int(image_id)}", timeout=300)
                return response.json()

            gr.Button("调用删除 API").click(delete_image, delete_id_input, delete_output)

        with gr.Tab("文本搜索"):
            query_input = gr.Textbox(label="搜索文本", lines=3, placeholder="例如：黑色钱包、带钥匙扣的蓝色书包")
            top_k_input = gr.Slider(label="Top K", minimum=1, maximum=20, step=1, value=5)
            search_cards = gr.HTML(label="搜索结果")
            search_output = gr.JSON(label="API Response")

            def search_image(query_text: str, top_k: int, request: gr.Request):
                if not query_text.strip():
                    payload = {"detail": "query is required"}
                    return "<div style='color:#b91c1c;'>请输入搜索文本</div>", payload
                api_base_url = _api_base_from_request(request)
                response = requests.post(
                    f"{api_base_url}/api/images/search",
                    data={"query": query_text, "top_k": str(top_k)},
                    timeout=300,
                )
                payload = response.json()
                results = payload.get("results", []) if isinstance(payload, dict) else []
                return _build_cards(results, api_base_url, show_score=True), payload

            gr.Button("调用搜索 API", variant="primary").click(
                search_image,
                [query_input, top_k_input],
                [search_cards, search_output],
            )

        with gr.Tab("状态"):
            model_output = gr.JSON(label="模型状态")
            list_cards = gr.HTML(label="图片列表")
            list_output = gr.JSON(label="图片列表 JSON")

            def fetch_model_status(request: gr.Request):
                api_base_url = _api_base_from_request(request)
                return requests.get(f"{api_base_url}/api/model/status", timeout=300).json()

            def fetch_images(request: gr.Request):
                api_base_url = _api_base_from_request(request)
                payload = requests.get(f"{api_base_url}/api/images", timeout=300).json()
                return _build_cards(payload, api_base_url, show_score=False), payload

            gr.Button("刷新模型状态").click(fetch_model_status, outputs=model_output)
            gr.Button("刷新图片列表").click(fetch_images, outputs=[list_cards, list_output])

    return demo
