import django_filters

from .models import Product, ProductImage


class ProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
    )

    min_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="gte",
    )

    max_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="lte",
    )

    in_stock = django_filters.BooleanFilter(
        method="filter_in_stock",
    )

    created_after = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
    )

    created_before = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
    )

    category = django_filters.CharFilter(
        field_name="categories__name",
        lookup_expr="icontains",
    )

    category_id = django_filters.UUIDFilter(
        field_name="categories__id",
    )

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock__gt=0)
        return queryset.filter(stock=0)

    class Meta:
        model = Product
        fields = [
            "name",
            "min_price",
            "max_price",
            "in_stock",
            "created_after",
            "created_before",
            "category",
            "category_id",
        ]


class ProductImageFilter(django_filters.FilterSet):
    is_primary = django_filters.BooleanFilter(
        field_name="is_primary",
    )
    product_id = django_filters.UUIDFilter(
        field_name="product__id",
    )

    class Meta:
        model = ProductImage
        fields = [
            "product_id",
            "is_primary",
        ]
