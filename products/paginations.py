from rest_framework import pagination, status

from config.error_handling.response import success_response


class CustomPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return success_response(
            message="Products retrieved successfully",
            data={
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            },
            status_code=status.HTTP_200_OK,
        )
