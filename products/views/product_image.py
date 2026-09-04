from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status

from config.error_handling.response import (
    error_response,
    success_response,
)

from ..filters import ProductImageFilter
from ..models import Product, ProductImage
from ..permissions import IsAuthenticatedReadOnlyOrAdmin
from ..serializers import (
    ProductImageCreateSerializer,
    ProductImageSerializer,
    ProductImageUpdateSerializer,
)
from ..services.product_image import ProductImageService


class ProductImageListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticatedReadOnlyOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductImageFilter

    def get_queryset(self):
        return ProductImage.objects.filter(product_id=self.kwargs["product_id"])

    def create(self, request, *args, **kwargs):
        product = Product.objects.filter(
            id=self.kwargs["product_id"],
            is_active=True,
        ).first()

        if product is None:
            return error_response(
                message="Product not found or inactive.",
                data={},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProductImageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            images = ProductImageService.create_images(
                product=product,
                images=serializer.validated_data["images"],
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                data={},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            message="Product images created successfully.",
            data=ProductImageSerializer(
                images,
                many=True,
            ).data,
            status_code=status.HTTP_201_CREATED,
        )


class ProductImageRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticatedReadOnlyOrAdmin]
    lookup_url_kwarg = "image_id"

    def get_queryset(self):
        return ProductImage.objects.filter(product_id=self.kwargs["product_id"])

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer = self.get_serializer(instance)

        return success_response(
            message="Product image retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)

        instance = self.get_object()

        serializer = ProductImageUpdateSerializer(
            instance=instance,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)

        try:
            updated_image = ProductImageService.update_image(
                product_image=instance,
                **serializer.validated_data,
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                data={},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            message="Product image updated successfully.",
            data=ProductImageSerializer(updated_image).data,
            status_code=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            ProductImageService.delete_image(
                product_image=instance,
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                data={},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            message="Product image deleted successfully.",
            data={},
            status_code=status.HTTP_200_OK,
        )
