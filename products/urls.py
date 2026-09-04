from django.urls import path

from .views.category import (
    CategoryChildrenListView,
    CategoryDetailView,
    CategoryListCreateView,
)
from .views.product import (
    ProductListCreateAPIView,
    ProductRetrieveUpdateDestroyAPIView,
)
from .views.product_image import (
    ProductImageListCreateAPIView,
    ProductImageRetrieveUpdateDestroyAPIView,
)

urlpatterns = [
    path(
        "categories/",
        CategoryListCreateView.as_view(),
        name="category-list-create",
    ),
    path(
        "categories/<uuid:category_id>/",
        CategoryDetailView.as_view(),
        name="category-detail",
    ),
    path(
        "categories/<uuid:category_id>/children/",
        CategoryChildrenListView.as_view(),
        name="category-children",
    ),
    path(
        "",
        ProductListCreateAPIView.as_view(),
        name="product-list-create",
    ),
    path(
        "<uuid:product_id>/",
        ProductRetrieveUpdateDestroyAPIView.as_view(),
        name="product-detail",
    ),
    path(
        "<uuid:product_id>/images/",
        ProductImageListCreateAPIView.as_view(),
        name="product-image-list-create",
    ),
    path(
        "<uuid:product_id>/images/<uuid:image_id>/",
        ProductImageRetrieveUpdateDestroyAPIView.as_view(),
        name="product-image-detail",
    ),
]
