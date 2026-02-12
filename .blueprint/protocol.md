# 專案開發協議 (Project Development Protocol) - Online Supermarket

## 1. 核心開發哲學
- **穩定優先**：由於涉及電商交易與搶購場景，代碼必須具備防禦性（Defensive Programming）。
- **架構對齊**：所有 Feature 開發前，必須確保符合 Infrastructure (PaaS/Render) 與 Data Structure 的限制。
- **一致性**：無論是誰（AI 或人類）編寫，代碼風格、目錄結構與錯誤處理必須完全統一。

## 2. 三位一體技術規範 (The Trinity)

### A. Infrastructure (基礎設施)
- **Schema First**: 建立及修改任何 Inrasturcture 之前，必須先更新 `.blueprint/infra.md` 。
- **Language/Framework**: Python 3.12+ / Django 5.0+
- **Database**: PostgreSQL (SQL 格式，託管於 Render 或相關 PaaS)
- **Deployment**: 必須提供 `Dockerfile` 與 `docker-compose.yml`。
- **PaaS (Render)**: 考慮 Render 的 Instance 限制，避免在 Web 服務中執行長時間阻塞任務。
- **高併發預備**: 
  - 搶購邏輯必須考慮「資料庫鎖 (Database Locking)」或「原子操作 (Atomic Operations)」，防止超賣。
  - 靜態資源必須考慮使用 CDN 或 Django 的 WhiteNoise。

### B. Data Structure (數據規範)
- **Schema First**: 修改任何 Table 之前，必須先更新 `.blueprint/data.md` 並生成 Django Migrations。
- **Naming**: 資料表使用蛇形命名 (snake_case)，Django Model 類別使用大駝峰 (PascalCase)。
- **Integrity**: 強制使用 ForeignKey 約束，重要金額欄位必須使用 `DecimalField` 而非 `FloatField`。

### C. Code Structure (代碼規範)
- **Schema First**: 新增或修改任何Feature 之前，必須先更新 `.blueprint/code_sturcture.md` 。
- **Testing**: 
  - 每個邏輯變更必須附帶 `tests.py`。
  - 搶購等核心邏輯必須包含「併發模擬測試 (Concurrency Unit Tests)」。
- **CI/CD**: 代碼提交前必須通過 Linting (Ruff/Flake8) 與已有的單元測試。

## 3. 強制工作流程 (The Mandatory Workflow)

每當接收到新功能請求（Feature Request）時，Claude 必須執行以下步驟：

### 第一階段：分析與讀取
1. 讀取 `.blueprint/` 下所有 md 文件。
2. 掃描當前目錄結構，確認相關的 Django App 和 Model。

### 第二階段：提交「開發提案」(Development Proposal)
在動手寫代碼前，**必須**輸出以下格式的報告並暫停：

> ### 🛠 開發提案：[功能名稱]
> - **規範參考**: (例如：參考了 Infra 中的高併發處理與 Data 中的庫存 Schema)
> - **實作邏輯**: (簡述你打算如何寫這段 Code，例如：使用 `select_for_update()` 處理搶購)
> - **影響範圍**: (哪些 Files 會被修改或新增)
> - **測試計畫**: (預計新增哪些 Unit Test 來驗證邏輯正確性)
> - **Docker/CI 改動**: (是否需要更新 Dockerfile 或環境變數)

### 第三階段：獲取確認
- 必須等待用戶回覆「Go」或「批准」後，才開始輸出代碼。

### 第四階段：執行與交付
- 輸出的代碼必須包含完整的 Docstring 註解。
- 必須同時提供 `tests.py` 的代碼片段。

## 4. 異常處理規範
- 所有 API 回傳必須包含標準化的 Error Response。
- 搶購失敗（庫存不足）與系統錯誤（DB 逾時）必須有明確的區分。

---
*本協議為本專案最高準則，AI 助手在任何情況下不得擅自跳過「提案階段」。*