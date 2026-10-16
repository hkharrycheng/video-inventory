# Video Inventory (J11)

HIS Tools — 影片／動畫庫助手（三 Tab 手機頁面）

## Tab 功能
1. **搜尋** — 搜尋 Video Master（1629 部影片）：Poster、評分（GPA/Grade）、DB 狀態、角色 → 演員／聲優，點擊卡片睇全部詳細資料
2. **下載中** — BT Watching 下載進度（動畫進度 bar、集數、Tier、狀態、BT／直接連結）
3. **新聞** — GNN 巴哈姆特 ACG 新聞橫卡圖庫（按平台 filter），GitHub Actions 每 6 小時自動更新 news-cache.json

## 檔案
- `index.html` — 主頁
- `videos.json` — 影片資料（由飛書 Video Master Base 生成）
- `downloads.json` — 下載進度（由 BT Watching Base 生成）
- `news-cache.json` — 新聞快取（news_mirror.py 生成）
- `news_mirror.py` — GNN 新聞爬蟲（GitHub Actions 定時跑）
- `posters/` — 影片海報縮圖
- `down_imgs/` — 下載中動畫海報縮圖

## 數據來源（飛書多維表格）
- Video Master: feishu.doubao.com/base/GBVWbrDHaa1xVbsLGOPcvSbbndg
- BT Watching: doubao.com/base/ARBFbl0TJaQ8nlsefNIcZJ1CnNd
- News Feed List: doubao.com/base/An0abQoUBalSqJsG66ucDzT3ncg

## 更新機制
- 新聞：GitHub Actions `news-cache.yml`（每 6 小時 + 手動 dispatch）自動跑 `news_mirror.py` 更新 news-cache.json
- 影片／下載 JSON：人手從多維表格重新生成上傳
