"""
Order & Coupon Models.

Ref: .blueprint/data.md §1C, §1E
- Order: 訂單主表
- OrderItem: 訂單項目（記錄購買時價格）
- Coupon: 優惠碼
- UserCoupon: 用戶優惠碼領取/使用記錄
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.products.models import Product
from common.models import TimeStampedModel


class Coupon(TimeStampedModel):
    """
    優惠碼 Model.

    Ref: data.md §1E
    - code 必須建立 db_index
    - used_count 更新必須使用 F() 表達式
    - 優惠碼校驗邏輯必須放在 services.py
    """

    class DiscountType(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", "百分比折扣"
        FIXED_AMOUNT = "FIXED_AMOUNT", "固定金額折扣"

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="唯一優惠碼 (如: SUPERMARKET666)",
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        help_text="折扣類型",
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="折扣數值（百分比為 0-100，固定金額為實際金額）",
    )
    min_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="最低消費金額門檻",
    )
    valid_from = models.DateTimeField(
        help_text="生效時間",
    )
    valid_until = models.DateTimeField(
        help_text="失效時間",
    )
    total_limit = models.PositiveIntegerField(
        default=0,
        help_text="總共可使用次數 (0 = 無限制)",
    )
    used_count = models.PositiveIntegerField(
        default=0,
        help_text="已使用次數 (Ref: data.md §1E - 必須用 F() 更新)",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="手動啟用/停用開關",
    )

    class Meta:
        verbose_name = "Coupon"
        verbose_name_plural = "Coupons"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.code} ({self.get_discount_type_display()})"


class Order(TimeStampedModel):
    """
    訂單 Model.

    Ref: data.md §1C
    - 必須記錄 applied_coupon 和 discount_amount
    - 創建訂單 + 扣庫存必須在 transaction.atomic 中 (data.md §5)
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "待付款"
        PAID = "PAID", "已付款"
        SHIPPED = "SHIPPED", "已發貨"
        CANCELLED = "CANCELLED", "已取消"
        REFUNDED = "REFUNDED", "已退款"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        help_text="下單用戶",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="訂單狀態",
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="訂單總金額（折扣後）",
    )
    payment_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="支付憑證 ID (Ref: data.md §1C)",
    )
    applied_coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text="使用的優惠碼 (Ref: data.md §1E - 必須記錄)",
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="折扣金額 (Ref: data.md §1E - 記錄下單時的折扣額度)",
    )

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Order {self.id} - {self.get_status_display()}"


class OrderItem(TimeStampedModel):
    """
    訂單項目 Model.

    Ref: data.md §1C
    - price_at_purchase 記錄購買時的價格，防止未來調價影響歷史訂單
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="所屬訂單",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
        help_text="購買商品",
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="購買數量",
    )
    price_at_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="購買時價格 (Ref: data.md §1C - 防止調價影響歷史訂單)",
    )

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self) -> str:
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self) -> Decimal:
        """計算小計金額."""
        return self.price_at_purchase * self.quantity


class UserCoupon(TimeStampedModel):
    """
    用戶優惠碼記錄 Model.

    Ref: data.md §1E
    - 記錄用戶領取或使用狀況
    - unique_together 防止單一用戶重複使用同一優惠碼
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_coupons",
        help_text="用戶",
    )
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name="user_coupons",
        help_text="優惠碼",
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="使用時間（null 表示已領取但未使用）",
    )

    class Meta:
        verbose_name = "User Coupon"
        verbose_name_plural = "User Coupons"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "coupon"],
                name="unique_user_coupon",
            )
        ]

    def __str__(self) -> str:
        status = "已使用" if self.used_at else "未使用"
        return f"{self.user} - {self.coupon.code} ({status})"
