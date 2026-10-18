# 各大指數高低控統整系統 (TAIEX / DJI / NASDAQ / SOX) — GitHub Pages 直接部署與每日自動更新套件

本套件將 **集中市場加權指數 (TAIEX)**、**道瓊工業平均指數 (DJI)**、**那斯達克綜合指數 (NASDAQ)** 與 **費城半導體指數 (SOX)** 四套多週期（日/周/月）與跨週期前瞻雙軌通道分析系統完整整合於同一個入口網頁 (`index.html`)：
- **第一頁面（入口總覽頁）**：最上端可選擇切換 `入口總覽`、`TAIEX`、`DJI`、`NASDAQ` 或 `SOX`；下方垂直排列展示 **4 個指數的「跨週期融合走勢圖 (日K + 日/周/月 六大通道線)」**（不含 Raw Data 表格），支援使用滑鼠滾輪直接上下滑動一次瀏覽四大指數跨週期走勢。
- **各指數獨立完整頁**：點選最上端的 `TAIEX`、`DJI`、`NASDAQ` 或 `SOX` 按鍵後，進入的頁面即為各指數原有的獨立網頁，完整保留 `🌐 跨週期融合 (日/周/月)`、`📅 日 K 線`、`📊 周 K 線`、`🗓️ 月 K 線` 四大切換按鍵、KPI 指標卡、次期前瞻預測卡、CSV 匯出與歷史明細數據表（Raw Data）。

---

## 📁 套件檔案結構
- `index.html`：GitHub Pages 預設首頁（即整合版入口網頁，部署後開啟 GitHub 網址即可直接瀏覽）。
- `各大指數高低控統整_多週期與跨週期前瞻雙軌通道分析系統.html`：與 `index.html` 完全相同之中文檔名備份，方便本機電腦直接使用 Google Chrome 點擊開啟。
- `.nojekyll`：告知 GitHub Pages 直接以純靜態網頁高速發佈，免除 Jekyll 編譯等待。
- `data/TAIEX/`、`data/DJI/`、`data/NASDAQ/`、`data/SOX/`：四大指數各自的 `raw_daily.csv`、`raw_weekly.csv`、`raw_monthly.csv` 歷史與最新收盤資料庫。
- `update_all_indices.py`：每日自動抓取四大指數最新盤後數據、更新日/周/月 CSV、重新計算 12 期滾動雙軌與 11 期次期前瞻雙軌，並自動寫回 `index.html` 的核心引擎。
- `.github/workflows/daily_update.yml`：GitHub Actions 自動排程設定檔（每個交易日台灣時間 14:35 台股盤後、以及清晨 05:30 美股盤後自動執行更新並推播至 GitHub Pages）。
- `send_email_report.py`：每日盤後自動寄送 HTML 報告附件至指定雙信箱之腳本。
- `requirements.txt`：Python 套件清單（`requests`、`pandas`、`numpy`）。

---

## 🚀 手把手教學：直接部署在 GitHub Pages（使用 GitHub 官方網址，免透過 Netlify）

### 步驟一：在 GitHub 建立新的儲存庫 (Repository)
1. 登入您的 [GitHub](https://github.com/) 帳號，點擊右上角的 **`+`** 號 ➔ 選擇 **`New repository`**。
2. **Repository name（儲存庫名稱）**：輸入您喜歡的英文名稱，例如 `major-indices-channel`（這會成為您之後 GitHub 網址的一部分）。
3. **Public / Private**：請務必選擇 **`Public`（公開）**（GitHub 免費版帳號需設為 Public 才能免費開啟 GitHub Pages 網頁與無限使用 GitHub Actions 自動更新）。
4. 勾選 **`Add a README file`**，然後點擊最下方的綠色按鈕 **`Create repository`**。

### 步驟二：上傳本套件所有檔案至 GitHub
1. 將您下載的 `各大指數高低控統整_GitHub_Pages每日自動更新部署套件.zip` 在電腦上**解壓縮**。
2. 進入剛剛建立好的 GitHub 儲存庫頁面，點擊上方的 **`Add file`** ➔ **`Upload files`**。
3. 將解壓縮出來的所有檔案與資料夾（包含 `index.html`、`data` 資料夾、`update_all_indices.py`、`send_email_report.py`、`requirements.txt`、`.nojekyll`）**全部拖曳到上傳框中**。
   > 💡 **注意隱藏資料夾 `.github`**：Windows / Mac 若沒顯示 `.github` 資料夾，或是拖曳時漏掉 `.github/workflows/daily_update.yml`，您也可以在上傳完成後，點選儲存庫上方的 **`Actions`** 頁籤 ➔ 點擊 **`set up a workflow yourself`**，將檔名改為 `daily_update.yml`，並把套件內 `.github/workflows/daily_update.yml` 的內容貼上後點擊右上角 **`Commit changes...`** 即可！
4. 在頁面下方點擊綠色按鈕 **`Commit changes`** 完成上傳。

### 步驟三：開啟 GitHub Actions 自動寫入權限（讓系統能每日自動更新網頁）
1. 在您的 GitHub 儲存庫頁面，點擊最上方的 **`Settings`（設定）**。
2. 在左側選單展開 **`Actions`** ➔ 點擊 **`General`**。
3. 往下滑動找到 **`Workflow permissions`（工作流程權限）**：
   - 改勾選 **`Read and write permissions`（讀取與寫入權限）**。
   - 點擊下方的 **`Save`** 按鈕儲存。

### 步驟四：啟用 GitHub Pages（取得您的專屬 GitHub 網址！）
1. 同樣在 **`Settings`（設定）** 頁面，點擊左側選單的 **`Pages`**。
2. 在 **`Build and deployment`** 區塊下的 **`Source`**：
   - 維持選擇 **`Deploy from a branch`**。
3. 在 **`Branch`（分支）** 下拉選單：
   - 第一個選單將 `None` 改選為 **`main`**。
   - 第二個選單維持 **`/ (root)`**。
   - 點擊旁邊的 **`Save`** 按鈕。
4. 等待約 **30 秒至 1 分鐘** 後，重新整理該 `Pages` 設定頁面，畫面上方就會出現一行提示：
   > **Your site is live at `https://<您的GitHub帳號>.github.io/major-indices-channel/`**
5. 點擊該網址，就能在電腦或手機瀏覽器直接開啟您的「各大指數高低控統整系統」！把這個網址加入書籤即可永久使用，完全不需要透過 Netlify！

### 步驟五：立刻手動測試一次自動更新（確認每日排程運作正常）
1. 點擊儲存庫最上方的 **`Actions`** 頁籤。
2. 點擊左側的 **`Daily Major Indices Auto Update & GitHub Pages Deploy`**。
3. 點擊右側的 **`Run workflow`** 下拉按鈕 ➔ 點擊綠色 **`Run workflow`**。
4. 約 20～30 秒後顯示綠色勾勾 `✅`，代表系統已成功連線抓取台股與美股四大指數最新盤後收盤價、更新 `data/` 與 `index.html`，並自動發佈到您的 GitHub Pages 網址！
   - 之後每個交易日 **台灣時間 14:35（台股收盤後）** 與 **清晨 05:30（美股收盤後）**，GitHub Actions 都會全自動執行更新，GitHub 網址打開永遠是最新資料！
