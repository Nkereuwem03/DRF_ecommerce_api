from collections.abc import Sequence

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import F

from ..models import Product, ProductImage


class ProductImageService:
    MAX_IMAGES = 4

    @staticmethod
    @transaction.atomic
    def create_images(
        product: Product,
        images: Sequence[UploadedFile],
    ) -> list[ProductImage]:

        existing_count = ProductImage.objects.filter(
            product=product,
        ).count()

        new_count = len(images)

        if existing_count + new_count > ProductImageService.MAX_IMAGES:
            raise ValueError(
                f"A product can have a maximum of "
                f"{ProductImageService.MAX_IMAGES} images."
            )

        existing_images = list(
            ProductImage.objects.filter(
                product=product,
            ).order_by(
                "display_order",
                "created_at",
            )
        )

        created_images = []

        start_order = len(existing_images)

        for index, image in enumerate(images):
            display_order = start_order + index

            product_image = ProductImage.objects.create(
                product=product,
                image=image,
                alt_text=f"{product.name} image {display_order + 1}",
                is_primary=False,
                display_order=display_order,
            )

            created_images.append(product_image)

        if not existing_images and created_images:
            primary_image = created_images[0]

            primary_image.is_primary = True

            primary_image.save(
                update_fields=["is_primary"],
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

        product = product_image.product

        old_order = product_image.display_order

        new_order = display_order if display_order is not None else old_order

        image_count = ProductImage.objects.filter(
            product=product,
        ).count()

        max_order = image_count - 1

        if new_order < 0 or new_order > max_order:
            raise ValueError(f"display_order must be between 0 and {max_order}.")

        if is_primary is True:
            new_order = 0

        elif new_order == 0:
            is_primary = True

        if is_primary is False and old_order == 0 and new_order == 0:
            raise ValueError(
                "The primary image cannot be made non-primary "
                "while remaining at display_order 0."
            )

        update_fields = []

        if image is not None:
            product_image.image = image
            update_fields.append("image")

        if alt_text is not None:
            product_image.alt_text = alt_text
            update_fields.append("alt_text")

        if new_order != old_order:
            if new_order < old_order:
                ProductImage.objects.filter(
                    product=product,
                    display_order__gte=new_order,
                    display_order__lt=old_order,
                ).exclude(
                    pk=product_image.pk,
                ).update(
                    display_order=F("display_order") + 1,
                )

            else:
                ProductImage.objects.filter(
                    product=product,
                    display_order__gt=old_order,
                    display_order__lte=new_order,
                ).exclude(
                    pk=product_image.pk,
                ).update(
                    display_order=F("display_order") - 1,
                )

            product_image.display_order = new_order
            update_fields.append("display_order")

        if is_primary is True or new_order == 0:
            ProductImage.objects.filter(
                product=product,
                is_primary=True,
            ).exclude(
                pk=product_image.pk,
            ).update(
                is_primary=False,
            )

            product_image.is_primary = True

            if "is_primary" not in update_fields:
                update_fields.append("is_primary")

        elif is_primary is False:
            product_image.is_primary = False

            if "is_primary" not in update_fields:
                update_fields.append("is_primary")

        if new_order == 0:
            product_image.is_primary = True

            if "is_primary" not in update_fields:
                update_fields.append("is_primary")

        if update_fields:
            product_image.save(
                update_fields=update_fields,
            )

        ProductImageService._ensure_primary_image(
            product=product,
        )

        return product_image

    @staticmethod
    def _ensure_primary_image(
        product: Product,
    ) -> ProductImage:

        primary_image = ProductImage.objects.filter(
            product=product,
            display_order=0,
        ).first()

        if primary_image is None:
            raise ValueError("A product must have a primary image.")

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
                update_fields=["is_primary"],
            )

        return primary_image

    @staticmethod
    @transaction.atomic
    def delete_image(
        product_image: ProductImage,
    ) -> None:

        if product_image.is_primary:
            raise ValueError("Cannot delete the primary image of the product.")

        product = product_image.product
        deleted_order = product_image.display_order

        product_image.delete()

        ProductImage.objects.filter(
            product=product,
            display_order__gt=deleted_order,
        ).update(
            display_order=F("display_order") - 1,
        )
