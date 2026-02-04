from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from app_connaissance.models import (
    Department, Poste, PlanIntegration, Module, ModuleStep,
    Quiz, QuizQuestion, QuizChoice, UserProfile, Progression,
    UserModuleStepCompletion, UserQuizAttempt
)

class IntegrationPlanTestCase(TestCase):
    """Tests de base pour le plan d'intégration"""
    
    def setUp(self):
        """Configuration des données de test"""
        self.client = Client()
        
        # Créer un département
        self.department = Department.objects.create(
            name="Informatique",
            description="Département technique"
        )
        
        # Créer un poste
        self.poste = Poste.objects.create(
            intitule="Développeur Web",
            department=self.department,
            description="Développeur web full-stack"
        )
        
        # Créer un plan d'intégration
        self.plan = PlanIntegration.objects.create(
            titre="Plan Développeur Web",
            description="Plan d'intégration pour les développeurs",
            duree_semaines=4
        )
        self.poste.plan_integration = self.plan
        self.poste.save()
        
        # Créer un utilisateur
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Créer le profil utilisateur
        self.profile = UserProfile.objects.create(
            user=self.user,
            display_name='Test User',
            role='employee',
            department=self.department,
            poste=self.poste
        )
        
        # Créer un module
        self.module = Module.objects.create(
            titre="Module Test",
            ordre=1,
            plan=self.plan,
            duree_jours=5
        )
        
        # Créer des étapes
        self.step1 = ModuleStep.objects.create(
            module=self.module,
            titre="Étape 1",
            ordre=1
        )
        self.step2 = ModuleStep.objects.create(
            module=self.module,
            titre="Étape 2",
            ordre=2
        )

class PlanIntegrationViewTest(IntegrationPlanTestCase):
    """Tests des vues du plan d'intégration"""
    
    def test_plan_integration_personnel_view_authenticated(self):
        """Test la vue du plan personnel pour utilisateur authentifié"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('plan_integration_personnel'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Plan Développeur Web')
        self.assertContains(response, 'Module Test')
    
    def test_plan_integration_personnel_view_unauthenticated(self):
        """Test la redirection pour utilisateur non authentifié"""
        response = self.client.get(reverse('plan_integration_personnel'))
        self.assertEqual(response.status_code, 302)  # Redirection vers login
    
    def test_plan_integration_personnel_no_plan(self):
        """Test quand l'utilisateur n'a pas de plan"""
        self.poste.plan_integration = None
        self.poste.save()
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('plan_integration_personnel'))
        
        self.assertEqual(response.status_code, 302)  # Redirection
    
    def test_module_step_toggle(self):
        """Test le toggle d'étape de module"""
        self.client.login(username='testuser', password='testpass123')
        
        # Toggle l'étape
        response = self.client.post(
            reverse('module_step_toggle', args=[self.step1.id]),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['checked'])
        
        # Vérifier que l'étape est marquée comme complétée
        completion = UserModuleStepCompletion.objects.filter(
            user=self.user,
            module_step=self.step1
        ).first()
        self.assertIsNotNone(completion)
    
    def test_module_step_toggle_uncheck(self):
        """Test le décochage d'une étape"""
        # Créer une complétion initiale
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Décocher l'étape
        response = self.client.post(
            reverse('module_step_toggle', args=[self.step1.id]),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertFalse(data['checked'])
        
        # Vérifier que la complétion a été supprimée
        completion = UserModuleStepCompletion.objects.filter(
            user=self.user,
            module_step=self.step1
        ).first()
        self.assertIsNone(completion)

class QuizViewTest(IntegrationPlanTestCase):
    """Tests des vues de quiz"""
    
    def setUp(self):
        super().setUp()
        
        # Créer un quiz
        self.quiz = Quiz.objects.create(
            module=self.module,
            titre="Quiz Test",
            seuil_reussite_pct=70
        )
        
        # Créer des questions
        self.question = QuizQuestion.objects.create(
            quiz=self.quiz,
            enonce="Question test ?",
            ordre=1
        )
        
        # Créer des choix
        self.choice1 = QuizChoice.objects.create(
            question=self.question,
            texte="Réponse correcte",
            is_correct=True
        )
        self.choice2 = QuizChoice.objects.create(
            question=self.question,
            texte="Réponse incorrecte",
            is_correct=False
        )
    
    def test_quiz_take_view(self):
        """Test la vue de prise de quiz"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('quiz_take', args=[self.quiz.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quiz Test')
        self.assertContains(response, 'Question test ?')
    
    def test_quiz_submit_correct(self):
        """Test la soumission d'un quiz avec réponse correcte"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('quiz_take', args=[self.quiz.id]),
            {
                f'q_{self.question.id}': self.choice1.id,
                'submit': '1'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Vérifier la tentative de quiz
        attempt = UserQuizAttempt.objects.filter(
            user=self.user,
            quiz=self.quiz
        ).first()
        self.assertIsNotNone(attempt)
        self.assertTrue(attempt.passed)
        self.assertEqual(attempt.score_pct, 100)
    
    def test_quiz_submit_incorrect(self):
        """Test la soumission d'un quiz avec réponse incorrecte"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('quiz_take', args=[self.quiz.id]),
            {
                f'q_{self.question.id}': self.choice2.id,
                'submit': '1'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Vérifier la tentative de quiz
        attempt = UserQuizAttempt.objects.filter(
            user=self.user,
            quiz=self.quiz
        ).first()
        self.assertIsNotNone(attempt)
        self.assertFalse(attempt.passed)
        self.assertEqual(attempt.score_pct, 0)

class ProgressionTest(IntegrationPlanTestCase):
    """Tests du calcul de progression"""
    
    def test_progression_calculation(self):
        """Test le calcul de progression"""
        # Compléter une étape sur deux
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('plan_integration_personnel'))
        
        self.assertEqual(response.status_code, 200)
        
        # Vérifier la progression (1/2 = 50%)
        progression = Progression.objects.filter(
            user=self.user,
            plan=self.plan
        ).first()
        self.assertIsNotNone(progression)
        self.assertEqual(progression.pourcentage, 50)
    
    def test_progression_full_completion(self):
        """Test la progression avec complétion totale"""
        # Compléter toutes les étapes
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1
        )
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step2
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('plan_integration_personnel'))
        
        self.assertEqual(response.status_code, 200)
        
        # Vérifier la progression (2/2 = 100%)
        progression = Progression.objects.filter(
            user=self.user,
            plan=self.plan
        ).first()
        self.assertIsNotNone(progression)
        self.assertEqual(progression.pourcentage, 100)

class PermissionTest(IntegrationPlanTestCase):
    """Tests des permissions et accès"""
    
    def test_user_can_only_access_own_plan(self):
        """Test qu'un utilisateur ne peut voir que son propre plan"""
        # Créer un autre utilisateur avec un autre plan
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        other_department = Department.objects.create(
            name="Marketing",
            description="Département marketing"
        )
        
        other_poste = Poste.objects.create(
            intitule="Chef de projet",
            department=other_department,
            description="Chef de projet marketing"
        )
        
        other_plan = PlanIntegration.objects.create(
            titre="Plan Marketing",
            description="Plan d'intégration marketing"
        )
        other_poste.plan_integration = other_plan
        other_poste.save()
        
        UserProfile.objects.create(
            user=other_user,
            display_name='Other User',
            role='employee',
            department=other_department,
            poste=other_poste
        )
        
        # Se connecter avec le premier utilisateur
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('plan_integration_personnel'))
        
        # Vérifier qu'il voit son plan et pas l'autre
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Plan Développeur Web')
        self.assertNotContains(response, 'Plan Marketing')
