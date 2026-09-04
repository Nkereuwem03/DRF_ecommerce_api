from django.contrib import admin

from .models import Category, Product, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "parent",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "is_active",
    ]

    search_fields = [
        "name",
        "slug",
    ]

    prepopulated_fields = {
        "slug": ("name",),
    }


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "price",
        "stock",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "is_active",
    ]

    search_fields = [
        "name",
        "slug",
        "description",
    ]

    filter_horizontal = [
        "categories",
    ]

    prepopulated_fields = {
        "slug": ("name",),
    }


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "is_primary",
        "display_order",
        "created_at",
    ]

    list_filter = [
        "is_primary",
    ]

    search_fields = [
        "product__name",
        "alt_text",
    ]

    ordering = [
        "product",
        "display_order",
    ]
