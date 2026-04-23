import requests
import asyncio
import ollama
from flask import Flask, request, abort

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    FlexMessage,
    FlexContainer
)
import re

from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)





from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))


@app.route("/", methods=['POST'])
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


# In-memory storage for user translation modes
user_modes = {}

SYSTEM_BASE = """你是一位精通各國口語的專業翻譯。
- 嚴禁逐字翻譯：必須使用目標語言最道地的慣用語（例：『現在幾點』翻為日文應為『今、何時ですか？』）。
- 文化常識校正：確保特定食物/名詞正確（例：『西班牙油條』是『Churros』而非炸薯條）。
- 格式限定：只輸出翻譯結果，嚴禁任何解釋或開場白。"""

FEW_SHOT_EXAMPLES = [
    {"role": "user", "content": "[中翻日] 現在幾點"},
    {"role": "assistant", "content": "今、何時ですか？"},
    {"role": "user", "content": "[中翻西] 西班牙油條"},
    {"role": "assistant", "content": "Churros"}
]

TRANSLATION_PROMPTS = {
    "中翻日": {"name": "中文 -> 日文", "prefix": "[中翻日]"},
    "日翻中": {"name": "日文 -> 中文", "prefix": "[日翻中]"},
    "韓翻中": {"name": "韓文 -> 中文", "prefix": "[韓翻中]"},
    "中翻韓": {"name": "中文 -> 韓文", "prefix": "[中翻韓]"},
    "中翻西": {"name": "中文 -> 西班牙文", "prefix": "[中翻西]"},
    "西翻中": {"name": "西班牙文 -> 中文", "prefix": "[西翻中]"}
}

def post_process_translation(text, mode):
    original_text = text.strip()
    # 移除常見的開場白
    text = re.sub(r'^(翻譯結果|譯文|Translation|結果|Output)：\s*', '', original_text, flags=re.I)

    # 若目標語言不是中文或日文，但結果包含中文，嘗試過濾掉可能的解釋
    # 因為日文包含漢字，所以中翻日不能過濾。中翻韓也建議保留，因為韓文有時使用漢字且韓文字元不在此範圍內。
    if "翻中" not in mode and "翻日" not in mode:
        # 移除包含中文的括號或後續文字 (Gemma 喜歡在後面括號解釋)
        # 例如: "Churros (西班牙油條是一種...)" -> "Churros"
        parts = re.split(r'[\(\（\s]*[\u4e00-\u9fff]+', text)
        if parts[0].strip():
            text = parts[0]
        # 如果第一部分是空的，表示開頭就是中文，那可能整句都是翻譯或是解釋放在前面，
        # 在這種情況下我們保留原狀，避免回傳空字串

    result = text.strip()
    return result if result else original_text if original_text else " "
async def ollama_request(text, mode):
    client = ollama.Client(host=os.getenv('OLLAMA_HOST'))
    mode_info = TRANSLATION_PROMPTS[mode]
    
    messages = [
        {'role': 'system', 'content': SYSTEM_BASE}
    ]
    messages.extend(FEW_SHOT_EXAMPLES)
    messages.append({
        'role': 'user',
        'content': f"{mode_info['prefix']} {text}"
    })
    
    response = client.chat(model="translategemma:4b", messages=messages)
    content = response['message']['content']
    return post_process_translation(content, mode)

def create_translation_flex_message(original, translated, mode_name):
    flex_contents = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": mode_name,
                    "weight": "bold",
                    "color": "#1DB446",
                    "size": "sm"
                },
                {
                    "type": "separator",
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "lg",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "原文",
                                    "size": "xs",
                                    "color": "#8C8C8C"
                                },
                                {
                                    "type": "text",
                                    "text": original,
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "md"
                                }
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "譯文",
                                    "size": "xs",
                                    "color": "#8C8C8C"
                                },
                                {
                                    "type": "text",
                                    "text": translated,
                                    "wrap": True,
                                    "color": "#111111",
                                    "size": "lg",
                                    "weight": "bold"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
    # 使用 from_json 需要將 dict 轉為 json string
    import json
    return FlexMessage(
        alt_text=f"翻譯結果: {translated}",
        contents=FlexContainer.from_json(json.dumps(flex_contents))
    )

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()
    
    # Check if user is switching modes
    if text in TRANSLATION_PROMPTS:
        user_modes[user_id] = text
        mode_name = TRANSLATION_PROMPTS[text]['name']
        reply_text = f"模式已切換為：{mode_name}\n請輸入要翻譯的文字。"
        
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
        return

    # Check valid mode or default
    current_mode = user_modes.get(user_id)
    if not current_mode:
        # Provide a selection menu if no mode selected
        modes_list = "\n".join(TRANSLATION_PROMPTS.keys())
        reply_text = f"請先選擇翻譯模式 (輸入以下任一指令):\n{modes_list}"
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
        return

    # Perform translation
    translated_text = asyncio.run(ollama_request(text, current_mode))
    mode_name = TRANSLATION_PROMPTS[current_mode]['name']
    
    flex_msg = create_translation_flex_message(text, translated_text, mode_name)
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[flex_msg]
            )
        )


if __name__ == "__main__":
    app.run()