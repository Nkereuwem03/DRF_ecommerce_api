from django.db import transaction
from django.utils.text import slugify
from rest_framework.exceptions import NotFound

from ..models import Category

_UNSET = object()


class CategoryService:
    @staticmethod
    def _generate_unique_slug(name: str) -> str:
        base_slug = slugify(name)

        slug = base_slug
        counter = 1

        while Category.objects.filter(
            slug=slug,
        ).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    @staticmethod
    def _validate_parent(
        parent: Category | None,
    ) -> None:
        if parent is None:
            return

        if not parent.is_active:
            raise ValueError("An inactive category cannot be used as a parent.")

    @staticmethod
    def _validate_category_name(
        name: str,
        parent: Category | None,
        exclude_category: Category | None = None,
    ) -> None:

        queryset = Category.objects.filter(name__iexact=name)

        if parent is None:
            queryset = queryset.filter(parent__isnull=True)
        else:
            queryset = queryset.filter(parent=parent)

        if exclude_category is not None:
            queryset = queryset.exclude(pk=exclude_category.pk)

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

        return Category.objects.create(
            name=name,
            slug=slug,
            description=description,
            parent=parent,
        )

    @staticmethod
    def get_root_categories():
        return Category.objects.filter(
            is_active=True,
            parent__isnull=True,
        ).order_by("name")

    @staticmethod
    def get_category_by_id(
        category_id,
    ) -> Category:

        try:
            return Category.objects.get(
                id=category_id,
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
        ).order_by("name")

    @staticmethod
    @transaction.atomic
    def update_category(
        category_id,
        *,
        name: str | None = None,
        description: str | None = None,
        parent=_UNSET,
    ) -> Category:

        category = CategoryService.get_category_by_id(
            category_id=category_id,
        )

        # If parent was not included in the request,
        # keep the existing parent.
        new_parent = category.parent if parent is _UNSET else parent

        # Validate the new parent.
        CategoryService._validate_parent(
            parent=new_parent,
        )

        # Use the new name if supplied,
        # otherwise keep the existing name.
        new_name = category.name if name is None else name

        # Validate that the name is unique
        # within the new parent.
        CategoryService._validate_category_name(
            name=new_name,
            parent=new_parent,
            exclude_category=category,
        )

        # Update name and regenerate slug
        # only when the name actually changes.
        if name is not None:
            category.name = name
            category.slug = CategoryService._generate_unique_slug(
                name=name,
            )

        # Update description only when supplied.
        if description is not None:
            category.description = description

        # Update parent, including explicitly setting it to None.
        if parent is not _UNSET:
            category.parent = parent

        category.save()

        return category

    @staticmethod
    def delete_category(category_id) -> None:
        category = CategoryService.get_category_by_id(
            category_id=category_id,
        )

        category.is_active = False
        category.save(update_fields=["is_active"])
