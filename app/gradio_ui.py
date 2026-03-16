from pathlib import Path

import gradio as gr
import requests


def build_gradio_app(api_base_url: str) -> gr.Blocks:
    with gr.Blocks(title="Lost and Found Image Search") as demo:
        gr.Markdown(
            """
            # Lost and Found Image Search
            使用这个页面操作本地 RESTful API：添加图片、删除图片、搜索图片。
            """
        )

        with gr.Tab("添加图片"):
            name_input = gr.Textbox(label="图片名称")
            file_input = gr.File(label="上传图片", type="filepath")
            add_output = gr.JSON(label="API Response")

            def add_image(name: str, file_path: str):
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

            def delete_image(image_id: float):
                response = requests.delete(f"{api_base_url}/api/images/{int(image_id)}", timeout=300)
                return response.json()

            gr.Button("调用删除 API").click(delete_image, delete_id_input, delete_output)

        with gr.Tab("搜索图片"):
            search_file_input = gr.File(label="上传查询图片", type="filepath")
            top_k_input = gr.Slider(label="Top K", minimum=1, maximum=20, step=1, value=5)
            search_output = gr.JSON(label="API Response")

            def search_image(file_path: str, top_k: int):
                with open(file_path, "rb") as file_obj:
                    response = requests.post(
                        f"{api_base_url}/api/images/search",
                        data={"top_k": str(top_k)},
                        files={"file": (Path(file_path).name, file_obj, "application/octet-stream")},
                        timeout=300,
                    )
                return response.json()

            gr.Button("调用搜索 API", variant="primary").click(search_image, [search_file_input, top_k_input], search_output)

        with gr.Tab("状态"):
            model_output = gr.JSON(label="模型状态")
            list_output = gr.JSON(label="图片列表")

            def fetch_model_status():
                return requests.get(f"{api_base_url}/api/model/status", timeout=300).json()

            def fetch_images():
                return requests.get(f"{api_base_url}/api/images", timeout=300).json()

            gr.Button("刷新模型状态").click(fetch_model_status, outputs=model_output)
            gr.Button("刷新图片列表").click(fetch_images, outputs=list_output)

    return demo
