from collections.abc import Sequence

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import NotFound

from ..models import Product, ProductImage


class ProductImageService:
    MAX_IMAGES = 4

    @staticmethod
    def _lock_product(
        product_id,
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
            raise NotFound("Product does not exist or is inactive.")

        return product

    @staticmethod
    def _normalize_order(
        product: Product,
    ) -> list[ProductImage]:

        images = list(
            ProductImage.objects.select_for_update()
            .filter(
                product=product,
            )
            .order_by(
                "display_order",
                "created_at",
                "id",
            )
        )

        for index, image in enumerate(images):
            if image.display_order != index:
                ProductImage.objects.filter(
                    pk=image.pk,
                ).update(
                    display_order=index,
                )

            image.display_order = index

        return images

    @staticmethod
    def _ensure_primary_image(
        product: Product,
    ) -> ProductImage:

        images = list(
            ProductImage.objects.select_for_update()
            .filter(
                product=product,
            )
            .order_by(
                "display_order",
                "created_at",
                "id",
            )
        )

        if not images:
            raise ValueError("A product must have at least one image.")

        primary_image = images[0]

        ProductImage.objects.filter(
            product=product,
        ).exclude(
            pk=primary_image.pk,
        ).update(
            is_primary=False,
        )

        if not primary_image.is_primary:
            primary_image.is_primary = True

            primary_image.save(
                update_fields=[
                    "is_primary",
                ],
            )

        return primary_image

    @staticmethod
    @transaction.atomic
    def create_images(
        product: Product,
        images: Sequence[UploadedFile],
    ) -> list[ProductImage]:

        product = ProductImageService._lock_product(
            product_id=product.pk,
        )

        existing_images = ProductImageService._normalize_order(
            product=product,
        )

        existing_count = len(existing_images)
        new_count = len(images)

        if existing_count + new_count > ProductImageService.MAX_IMAGES:
            raise ValueError(
                f"A product can have a maximum of "
                f"{ProductImageService.MAX_IMAGES} images."
            )

        created_images = []

        start_order = existing_count

        for index, image in enumerate(images):
            display_order = start_order + index

            product_image = ProductImage.objects.create(
                product=product,
                image=image,
                alt_text=f"{product.name} image {display_order + 1}",
                is_primary=False,
                display_order=display_order,
            )

            created_images.append(
                product_image,
            )

        if not existing_images and created_images:
            primary_image = created_images[0]

            primary_image.is_primary = True

            primary_image.save(
                update_fields=[
                    "is_primary",
                ],
            )

        return created_images

    @staticmethod
    @transaction.atomic
    def update_image(
        product_image: ProductImage,
        image: UploadedFile | None = None,
        alt_text: str | None = None,
        is_primary: bool | None = None,
        display_order: int | None = None,
    ) -> ProductImage:

        product = ProductImageService._lock_product(
            product_id=product_image.product_id,
        )

        current_image = (
            ProductImage.objects.select_for_update()
            .filter(
                pk=product_image.pk,
                product=product,
            )
            .first()
        )

        if current_image is None:
            raise NotFound("Product image does not exist.")

        images = ProductImageService._normalize_order(
            product=product,
        )

        image_count = len(images)

        old_order = current_image.display_order

        new_order = old_order if display_order is None else display_order

        if new_order < 0 or new_order >= image_count:
            raise ValueError(f"display_order must be between 0 and {image_count - 1}.")

        if is_primary is True:
            new_order = 0

        if new_order == 0:
            is_primary = True

        if is_primary is False and old_order == 0 and new_order == 0:
            raise ValueError(
                "The primary image cannot be made non-primary "
                "while remaining at display_order 0."
            )

        if image is not None:
            current_image.image = image

        if alt_text is not None:
            current_image.alt_text = alt_text

        if new_order != old_order:
            if new_order < old_order:
                ProductImage.objects.filter(
                    product=product,
                    display_order__gte=new_order,
                    display_order__lt=old_order,
                ).exclude(
                    pk=current_image.pk,
                ).update(
                    display_order=F("display_order") + 1,
                )

            else:
                ProductImage.objects.filter(
                    product=product,
                    display_order__gt=old_order,
                    display_order__lte=new_order,
                ).exclude(
                    pk=current_image.pk,
                ).update(
                    display_order=F("display_order") - 1,
                )

            current_image.display_order = new_order

        if is_primary is True:
            ProductImage.objects.filter(
                product=product,
            ).exclude(
                pk=current_image.pk,
            ).update(
                is_primary=False,
            )

            current_image.is_primary = True

        elif is_primary is False:
            current_image.is_primary = False

        if current_image.display_order == 0:
            current_image.is_primary = True

        current_image.save()

        ProductImageService._ensure_primary_image(
            product=product,
        )

        current_image.refresh_from_db()

        return current_image

    @staticmethod
    @transaction.atomic
    def delete_image(
        product_image: ProductImage,
    ) -> None:

        product = ProductImageService._lock_product(
            product_id=product_image.product_id,
        )

        current_image = (
            ProductImage.objects.select_for_update()
            .filter(
                pk=product_image.pk,
                product=product,
            )
            .first()
        )

        if current_image is None:
            raise NotFound("Product image does not exist.")

        if current_image.is_primary:
            raise ValueError("Cannot delete the primary image of the product.")

        deleted_order = current_image.display_order

        current_image.delete()

        ProductImage.objects.filter(
            product=product,
            display_order__gt=deleted_order,
        ).update(
            display_order=F("display_order") - 1,
        )

        remaining_images = list(
            ProductImage.objects.select_for_update()
            .filter(
                product=product,
            )
            .order_by(
                "display_order",
                "created_at",
                "id",
            )
        )

        for index, image in enumerate(remaining_images):
            if image.display_order != index:
                ProductImage.objects.filter(
                    pk=image.pk,
                ).update(
                    display_order=index,
                )

        if remaining_images:
            ProductImageService._ensure_primary_image(
                product=product,
            )
