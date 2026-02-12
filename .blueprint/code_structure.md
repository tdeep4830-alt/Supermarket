# 代碼結構規範 (Code Structure Blueprint) - Online Supermarket

## 1. 專案目錄組織 (Project Layout)
採用功能模組化 (Feature-based) 與職責分離架構：

```text
/
├── .blueprint/             # 專案憲法目錄
├── .github/workflows/      # CI/CD (Automated Testing) 腳本
├── src/                    # 源代碼根目錄
│   ├── manage.py
│   ├── core/               # 專案核心配置 (Settings, WSGI, ASGI)
│   ├── common/             # 通用工具、Base Models、Middleware
│   ├── apps/               # 業務邏輯模組
│   │   ├── products/       # 商品與庫存
│   │   ├── orders/         # 訂單、優惠碼與支付
│   │   ├── users/          # 會員與積分
│   │   └── delivery/       # 配送時段管理
│   └── templates/          # 全局模板 (若為前後端分離則僅留 API 目錄)
├── tests/                  # 全局測試目錄 (或放在各 App 內)
├── Dockerfile
└── docker-compose.yml
```

## 2. 應用程式內部結構 (Deep Dive into App Layers)
每個 App 必須嚴格遵守「單一職責原則」，邏輯流向為：`View -> Service -> Model` 或 `View -> Selector -> Model`。

- **`models.py` (The Schema)**:
    - 只負責數據定義、`Meta` 配置及 `__str__` 方法。
    - 嚴禁在 Model 中寫 `save()` 重寫邏輯來處理業務（避免 Side Effects 不可控）。
    - 複雜的 QuerySet 邏輯應封裝在自定義的 `models.QuerySet` 類別中。

- **`services.py` (The Command Center - Write Actions)**:
    - **原則**：一個 Service 函數代表一個「原子操作」。
    - **職責**：處理商業邏輯、跨 App 調用、發送通知、寫入數據庫。
    - **範例**：`place_order_service(user, items, coupon_code)` 內部需處理校驗、扣庫存、應用優惠碼、建立訂單等。
    - **要求**：必須使用 `transaction.atomic` 確保數據一致性。

- **`selectors.py` (The Query Engine - Read Actions)**:
    - **職責**：所有從數據庫「拿資料」的邏輯。
    - **範例**：`get_available_products_for_user(user)` 或 `get_order_summary_report(date_range)`。
    - **好處**：當 Query 變複雜（例如需要大量的 `annotate` 或 `select_related`）時，不會污染 View。

- **`views.py` (The Entry Point)**:
    - **職責**：參數校驗（Request Validation）、調用 Service/Selector、處理 HTTP 狀態碼。
    - **要求**：單個 View 函數原則上不超過 15 行。

---

## 3. 編碼與命名規範 (Coding Standards & Typing)
- **Type Hinting**: 所有函數必須標註類型。
    - *Bad*: `def process(data):`
    - *Good*: `def process_payment(amount: Decimal, currency: str) -> bool:`
- **Constants**: 所有硬編碼（如訂單狀態、分頁數量）必須定義在 `constants.py` 或 Model 的 `Choices` 中。
- **Docstrings**: 複雜的 Service 邏輯必須包含 Google Style Docstring，解釋邏輯流程與可能拋出的異常。

---

## 4. 錯誤處理與日誌 (Observability Implementation)
- **Business Exceptions**: 建立 `apps.common.exceptions` 基類。
    - 業務錯誤拋出自定義異常（如 `InsufficientStockException`），而非直接回傳 `None` 或 `False`。
- **Structured Logging (核心機制)**:
    - 使用 `logger.bind(request_id=...)` 紀錄上下文。
    - **關鍵點**：在 `services.py` 的開始、成功結束、以及 `except` 塊中必須埋點。
    - **警報**：對於「支付失敗」或「庫存異常」等關鍵錯誤，需使用 `logger.error` 以觸發 Sentry 報警。

---

## 5. 測試規範 (Automated Testing Strategy)
- **測試隔離**:
    - 使用 `@pytest.mark.django_db` 進行數據庫測試。
    - 涉及 Redis 或第三方支付時，必須使用 `unittest.mock` 或 `pytest-mock`。
- **搶購併發測試 (Concurrency Test)**:
    - **做法**：在 Unit Test 中啟動多個 `threading.Thread` 同時呼叫 `decrease_stock_service`，驗證最後庫存是否正確且無負數。
- **測試結構**:
    ```text
    tests/
    ├── unit/          # 測試單一 Service 函數
    ├── integration/   # 測試 API 完整流程
    └── concurrency/   # 專門測試搶購鎖機制
    ```

---

## 6. 完工定義 (Definition of Done - DoD)
在 AI 完成任務並提交 Code 之前，必須自檢並在回覆中確認：
1.  **Static Analysis**: 是否通過了 `Ruff` 或 `Flake8` 的語法檢查？
2.  **Automated Tests**: 是否至少包含一個 Success Path 和兩個 Edge Case (如庫存不足、優惠碼過期) 的測試？
3.  **Observability**: 邏輯路徑中是否有足夠的日誌紀錄？
4.  **Security**: 是否有處理權限校驗（例如：用戶 A 不能看用戶 B 的訂單）？
5.  **Blueprint Alignment**: 是否有任何代碼違反了 `data.md` 或 `infra.md` 的定義？