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
- [ ] API Key 登入
- [x] 主題選擇
- [ ] 搜尋功能
- [x] 排序功能
- [ ] 標籤篩選
- [x] 機器人頁面
    - [x] 狀態
    - [x] 連結按鈕
    - [x] 標籤
        - [ ] 點擊標籤出現相關機器人
    - [ ] 投票數
    - [ ] 留言
    - [ ] 伺服器數量
    - [ ] 開發人員列表
    - [ ] 社群連結
- [x] 伺服器頁面
    - [x] 連結按鈕
    - [x] 標籤
        - [ ] 點擊標籤出現相關伺服器
    - [ ] 投票數
    - [ ] 留言
    - [ ] 成員數量
        - [ ] 在線人數
    - [ ] 社群連結
    - [ ] 功能列表
    - [ ] 管理員列表
- [x] 範本頁面
    - [x] 連結按鈕
    - [x] 標籤
        - [ ] 點擊標籤出現相關範本
    - [ ] 投票數
    - [ ] 留言
    - [ ] 作者
    - [ ] 社群連結

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