from collections.abc import Sequence
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils.text import slugify
from rest_framework.exceptions import NotFound

from ..models import Category, Product


class ProductService:
    @staticmethod
    def _generate_unique_slug(
        name: str,
        product_id=None,
    ) -> str:

        base_slug = slugify(name)

        if not base_slug:
            raise ValueError("Product name cannot be converted into a valid slug.")

        slug = base_slug
        counter = 1

        while True:
            queryset = Product.objects.filter(
                slug=slug,
            )

            if product_id is not None:
                queryset = queryset.exclude(
                    pk=product_id,
                )

            if not queryset.exists():
                return slug

            slug = f"{base_slug}-{counter}"
            counter += 1

    @staticmethod
    def _validate_categories(
        categories: Sequence[Category],
    ) -> None:

        categories = list(categories)

        if not categories:
            raise ValueError("At least one category is required.")

        category_ids = {category.pk for category in categories}

        active_count = Category.objects.filter(
            id__in=category_ids,
            is_active=True,
        ).count()

        if active_count != len(category_ids):
            raise ValueError(
                "One or more selected categories do not exist or are inactive."
            )

    @staticmethod
    @transaction.atomic
    def create_product(
        name: str,
        categories: Sequence[Category],
        description: str,
        price: Decimal,
        stock: int,
    ) -> Product:

        name = name.strip()

        if not name:
            raise ValueError("Product name cannot be empty.")

        ProductService._validate_categories(
            categories=categories,
        )

        slug = ProductService._generate_unique_slug(
            name=name,
        )

        try:
            with transaction.atomic():
                product = Product.objects.create(
                    name=name,
                    slug=slug,
                    description=description.strip(),
                    price=price,
                    stock=stock,
                )
        except IntegrityError:
            slug = ProductService._generate_unique_slug(
                name=name,
            )

            product = Product.objects.create(
                name=name,
                slug=slug,
                description=description.strip(),
                price=price,
                stock=stock,
            )

        product.categories.set(
            categories,
        )

        return product

    @staticmethod
    @transaction.atomic
    def update_product(
        product_id,
        name: str | None = None,
        description: str | None = None,
        categories: Sequence[Category] | None = None,
        price: Decimal | None = None,
        stock: int | None = None,
    ) -> Product:

        product = (
            Product.objects.select_for_update()
            .filter(
                id=product_id,
                is_active=True,
            )
            .first()
        )

        if product is None:
            raise NotFound("Product does not exist.")

        if name is not None:
            name = name.strip()

            if not name:
                raise ValueError("Product name cannot be empty.")

            product.name = name
            product.slug = ProductService._generate_unique_slug(
                name=name,
                product_id=product.pk,
            )

        if description is not None:
            product.description = description.strip()

        if categories is not None:
            ProductService._validate_categories(
                categories=categories,
            )

            product.categories.set(
                categories,
            )

        if price is not None:
            product.price = price

        if stock is not None:
            product.stock = stock

        try:
            product.save()
        except IntegrityError:
            if name is None:
                raise

            product.slug = ProductService._generate_unique_slug(
                name=product.name,
                product_id=product.pk,
            )

            product.save()

        return product

    @staticmethod
    @transaction.atomic
    def delete_product(
        product_id,
    ) -> None:

        product = (
            Product.objects.select_for_update()
            .filter(
                id=product_id,
                is_active=True,
            )
            .first()
        )

        if product is None:
            raise NotFound("Product does not exist.")

        product.is_active = False

        product.save(
            update_fields=[
                "is_active",
            ],
        )

    @staticmethod
    def get_product_by_id(
        product_id,
    ) -> Product:

        try:
            return Product.objects.get(
                id=product_id,
                is_active=True,
            )
        except Product.DoesNotExist:
            raise NotFound("Product does not exist.")
