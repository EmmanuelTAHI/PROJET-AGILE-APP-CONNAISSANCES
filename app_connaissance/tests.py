from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Department, KnowledgeItem, KnowledgeKind, UserProfile


class DepartmentVisibilityTests(TestCase):
    def setUp(self):
        # Departments
        self.dept_compta = Department.objects.create(name="Comptabilité")
        self.dept_rh = Department.objects.create(name="Ressources Humaines")

        # Kind
        self.kind = KnowledgeKind.objects.create(name="Procédure")

        # Users
        self.user_compta = User.objects.create_user(username="alice", password="pwd")
        self.profile_compta = UserProfile.objects.create(user=self.user_compta, display_name="Alice", role="employee", department=self.dept_compta)

        self.user_rh = User.objects.create_user(username="bruno", password="pwd")
        self.profile_rh = UserProfile.objects.create(user=self.user_rh, display_name="Bruno", role="employee", department=self.dept_rh)

        self.user_admin = User.objects.create_user(username="admin", password="pwd")
        self.profile_admin = UserProfile.objects.create(user=self.user_admin, display_name="Admin", role="admin")

        self.user_manager = User.objects.create_user(username="mgr", password="pwd")
        self.profile_manager = UserProfile.objects.create(user=self.user_manager, display_name="Manager", role="manager")

        # Knowledge items
        self.k_compta_pub = KnowledgeItem.objects.create(title="Budget AV", kind=self.kind, department=self.dept_compta, content="x", status=KnowledgeItem.Status.PUBLISHED)
        self.k_rh_pub = KnowledgeItem.objects.create(title="Onboarding", kind=self.kind, department=self.dept_rh, content="x", status=KnowledgeItem.Status.PUBLISHED)
        self.k_compta_draft = KnowledgeItem.objects.create(title="Secret compta", kind=self.kind, department=self.dept_compta, content="x", status=KnowledgeItem.Status.DRAFT)

    def test_employee_sees_only_their_department_in_list(self):
        self.client.force_login(self.user_compta)
        url = reverse('knowledge_list')
        resp = self.client.get(url)
        items = resp.context['items']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, self.k_compta_pub.id)

    def test_employee_cannot_view_other_department_detail(self):
        self.client.force_login(self.user_compta)
        url = reverse('knowledge_detail', kwargs={'knowledge_id': self.k_rh_pub.id})
        resp = self.client.get(url)
        # Redirection vers la liste si accès refusé
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('knowledge_list'))

    def test_admin_and_manager_see_all(self):
        # Admin
        self.client.force_login(self.user_admin)
        resp = self.client.get(reverse('knowledge_list'))
        items = resp.context['items']
        ids = {i.id for i in items}
        self.assertIn(self.k_compta_pub.id, ids)
        self.assertIn(self.k_rh_pub.id, ids)

        # Manager
        self.client.force_login(self.user_manager)
        resp = self.client.get(reverse('knowledge_list'))
        items = resp.context['items']
        ids = {i.id for i in items}
        self.assertIn(self.k_compta_pub.id, ids)
        self.assertIn(self.k_rh_pub.id, ids)

    def test_department_filter_cant_be_used_to_bypass(self):
        # Employee of compta tries to filter by RH
        self.client.force_login(self.user_compta)
        resp = self.client.get(reverse('knowledge_list') + f'?department={self.dept_rh.id}')
        items = resp.context['items']
        # No results because filter is intersected with user's department
        self.assertEqual(len(items), 0)

