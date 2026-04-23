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
    TextMessage
)
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

TRANSLATION_PROMPTS = {
    "中翻日": {
        "name": "Chinese to Japanese",
        "system": "You are a professional Traditional Chinese (zh-TW) to Japanese (ja-JP) translator. Your goal is to accurately convey the meaning and nuances of the original Traditional Chinese text while adhering to Japanese grammar, vocabulary, and cultural sensitivities. Produce only the Japanese translation, without any additional explanations or commentary. Please translate the following Traditional Chinese text into Japanese:"
    },
    "日翻中": {
        "name": "Japanese to Chinese",
        "system": "You are a professional Japanese (ja-JP) to Traditional Chinese (zh-TW) translator. Your goal is to accurately convey the meaning and nuances of the original Japanese text while adhering to Traditional Chinese grammar, vocabulary, and cultural sensitivities. Produce only the Traditional Chinese translation, without any additional explanations or commentary. Please translate the following Japanese text into Traditional Chinese:"
    },
    "韓翻中": {
        "name": "Korean to Chinese", 
        "system": "You are a professional Korean (ko-KR) to Traditional Chinese (zh-TW) translator. Your goal is to accurately convey the meaning and nuances of the original Korean text while adhering to Traditional Chinese grammar, vocabulary, and cultural sensitivities. Produce only the Traditional Chinese translation, without any additional explanations or commentary. Please translate the following Korean text into Traditional Chinese:"
    },
    "中翻韓": {
        "name": "Chinese to Korean",
        "system": "You are a professional Traditional Chinese (zh-TW) to Korean (ko-KR) translator. Your goal is to accurately convey the meaning and nuances of the original Traditional Chinese text while adhering to Korean grammar, vocabulary, and cultural sensitivities. Produce only the Korean translation, without any additional explanations or commentary. Please translate the following Traditional Chinese text into Korean:"
    },
    "中翻西": {
        "name": "Chinese to Spanish",
        "system": "You are a professional Traditional Chinese (zh-TW) to Spanish (es-ES) translator. Your goal is to accurately convey the meaning and nuances of the original Traditional Chinese text while adhering to Spanish grammar, vocabulary, and cultural sensitivities. Produce only the Spanish translation, without any additional explanations or commentary. Please translate the following Traditional Chinese text into Spanish:"
    },
    "西翻中": {
        "name": "Spanish to Chinese",
        "system": "You are a professional Spanish (es-ES) to Traditional Chinese (zh-TW) translator. Your goal is to accurately convey the meaning and nuances of the original Spanish text while adhering to Traditional Chinese grammar, vocabulary, and cultural sensitivities. Produce only the Traditional Chinese translation, without any additional explanations or commentary. Please translate the following Spanish text into Traditional Chinese:"
    }
}

async def ollama_request(text, system_prompt):
    client = ollama.Client(host=os.getenv('OLLAMA_HOST'))
    response = client.chat(model="translategemma:4b", messages = [
        {
            'role': 'system',
            'content': system_prompt
        },
        {
            'role': 'user',
            'content': text
        },
    ])
    return response['message']['content']



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
    system_prompt = TRANSLATION_PROMPTS[current_mode]['system']
    msg = asyncio.run(ollama_request(text, system_prompt))
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=msg)]
            )
        )


if __name__ == "__main__":
    app.run()