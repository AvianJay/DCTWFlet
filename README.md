# DCTW APP

亂做的 DCTW 應用程式。

## 下載最新成功構建的檔案
[Android](https://nightly.link/AvianJay/DCTWFlet/workflows/build/main/DCTWFlet-android.zip)
[iOS](https://nightly.link/AvianJay/DCTWFlet/workflows/build/main/DCTWFlet-ios.zip)
[Windows](https://nightly.link/AvianJay/DCTWFlet/workflows/build/main/DCTWFlet-windows.zip)
[macOS](https://nightly.link/AvianJay/DCTWFlet/workflows/build/main/DCTWFlet-macos.zip)
[Linux](https://nightly.link/AvianJay/DCTWFlet/workflows/build/main/DCTWFlet-linux.zip)
[Web](https://nightly.link/AvianJay/DCTWFlet/workflows/build/main/DCTWFlet-web.zip)

## 計畫列表
- [x] API Key 設定
- [x] 從剪貼簿貼上 API Key
- [x] 投票功能（機器人／伺服器／模板）
- [x] 主題選擇
- [x] 搜尋功能
- [x] 排序功能
- [x] 標籤篩選
- [x] 機器人頁面
    - [x] 狀態
    - [x] 連結按鈕
    - [x] 標籤
        - [x] 點擊標籤出現相關機器人
    - [x] 投票數
    - [ ] 留言
    - [x] 伺服器數量
    - [x] 開發人員列表（作者）
    - [x] 社群連結
- [x] 伺服器頁面
    - [x] 連結按鈕
    - [x] 標籤
        - [ ] 點擊標籤出現相關伺服器
    - [x] 投票數
    - [ ] 留言
    - [ ] 成員數量
        - [ ] 在線人數
    - [x] 社群連結
    - [ ] 功能列表
    - [ ] 管理員列表
- [x] 模板頁面
    - [x] 連結按鈕
    - [x] 標籤
        - [ ] 點擊標籤出現相關模板
    - [x] 投票數
    - [ ] 留言
    - [ ] 作者
    - [ ] 社群連結

## API Key

瀏覽機器人、伺服器與模板不需要 API Key；只有投票需要。取得方式：

1. 到 [DCTW 官網](https://dctw.xyz) 登入後，在後台「我的帳號」點擊「複製 API KEY」
2. 回到應用程式的「設定」，點擊「從剪貼簿貼上 API Key」

也可以在設定頁面手動輸入（會先向 API 驗證後才儲存）。
官方說明：[取得 API KEY](https://dctw.xyz/docs/api-key)

## 直接從原代碼執行

### 複製此存儲庫：

```
git clone https://github.com/AvianJay/DCTWFlet.git
cd DCTWFlet
```

### 安裝依賴項

```
# 創建 venv (可選)
python -m venv .venv
# 啟用 venv (可選)
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install .
```

## 直接運行應用程式

以視窗應用程式形式運行：

```
flet run
```

以網頁應用程式形式運行：

```
flet run --web
```

### uv

以視窗應用程式形式運行：

```
uv run flet run
```

以網頁應用程式形式運行：

```
uv run flet run --web
```

### Poetry

從 `pyproject.toml` 裡安裝依賴項：

```
poetry install
```

以視窗應用程式形式運行：

```
poetry run flet run
```

以網頁應用程式形式運行：

```
poetry run flet run --web
```

更多相關資訊請參考 Flet 文檔: [Getting Started Guide](https://flet.dev/docs/getting-started/).

## 構建應用程式

### Android

```
flet build apk -v
```

更多相關構建及簽名 `.apk` 或 `.aab` 的資訊，請參考 Flet 文檔 [Android Packaging Guide](https://flet.dev/docs/publish/android/).

### iOS

```
flet build ipa -v
```

更多相關構建及簽名 `.ipa` 的資訊，請參考 Flet 文檔 [iOS Packaging Guide](https://flet.dev/docs/publish/ios/).

### macOS

```
flet build macos -v
```

更多相關構建 macOS 應用程式的資訊，請參考 Flet 文檔 [macOS Packaging Guide](https://flet.dev/docs/publish/macos/).

### Linux

```
flet build linux -v
```

更多相關構建 Linux 應用程式的資訊，請參考 Flet 文檔 [Linux Packaging Guide](https://flet.dev/docs/publish/linux/).

### Windows

```
flet build windows -v
```

更多相關構建 Windows 應用程式的資訊，請參考 Flet 文檔 [Windows Packaging Guide](https://flet.dev/docs/publish/windows/).
