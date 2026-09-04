from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from config.error_handling.response import success_response

from ..filters import ProductFilter
from ..models import Product
from ..paginations import CustomPagination
from ..permissions import IsAuthenticatedReadOnlyOrAdmin
from ..serializers import ProductSerializer
from ..services.product import ProductService


class ProductListCreateAPIView(ListCreateAPIView):
    permission_classes = [IsAuthenticatedReadOnlyOrAdmin]
    serializer_class = ProductSerializer
    pagination_class = CustomPagination
    filter_backends = [filters.DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = [
        "name",
        "price",
        "stock",
        "created_at",
    ]

    ordering = [
        "-created_at",
    ]

    def get_queryset(self):
        return Product.objects.filter(is_active=True).prefetch_related(
            "categories",
            "images",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        product = ProductService.create_product(
            name=serializer.validated_data["name"],
            categories=serializer.validated_data["categories"],
            description=serializer.validated_data.get(
                "description",
                "",
            ),
            price=serializer.validated_data["price"],
            stock=serializer.validated_data["stock"],
        )

        return success_response(
            message="Product created successfully",
            data=ProductSerializer(product).data,
            status_code=status.HTTP_201_CREATED,
        )


class ProductRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticatedReadOnlyOrAdmin]
    serializer_class = ProductSerializer
    lookup_url_kwarg = "product_id"

    def get_queryset(self):
        return Product.objects.filter(is_active=True).prefetch_related(
            "categories",
            "images",
        )

    def retrieve(self, request, *args, **kwargs):
        product = self.get_object()

        serializer = self.get_serializer(product)

        return success_response(
            message="Product retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        product = self.get_object()

        serializer = self.get_serializer(
            product,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        updated_product = ProductService.update_product(
            product_id=product.id,
            name=serializer.validated_data.get("name"),
            description=serializer.validated_data.get("description"),
            categories=serializer.validated_data.get("categories"),
            price=serializer.validated_data.get("price"),
            stock=serializer.validated_data.get("stock"),
        )

        return success_response(
            message="Product updated successfully",
            data=ProductSerializer(updated_product).data,
            status_code=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()

        ProductService.delete_product(
            product_id=product.id,
        )

        return success_response(
            message="Product deleted successfully",
            status_code=status.HTTP_200_OK,
        )
