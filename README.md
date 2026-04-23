# line_bot_translate

一個用於示範如何將 LINE Bot 訊息進行翻譯的簡易範例應用。

## 專案說明

此專案包含一個簡單的 Python LINE Bot 範例，會接收來自 LINE 的事件並做翻譯處理（範例程式可在 `app.py` 中找到）。此專案同時提供 Dockerfile 與 `docker-compose.yml`，方便在容器中執行。

## 專案結構

- [app.py](app.py)
- [requirements.txt](requirements.txt)
- [Dockerfile](Dockerfile)
- [docker-compose.yml](docker-compose.yml)

## 快速開始（本地）

建議使用虛擬環境：

```powershell
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# 或在 cmd: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

啟動後，依 `app.py` 設定的監聽埠（預設 8000 或專案內設定）訪問或讓 LINE webhook 指向該位址。

## 使用 Docker

使用 Docker 建置並在容器中執行：

```bash
docker build -t line_bot_translate .
docker run --env-file .env -p 8000:8000 line_bot_translate
```

或使用 docker-compose：

```bash
docker-compose up --build
```

## 環境變數範例（在專案根目錄建立 `.env`）

```env
LINE_CHANNEL_SECRET=your_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token
PORT=8000
```

請依 `app.py` 的實作與您 LINE 開發者設定填入實際值。

## 開發與測試

- 編輯 `app.py` 實作機器人邏輯與翻譯功能。
- 使用 `requirements.txt` 管理相依套件。

## 貢獻

歡迎提出 Issue 或 Pull Request。簡單來說：

1. Fork 此專案
2. 新增分支修正或新增功能
3. 發送 PR

## 授權

MIT License
