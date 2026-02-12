"""
Product & Inventory Models.

Ref: .blueprint/data.md §1A, §1B
- Category: 商品分類（支援多層）
- Product: 商品資訊
- Stock: 庫存管理（搶購核心，含樂觀鎖）
"""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from common.models import TimeStampedModel


class Category(TimeStampedModel):
    """
    商品分類 Model.

    Ref: data.md §1A
    支援多層分類結構（如：食品 > 零食 > 餅乾）
    """

    name = models.CharField(
        max_length=100,
        help_text="分類名稱",
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL 友好的唯一標識符",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text="父分類（用於多層分類結構）",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="是否啟用此分類",
    )

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Product(TimeStampedModel):
    """
    商品 Model.

    Ref: data.md §1A
    - price 使用 DecimalField (max_digits=10, decimal_places=2)
    - is_active 用於快速下架
    """

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        help_text="商品分類",
    )
    name = models.CharField(
        max_length=200,
        help_text="商品名稱",
    )
    description = models.TextField(
        blank=True,
        help_text="商品描述",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="商品價格 (Ref: data.md §4 - DecimalField)",
    )
    image_url = models.URLField(
        blank=True,
        help_text="商品圖片 URL (Ref: infra.md §5 - 外部存儲)",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="是否上架（用於快速下架產品）",
    )

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "-created_at"]),
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class Stock(TimeStampedModel):
    """
    庫存 Model - 搶購核心.

    Ref: data.md §1B
    - 獨立表設計，與 Product 一對一關聯
    - version 欄位用於 Optimistic Locking（樂觀鎖）
    - 扣減庫存必須使用 F() 表達式

    IMPORTANT (data.md §5):
    禁止在 View 層直接修改 quantity，
    必須透過 services.py 中的 decrease_stock 函數執行。
    """

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="stock",
        help_text="關聯商品",
    )
    quantity = models.PositiveIntegerField(
        default=0,
        help_text="庫存數量",
    )
    version = models.PositiveIntegerField(
        default=0,
        help_text="樂觀鎖版本號 (Ref: data.md §1B - Optimistic Locking)",
    )

    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"

    def __str__(self) -> str:
        return f"{self.product.name}: {self.quantity}"
