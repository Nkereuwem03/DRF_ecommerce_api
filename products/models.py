import uuid

from django.db import models
from django.db.models.functions import Lower


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )

    name = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "categories"

        ordering = [
            "name",
        ]

        indexes = [
            models.Index(
                fields=[
                    "parent",
                    "is_active",
                ],
            ),
            models.Index(
                fields=[
                    "is_active",
                ],
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                condition=models.Q(
                    parent__isnull=True,
                ),
                name="unique_root_category_name_ci",
            ),
            models.UniqueConstraint(
                Lower("name"),
                "parent",
                condition=models.Q(
                    parent__isnull=False,
                ),
                name="unique_child_category_name_ci",
            ),
        ]

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    categories = models.ManyToManyField(
        Category,
        related_name="products",
        blank=True,
    )

    name = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    stock = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "products"

        ordering = [
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "is_active",
                    "-created_at",
                ],
            ),
            models.Index(
                fields=[
                    "name",
                ],
            ),
        ]

    def __str__(self):
        return self.name


class ProductImage(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(
        upload_to="products/",
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True,
    )

    is_primary = models.BooleanField(
        default=False,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        db_table = "product_images"

        ordering = [
            "display_order",
            "created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "product",
                    "display_order",
                ],
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "product",
                ],
                condition=models.Q(
                    is_primary=True,
                ),
                name="unique_primary_image_per_product",
            ),
        ]

    def __str__(self):
        return f"Image for {self.product.name}"
