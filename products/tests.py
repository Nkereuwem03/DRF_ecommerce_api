from django.test import TestCase

from .models import Category
from .services.category import CategoryService


class CategoryServiceTests(TestCase):
    def test_update_category_allows_reparenting_without_error(self):
        parent = Category.objects.create(name="Parent", slug="parent")
        child = Category.objects.create(name="Child", slug="child", parent=parent)

        updated = CategoryService.update_category(
            category_id=child.id,
            parent=None,
            name="Updated Child",
        )

        self.assertIsNone(updated.parent)
        self.assertEqual(updated.name, "Updated Child")

    def test_delete_category_marks_category_inactive(self):
        category = Category.objects.create(name="To Delete", slug="to-delete")

        CategoryService.delete_category(category_id=category.id)

        category.refresh_from_db()
        self.assertFalse(category.is_active)
