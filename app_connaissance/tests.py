from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Department, KnowledgeKind, KnowledgeItem, UserProfile


class DepartmentKnowledgeAccessTests(TestCase):
    def setUp(self):
        # Departments
        self.dept_a = Department.objects.create(name="Informatique")
        self.dept_b = Department.objects.create(name="RH")
        # Kind
        kind = KnowledgeKind.objects.create(name="Procédure")
        # Users
        self.admin = User.objects.create_user(username="admin", password="pw")
        UserProfile.objects.create(user=self.admin, display_name="Admin", role="admin")

        self.manager = User.objects.create_user(username="mgr", password="pw")
        UserProfile.objects.create(user=self.manager, display_name="Manager", role="manager")

        self.user_a = User.objects.create_user(username="usera", password="pw")
        UserProfile.objects.create(user=self.user_a, display_name="User A", role="employee", department=self.dept_a)

        self.user_b = User.objects.create_user(username="userb", password="pw")
        UserProfile.objects.create(user=self.user_b, display_name="User B", role="employee", department=self.dept_b)

        # Knowledge items
        KnowledgeItem.objects.create(title="A publiée", kind=kind, department=self.dept_a, content="x", status=KnowledgeItem.Status.PUBLISHED)
        KnowledgeItem.objects.create(title="B publiée", kind=kind, department=self.dept_b, content="x", status=KnowledgeItem.Status.PUBLISHED)
        KnowledgeItem.objects.create(title="Global publiée", kind=kind, department=None, content="x", status=KnowledgeItem.Status.PUBLISHED)
        KnowledgeItem.objects.create(title="A brouillon", kind=kind, department=self.dept_a, content="x", status=KnowledgeItem.Status.DRAFT, author_user=self.user_a)

    def test_employee_sees_only_their_department_and_global(self):
        self.client.login(username="usera", password="pw")
        resp = self.client.get(reverse("knowledge_list"))
        titles = {i.title for i in resp.context["items"]}
        self.assertIn("A publiée", titles)
        self.assertIn("Global publiée", titles)
        self.assertNotIn("B publiée", titles)

    def test_admin_sees_all(self):
        self.client.login(username="admin", password="pw")
        resp = self.client.get(reverse("knowledge_list"))
        titles = {i.title for i in resp.context["items"]}
        self.assertIn("A publiée", titles)
        self.assertIn("B publiée", titles)
        self.assertIn("Global publiée", titles)

    def test_employee_cannot_view_other_department_detail(self):
        # usera should not access 'B publiée'
        item_b = KnowledgeItem.objects.get(title="B publiée")
        self.client.login(username="usera", password="pw")
        resp = self.client.get(reverse("knowledge_detail", args=[item_b.id]))
        # Should be redirected back to list
        self.assertEqual(resp.status_code, 302)

    def test_global_is_viewable_by_all(self):
        item_g = KnowledgeItem.objects.get(title="Global publiée")
        self.client.login(username="userb", password="pw")
        resp = self.client.get(reverse("knowledge_detail", args=[item_g.id]))
        self.assertEqual(resp.status_code, 200)

    def test_author_can_view_own_draft(self):
        draft = KnowledgeItem.objects.get(title="A brouillon")
        self.client.login(username="usera", password="pw")
        resp = self.client.get(reverse("knowledge_detail", args=[draft.id]))
        self.assertEqual(resp.status_code, 200)
