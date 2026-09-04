from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.error_handling.response import success_response

from ..permissions import IsAuthenticatedReadOnlyOrAdmin
from ..serializers import CategorySerializer
from ..services.category import CategoryService


class CategoryListCreateView(APIView):
    permission_classes = [
        IsAuthenticatedReadOnlyOrAdmin,
    ]

    def get(self, request):
        categories = CategoryService.get_root_categories()

        serializer = CategorySerializer(
            categories,
            many=True,
        )

        return success_response(
            message="Categories retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = CategorySerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        category = CategoryService.create_category(
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get(
                "description",
                "",
            ),
            parent=serializer.validated_data.get(
                "parent",
            ),
        )

        return success_response(
            message="Category created successfully.",
            data=CategorySerializer(category).data,
            status_code=status.HTTP_201_CREATED,
        )


class CategoryDetailView(APIView):
    permission_classes = [
        IsAuthenticatedReadOnlyOrAdmin,
    ]

    def get(self, request, category_id):
        category = CategoryService.get_category_by_id(
            category_id=category_id,
        )

        serializer = CategorySerializer(category)

        return success_response(
            message="Category retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )

    def patch(self, request, category_id):
        serializer = CategorySerializer(
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        category = CategoryService.update_category(
            category_id=category_id,
            **serializer.validated_data,
        )

        return success_response(
            message="Category updated successfully.",
            data=CategorySerializer(category).data,
            status_code=status.HTTP_200_OK,
        )

    def delete(self, request, category_id):
        CategoryService.delete_category(
            category_id=category_id,
        )

        return success_response(
            message="Category deleted successfully.",
            status_code=status.HTTP_200_OK,
        )


class CategoryChildrenListView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request, category_id):
        categories = CategoryService.get_category_children(
            category_id=category_id,
        )

        serializer = CategorySerializer(
            categories,
            many=True,
        )

        return success_response(
            message="Child categories retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK,
        )
