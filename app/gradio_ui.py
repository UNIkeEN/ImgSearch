from pathlib import Path

import gradio as gr
import requests


def _api_base_from_request(request: gr.Request | None) -> str:
    if request is None:
        return "http://127.0.0.1:8000"
    return str(request.request.base_url).rstrip("/")


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
            search_output = gr.JSON(label="API Response")

            def search_image(query_text: str, top_k: int, request: gr.Request):
                if not query_text.strip():
                    return {"detail": "query is required"}
                api_base_url = _api_base_from_request(request)
                response = requests.post(
                    f"{api_base_url}/api/images/search",
                    data={"query": query_text, "top_k": str(top_k)},
                    timeout=300,
                )
                return response.json()

            gr.Button("调用搜索 API", variant="primary").click(search_image, [query_input, top_k_input], search_output)

        with gr.Tab("状态"):
            model_output = gr.JSON(label="模型状态")
            list_output = gr.JSON(label="图片列表")

            def fetch_model_status(request: gr.Request):
                api_base_url = _api_base_from_request(request)
                return requests.get(f"{api_base_url}/api/model/status", timeout=300).json()

            def fetch_images(request: gr.Request):
                api_base_url = _api_base_from_request(request)
                return requests.get(f"{api_base_url}/api/images", timeout=300).json()

            gr.Button("刷新模型状态").click(fetch_model_status, outputs=model_output)
            gr.Button("刷新图片列表").click(fetch_images, outputs=list_output)

    return demo
