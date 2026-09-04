from rest_framework import serializers

from .models import Category, Product, ProductImage


class ProductImageNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage

        fields = [
            "id",
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "created_at",
            "updated_at",
        ]


class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        error_messages={
            "does_not_exist": "Parent category with this ID does not exist.",
            "incorrect_type": "Parent category ID must be a valid UUID.",
        },
    )

    class Meta:
        model = Category

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "parent",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "slug",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Category name cannot be empty.")

        return value


class ProductSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Category.objects.filter(is_active=True),
        error_messages={
            "does_not_exist": "Category with this ID does not exist.",
            "incorrect_type": "Category ID must be a valid UUID.",
        },
    )

    images = ProductImageNestedSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Product

        fields = [
            "id",
            "categories",
            "name",
            "slug",
            "description",
            "images",
            "price",
            "stock",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "slug",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def validate_categories(self, value):
        if not value:
            raise serializers.ValidationError("At least one category is required.")

        return value


class ProductImageCreateSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        allow_empty=False,
        max_length=4,
    )

    def validate_images(self, value):
        max_size = 5 * 1024 * 1024

        allowed_types = {
            "image/jpeg",
            "image/png",
            "image/webp",
        }

        for image in value:
            if image.size > max_size:
                raise serializers.ValidationError(
                    "Each image file must not exceed 5MB."
                )

            if image.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Only JPEG, PNG, and WebP images are allowed."
                )

        return value


class ProductImageUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage

        fields = [
            "image",
            "alt_text",
            "is_primary",
            "display_order",
        ]

        extra_kwargs = {
            "image": {
                "required": False,
            },
            "alt_text": {
                "required": False,
            },
            "is_primary": {
                "required": False,
            },
            "display_order": {
                "required": False,
            },
        }


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage

        fields = [
            "id",
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "is_primary",
            "display_order",
            "created_at",
            "updated_at",
        ]
