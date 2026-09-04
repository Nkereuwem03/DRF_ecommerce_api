from django.db import IntegrityError, transaction
from django.utils.text import slugify
from rest_framework.exceptions import NotFound

from ..models import Category

_UNSET = object()


class CategoryService:
    @staticmethod
    def _generate_unique_slug(
        name: str,
        category_id=None,
    ) -> str:

        base_slug = slugify(name)

        if not base_slug:
            raise ValueError("Category name cannot be converted into a valid slug.")

        slug = base_slug
        counter = 1

        while True:
            queryset = Category.objects.filter(
                slug=slug,
            )

            if category_id is not None:
                queryset = queryset.exclude(
                    pk=category_id,
                )

            if not queryset.exists():
                return slug

            slug = f"{base_slug}-{counter}"
            counter += 1

    @staticmethod
    def _validate_parent(
        parent: Category | None,
        category: Category | None = None,
    ) -> None:

        if parent is None:
            return

        if not parent.is_active:
            raise ValueError("An inactive category cannot be used as a parent.")

        if category is None:
            return

        if parent.pk == category.pk:
            raise ValueError("A category cannot be its own parent.")

        descendant_ids = CategoryService._get_descendant_ids(
            category=category,
        )

        if parent.pk in descendant_ids:
            raise ValueError("A category cannot be moved under one of its descendants.")

    @staticmethod
    def _get_descendant_ids(
        category: Category,
    ) -> set:

        descendant_ids = set()

        stack = list(
            Category.objects.filter(
                parent=category,
            ).values_list(
                "id",
                flat=True,
            )
        )

        while stack:
            descendant_id = stack.pop()

            if descendant_id in descendant_ids:
                continue

            descendant_ids.add(descendant_id)

            children = Category.objects.filter(
                parent_id=descendant_id,
            ).values_list(
                "id",
                flat=True,
            )

            stack.extend(children)

        return descendant_ids

    @staticmethod
    def _validate_category_name(
        name: str,
        parent: Category | None,
        exclude_category: Category | None = None,
    ) -> None:

        queryset = Category.objects.filter(
            name__iexact=name,
            is_active=True,
        )

        if parent is None:
            queryset = queryset.filter(
                parent__isnull=True,
            )
        else:
            queryset = queryset.filter(
                parent=parent,
            )

        if exclude_category is not None:
            queryset = queryset.exclude(
                pk=exclude_category.pk,
            )

        if queryset.exists():
            if parent is None:
                raise ValueError("A top-level category with this name already exists.")

            raise ValueError(
                "A category with this name already exists under this parent."
            )

    @staticmethod
    @transaction.atomic
    def create_category(
        *,
        name: str,
        description: str = "",
        parent: Category | None = None,
    ) -> Category:

        name = name.strip()

        CategoryService._validate_parent(
            parent=parent,
        )

        CategoryService._validate_category_name(
            name=name,
            parent=parent,
        )

        slug = CategoryService._generate_unique_slug(
            name=name,
        )

        try:
            return Category.objects.create(
                name=name,
                slug=slug,
                description=description.strip(),
                parent=parent,
            )
        except IntegrityError:
            slug = CategoryService._generate_unique_slug(
                name=name,
            )

            return Category.objects.create(
                name=name,
                slug=slug,
                description=description.strip(),
                parent=parent,
            )

    @staticmethod
    def get_root_categories():
        return Category.objects.filter(
            is_active=True,
            parent__isnull=True,
        ).order_by(
            "name",
        )

    @staticmethod
    def get_category_by_id(
        category_id,
    ) -> Category:

        try:
            return Category.objects.get(
                id=category_id,
                is_active=True,
            )
        except Category.DoesNotExist:
            raise NotFound("Category does not exist.")

    @staticmethod
    def get_category_children(
        category_id,
    ):
        parent = CategoryService.get_category_by_id(
            category_id=category_id,
        )

        return Category.objects.filter(
            parent=parent,
            is_active=True,
        ).order_by(
            "name",
        )

    @staticmethod
    @transaction.atomic
    def update_category(
        category_id,
        *,
        name: str | None = None,
        description: str | None = None,
        parent=_UNSET,
    ) -> Category:

        category = (
            Category.objects.select_for_update()
            .filter(
                id=category_id,
                is_active=True,
            )
            .first()
        )

        if category is None:
            raise NotFound("Category does not exist.")

        new_parent = category.parent if parent is _UNSET else parent

        CategoryService._validate_parent(
            parent=new_parent,
            category=category,
        )

        new_name = category.name if name is None else name.strip()

        if not new_name:
            raise ValueError("Category name cannot be empty.")

        CategoryService._validate_category_name(
            name=new_name,
            parent=new_parent,
            exclude_category=category,
        )

        if name is not None:
            category.name = new_name
            category.slug = CategoryService._generate_unique_slug(
                name=new_name,
                category_id=category.pk,
            )

        if description is not None:
            category.description = description.strip()

        if parent is not _UNSET:
            category.parent = new_parent

        try:
            category.save()
        except IntegrityError:
            category.slug = CategoryService._generate_unique_slug(
                name=category.name,
                category_id=category.pk,
            )
            category.save()

        return category

    @staticmethod
    @transaction.atomic
    def delete_category(
        category_id,
    ) -> None:

        category = (
            Category.objects.select_for_update()
            .filter(
                id=category_id,
                is_active=True,
            )
            .first()
        )

        if category is None:
            raise NotFound("Category does not exist.")

        has_active_children = Category.objects.filter(
            parent=category,
            is_active=True,
        ).exists()

        if has_active_children:
            raise ValueError(
                "Cannot deactivate a category that has active child categories."
            )

        category.is_active = False

        category.save(
            update_fields=[
                "is_active",
            ],
        )
