from collections.abc import Sequence
from decimal import Decimal

from django.db import transaction
from django.utils.text import slugify

from ..models import Category, Product


class ProductService:
    @staticmethod
    def _generate_unique_slug(
        name: str,
        product_id: str | None = None,
    ) -> str:

        base_slug = slugify(name)
        slug = base_slug
        counter = 1

        queryset = Product.objects.filter(
            slug=slug,
        )

        if product_id is not None:
            queryset = queryset.exclude(
                id=product_id,
            )

        while queryset.exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

            queryset = Product.objects.filter(
                slug=slug,
            )

            if product_id is not None:
                queryset = queryset.exclude(
                    id=product_id,
                )

        return slug

    @staticmethod
    @transaction.atomic
    def create_product(
        name: str,
        categories: Sequence[Category],
        description: str,
        price: Decimal,
        stock: int,
    ) -> Product:

        slug = ProductService._generate_unique_slug(
            name=name,
        )

        product = Product.objects.create(
            name=name,
            slug=slug,
            description=description,
            price=price,
            stock=stock,
        )

        product.categories.set(categories)

        return product

    @staticmethod
    @transaction.atomic
    def update_product(
        product_id: str,
        name: str | None = None,
        description: str | None = None,
        categories: Sequence[Category] | None = None,
        price: Decimal | None = None,
        stock: int | None = None,
    ) -> Product:

        product = ProductService.get_product_by_id(
            product_id=product_id,
        )

        if name is not None:
            product.name = name
            product.slug = ProductService._generate_unique_slug(
                name=name,
                product_id=product_id,
            )

        if description is not None:
            product.description = description

        if categories is not None:
            product.categories.set(categories)

        if price is not None:
            product.price = price

        if stock is not None:
            product.stock = stock

        product.save()

        return product

    @staticmethod
    @transaction.atomic
    def delete_product(
        product_id: str,
    ) -> None:

        product = ProductService.get_product_by_id(
            product_id=product_id,
        )

        product.is_active = False

        product.save(
            update_fields=["is_active"],
        )

    @staticmethod
    def get_product_by_id(
        product_id: str,
    ) -> Product:

        return Product.objects.get(
            id=product_id,
            is_active=True,
        )
