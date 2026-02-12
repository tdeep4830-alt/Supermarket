# 數據結構規範 (Data Structure Blueprint) - Online Supermarket

## 1. 核心實體關係 (Entity Relationship)
本專案採用 PostgreSQL，所有 Model 必須繼承 `TimeStampedModel` (紀錄 `created_at` 與 `updated_at`)。

### A. 產品與分類 (Product & Category)
- **Category**: 管理超市分類（如：新鮮蔬果、零食、日用品）。
- **Product**: 
    - `name`, `description`, `price` (DecimalField, max_digits=10, decimal_places=2)。
    - `is_active`: 布林值，用於快速下架產品。

### B. 庫存管理 (Inventory) - **搶購核心**
為了應對高併發，庫存採取獨立表設計或嚴格欄位控制：
- **Stock**:
    - `product`: OneToOne 關聯 Product。
    - `quantity`: PositiveIntegerField。
    - `version`: IntegerField (用於 **Optimistic Locking** 樂觀鎖，防止併發扣庫存出錯)。
    - **規範**: 扣減庫存時必須使用 `F()` 表達式：`Stock.objects.filter(id=id, quantity__gte=q).update(quantity=F('quantity') - q)`。

### C. 訂單系統 (Order & OrderItem)
- **Order**:
    - `user`: 關聯 User。
    - `status`: [PENDING, PAID, SHIPPED, CANCELLED, REFUNDED]。
    - `total_amount`: 總金額。
    - `payment_id`: 紀錄 PaaS/Render 環境接駁的支付憑證。
- **OrderItem**:
    - `order`, `product`, `quantity`, `price_at_purchase` (紀錄購買時的價格，防止未來調價影響歷史訂單)。

### D. 購物車 (Cart)
- 使用資料庫存儲或 Session 存儲（根據需求）。若要支持多端同步，建議使用資料庫。

### E. 優惠碼系統 (Promotion & Coupon)
- **Coupon**:
    - `code`: 唯一代碼 (如: SUPERMARKET666)，建立 `db_index`。
    - `discount_type`: [PERCENTAGE, FIXED_AMOUNT]。
    - `discount_value`: 折扣數值。
    - `min_purchase_amount`: 最低消費金額門檻。
    - `valid_from` & `valid_until`: 有效期。
    - `total_limit`: 總共可領取/使用次數。
    - `used_count`: 目前已使用次數 (配合 `F()` 表達式進行原子更新)。
    - `is_active`: 手動啟動/停用開關。

- **UserCoupon**: (紀錄用戶領取或使用狀況)
    - `user`, `coupon`, `used_at`。
    - **唯一約束**: `unique_together = ('user', 'coupon')` (防止單一用戶重複使用同一個優惠碼)。

- **規範**: 
    - 訂單必須紀錄 `applied_coupon` 和 `discount_amount`（紀錄下單當時的折扣額度，防止日後優惠碼刪除或變更導致數據不一致）。
    - 優惠碼校驗邏輯必須放在 `services.py`。
    
## 2. 高速緩存與併發層 (Redis - The Performance Layer)

為了提升響應速度及應對搶購，以下數據必須進入 Redis：

### A. 即時庫存快照 (Inventory Cache)
- **Key**: `stock:{product_id}`
- **Value**: 剩餘數量 (Integer)。
- **用途**: 搶購時，AI 必須優先扣除 Redis 裡的數量。
- **策略**: 使用 `DECRBY` 命令。當 Redis 數量扣減成功後，再異步同步回 PostgreSQL。

### B. 購物車緩存 (Shopping Cart Cache)
- **Key**: `cart:{user_id}`
- **Value**: Hash Map `{product_id: quantity}`。
- **用途**: 用戶频繁修改購物車時，不直接寫入 DB，減少 I/O。
- **過期**: 設置 7 天過期。

### C. 熱門商品與搜索建議 (Hot Products & Search)
- **Key**: `hot_products`
- **Structure**: Sorted Set (ZSET)。
- **用途**: 根據銷量或點擊量排序，首頁展示。
- **Key**: `autocomplete:{prefix}`
- **用途**: 實現搜索框的即時下拉建議。

### D. 限流與防抖 (Rate Limiting)
- **Key**: `ratelimit:order:{user_id}`
- **用途**: 限制同一用戶在 1 秒內只能提交一次訂單，防止刷單工具。

### E. 優惠碼領取狀態 (Coupon Snapshot)
- **Key**: `coupon:quota:{coupon_code}`
- **Value**: 剩餘可領取數量。
- **用途**: 高併發搶碼時，在 Redis 進行初步攔截。

## 3. 數據一致性協議 (Data Consistency)
- **Cache-Aside Pattern**: 讀取數據時，先查 Redis，若無則查 DB 並回填 Redis。
- **Write-Through/Behind**: 庫存扣減優先在 Redis 執行，成功後發送信號給後台 Task (如 Django-Q2) 更新 PostgreSQL。
- **失效機制**: 當管理台修改產品價格或資訊時，必須執行 `cache.delete(f"product:{id}")`。

## 4. 字段規範 (續)
- **金額**: 統一使用 `DecimalField` (DB) / String (Redis)。
- **ID**: 統一使用 `UUID`。

## 5. 數據操作約束 (Operational Constraints)
- **禁止邏輯**: 禁止在 View 層直接修改 `Stock.quantity`，必須透過 `services.py` 中的 `decrease_stock` 函數執行。
- **事務控制**: 涉及「創建訂單 + 扣減庫存」的操作必須包裝在 `transaction.atomic` 事務中。