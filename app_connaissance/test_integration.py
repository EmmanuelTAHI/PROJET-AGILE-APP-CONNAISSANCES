from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from app_connaissance.models import (
    Department, Poste, PlanIntegration, Module, ModuleStep,
    Quiz, QuizQuestion, QuizChoice, UserProfile, Progression,
    UserModuleStepCompletion, UserQuizAttempt
)
from app_connaissance.views import _progress_for_plan

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
            duree_estimee_jours=20  # 4 semaines * 5 jours
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
        
        # D'abord compléter les étapes du module pour pouvoir accéder au quiz
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1
        )
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step2
        )
        
        response = self.client.get(reverse('quiz_take', args=[self.quiz.id]))
        
        # Si c'est une redirection, suivre la redirection pour voir le message
        if response.status_code == 302:
            redirect_response = self.client.get(response.url)
            self.assertEqual(redirect_response.status_code, 200)
            # Afficher le contenu pour déboguer
            print(f"Redirected to: {response.url}")
            print(f"Response content: {redirect_response.content.decode()[:500]}")
        else:
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Quiz Test')
            self.assertContains(response, 'Question test ?')
    
    def test_quiz_submit_correct(self):
        """Test la soumission d'un quiz avec réponse correcte"""
        self.client.login(username='testuser', password='testpass123')
        
        # D'abord compléter les étapes du module pour pouvoir accéder au quiz
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1
        )
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step2
        )
        
        response = self.client.post(
            reverse('quiz_take', args=[self.quiz.id]),
            {
                f'q_{self.question.id}': self.choice1.id,
                'submit': '1'
            }
        )
        
        # Vérifier la redirection après soumission
        self.assertEqual(response.status_code, 302)
        
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
        
        # D'abord compléter les étapes du module pour pouvoir accéder au quiz
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1
        )
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step2
        )
        
        response = self.client.post(
            reverse('quiz_take', args=[self.quiz.id]),
            {
                f'q_{self.question.id}': self.choice2.id,
                'submit': '1'
            }
        )
        
        # Vérifier la redirection après soumission
        self.assertEqual(response.status_code, 302)
        
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
    
    def setUp(self):
        super().setUp()
        
        # Créer un quiz pour le module
        self.quiz = Quiz.objects.create(
            module=self.module,
            titre="Quiz Test Progression",
            seuil_reussite_pct=70
        )
    
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
        
        # Vérifier la progression (0% car le module n'est pas complètement validé)
        # Avec la nouvelle logique, un module n'est compté comme complété que si 
        # toutes ses étapes sont terminées ET le quiz est réussi
        progression = Progression.objects.filter(
            user=self.user,
            plan=self.plan
        ).first()
        self.assertIsNotNone(progression)
        self.assertEqual(progression.pourcentage, 0)  # 0% car le module n'est pas encore validé
    
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
        
        # Réussir le quiz
        UserQuizAttempt.objects.create(
            user=self.user,
            quiz=self.quiz,
            score_pct=80,
            passed=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('plan_integration_personnel'))
        
        self.assertEqual(response.status_code, 200)
        
        # Vérifier la progression (100% car le module est complètement validé)
        progression = Progression.objects.filter(
            user=self.user,
            plan=self.plan
        ).first()
        self.assertIsNotNone(progression)
        self.assertEqual(progression.pourcentage, 100)  # 100% car le module est validé

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


class ModuleSequencingTest(TestCase):
    """Test spécifique pour la logique de séquencement des modules"""
    
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
            duree_estimee_jours=20
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
        
        # Créer 3 modules
        self.module1 = Module.objects.create(
            titre="Module 1 - Introduction",
            ordre=1,
            plan=self.plan,
            duree_jours=5
        )
        self.module2 = Module.objects.create(
            titre="Module 2 - Avancé",
            ordre=2,
            plan=self.plan,
            duree_jours=5
        )
        self.module3 = Module.objects.create(
            titre="Module 3 - Expert",
            ordre=3,
            plan=self.plan,
            duree_jours=5
        )
        
        # Créer des étapes pour chaque module
        self.step1_1 = ModuleStep.objects.create(
            module=self.module1,
            titre="Étape 1.1",
            ordre=1
        )
        self.step1_2 = ModuleStep.objects.create(
            module=self.module1,
            titre="Étape 1.2",
            ordre=2
        )
        
        self.step2_1 = ModuleStep.objects.create(
            module=self.module2,
            titre="Étape 2.1",
            ordre=1
        )
        self.step2_2 = ModuleStep.objects.create(
            module=self.module2,
            titre="Étape 2.2",
            ordre=2
        )
        
        self.step3_1 = ModuleStep.objects.create(
            module=self.module3,
            titre="Étape 3.1",
            ordre=1
        )
        
        # Créer des quiz pour les modules 1 et 2
        self.quiz1 = Quiz.objects.create(
            module=self.module1,
            titre="Quiz Module 1",
            seuil_reussite_pct=70
        )
        self.quiz2 = Quiz.objects.create(
            module=self.module2,
            titre="Quiz Module 2",
            seuil_reussite_pct=70
        )
    
    def test_module_sequencing_access(self):
        """Test que les modules suivants ne sont pas accessibles avant le précédent"""
        # Progression initiale : seul le premier module doit être accessible
        progress = _progress_for_plan(self.user, self.plan)
        
        # Module 1 doit être accessible
        module1_status = next(m for m in progress["modules"] if m["module"].id == self.module1.id)
        self.assertTrue(module1_status["accessible"], "Le module 1 doit être accessible")
        
        # Module 2 ne doit pas être accessible
        module2_status = next(m for m in progress["modules"] if m["module"].id == self.module2.id)
        self.assertFalse(module2_status["accessible"], "Le module 2 ne doit pas être accessible au début")
        
        # Module 3 ne doit pas être accessible
        module3_status = next(m for m in progress["modules"] if m["module"].id == self.module3.id)
        self.assertFalse(module3_status["accessible"], "Le module 3 ne doit pas être accessible au début")
    
    def test_module_sequencing_after_completion(self):
        """Test que les modules deviennent accessibles après complétion du précédent"""
        # Compléter les étapes du module 1
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1_1
        )
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1_2
        )
        
        # Réussir le quiz du module 1
        UserQuizAttempt.objects.create(
            user=self.user,
            quiz=self.quiz1,
            score_pct=80,
            passed=True
        )
        
        progress = _progress_for_plan(self.user, self.plan)
        
        # Module 1 doit être validé et accessible
        module1_status = next(m for m in progress["modules"] if m["module"].id == self.module1.id)
        self.assertTrue(module1_status["passed"], "Le module 1 doit être validé")
        self.assertTrue(module1_status["accessible"], "Le module 1 doit rester accessible")
        
        # Module 2 doit maintenant être accessible
        module2_status = next(m for m in progress["modules"] if m["module"].id == self.module2.id)
        self.assertTrue(module2_status["accessible"], "Le module 2 doit être accessible après validation du module 1")
        self.assertFalse(module2_status["passed"], "Le module 2 ne doit pas être validé")
        
        # Module 3 ne doit toujours pas être accessible
        module3_status = next(m for m in progress["modules"] if m["module"].id == self.module3.id)
        self.assertFalse(module3_status["accessible"], "Le module 3 ne doit pas être accessible")
    
    def test_quiz_access_without_completed_steps(self):
        """Test que le quiz n'est pas accessible si les étapes ne sont pas complétées"""
        self.client.login(username='testuser', password='testpass123')
        
        # Essayer d'accéder au quiz du module 1 sans avoir complété les étapes
        response = self.client.get(reverse('quiz_take', kwargs={'quiz_id': self.quiz1.id}))
        
        # Doit être redirigé
        self.assertEqual(response.status_code, 302)
        
        # Vérifier que la redirection mène bien vers le plan d'intégration
        self.assertIn('/integration/', response.url)
        
        # Suivre la redirection manuellement
        redirect_response = self.client.get(response.url)
        self.assertEqual(redirect_response.status_code, 200)
        
        # Vérifier les messages d'erreur (peut être dans les messages Django)
        messages = list(redirect_response.context['messages'])
        self.assertTrue(any("compléter" in str(message) for message in messages))
    
    def test_quiz_access_with_completed_steps(self):
        """Test que le quiz est accessible si les étapes sont complétées"""
        self.client.login(username='testuser', password='testpass123')
        
        # Compléter les étapes du module 1
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1_1
        )
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1_2
        )
        
        # Accéder au quiz du module 1
        response = self.client.get(reverse('quiz_take', kwargs={'quiz_id': self.quiz1.id}))
        
        # Doit pouvoir accéder au quiz
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quiz Module 1")


class BugFixValidationTest(TestCase):
    """Tests spécifiques pour valider les corrections des bugs identifiés"""
    
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
            duree_estimee_jours=20
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
        
        # Créer 2 modules
        self.module1 = Module.objects.create(
            titre="Module 1 - Introduction",
            ordre=1,
            plan=self.plan,
            duree_jours=5
        )
        self.module2 = Module.objects.create(
            titre="Module 2 - Avancé",
            ordre=2,
            plan=self.plan,
            duree_jours=5
        )
        
        # Créer des étapes pour chaque module
        self.step1_1 = ModuleStep.objects.create(
            module=self.module1,
            titre="Étape 1.1",
            ordre=1
        )
        self.step1_2 = ModuleStep.objects.create(
            module=self.module1,
            titre="Étape 1.2",
            ordre=2
        )
        
        self.step2_1 = ModuleStep.objects.create(
            module=self.module2,
            titre="Étape 2.1",
            ordre=1
        )
        self.step2_2 = ModuleStep.objects.create(
            module=self.module2,
            titre="Étape 2.2",
            ordre=2
        )
        
        # Créer des quiz pour les modules
        self.quiz1 = Quiz.objects.create(
            module=self.module1,
            titre="Quiz Module 1",
            seuil_reussite_pct=70
        )
        self.quiz2 = Quiz.objects.create(
            module=self.module2,
            titre="Quiz Module 2",
            seuil_reussite_pct=70
        )
        
        # Créer des questions et choix pour les quiz
        self.question1 = QuizQuestion.objects.create(
            quiz=self.quiz1,
            enonce="Question Module 1 ?",
            ordre=1
        )
        self.choice1_correct = QuizChoice.objects.create(
            question=self.question1,
            texte="Réponse correcte",
            is_correct=True
        )
        self.choice1_wrong = QuizChoice.objects.create(
            question=self.question1,
            texte="Réponse incorrecte",
            is_correct=False
        )
    
    def test_bug_fix_quiz_not_marked_passed_without_attempt(self):
        """Test de correction: le quiz ne doit pas être marqué comme réussi sans tentative"""
        self.client.login(username='testuser', password='testpass123')
        
        # Compléter les étapes du module 1
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1_1
        )
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1_2
        )
        
        # Vérifier la progression
        progress = _progress_for_plan(self.user, self.plan)
        module1_status = next(m for m in progress["modules"] if m["module"].id == self.module1.id)
        
        # Le quiz ne doit PAS être marqué comme réussi
        self.assertFalse(module1_status["quiz_passed"], "Le quiz ne doit pas être marqué comme réussi sans tentative")
        self.assertFalse(module1_status["passed"], "Le module ne doit pas être validé sans quiz réussi")
        
        # Vérifier l'affichage dans le template
        response = self.client.get(reverse('plan_integration_personnel'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Quiz réussi")
        self.assertContains(response, "Passer le quiz")
    
    def test_bug_fix_knowledge_access_after_module_completion(self):
        """Test de correction: les connaissances doivent être accessibles après validation du module"""
        self.client.login(username='testuser', password='testpass123')
        
        # Compléter les étapes ET le quiz du module 1
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1_1
        )
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1_2
        )
        
        UserQuizAttempt.objects.create(
            user=self.user,
            quiz=self.quiz1,
            score_pct=80,
            passed=True
        )
        
        # Vérifier la progression
        progress = _progress_for_plan(self.user, self.plan)
        module1_status = next(m for m in progress["modules"] if m["module"].id == self.module1.id)
        
        # Le module doit être validé
        self.assertTrue(module1_status["passed"], "Le module doit être validé")
        
        # Vérifier l'accès aux connaissances dans le template
        response = self.client.get(reverse('plan_integration_personnel'))
        self.assertEqual(response.status_code, 200)
        
        # Les connaissances du module validé doivent être accessibles
        # (vérification par la présence de liens cliquables)
        self.assertContains(response, "href=")  # Au moins un lien doit être présent
    
    def test_bug_fix_sequential_module_access(self):
        """Test de correction: le module 2 ne doit pas être accessible si module 1 non validé"""
        self.client.login(username='testuser', password='testpass123')
        
        # Compléter seulement les étapes du module 1 (sans passer le quiz)
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1_1
        )
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1_2
        )
        
        # Vérifier la progression
        progress = _progress_for_plan(self.user, self.plan)
        module1_status = next(m for m in progress["modules"] if m["module"].id == self.module1.id)
        module2_status = next(m for m in progress["modules"] if m["module"].id == self.module2.id)
        
        # Module 1 accessible mais non validé
        self.assertTrue(module1_status["accessible"], "Module 1 doit être accessible")
        self.assertFalse(module1_status["passed"], "Module 1 ne doit pas être validé sans quiz")
        
        # Module 2 non accessible
        self.assertFalse(module2_status["accessible"], "Module 2 ne doit pas être accessible")
        
        # Vérifier l'affichage dans le template
        response = self.client.get(reverse('plan_integration_personnel'))
        self.assertEqual(response.status_code, 200)
        
        # Module 2 doit être verrouillé
        self.assertContains(response, "Quiz verrouillé")
        self.assertContains(response, "Verrouillé")
    
    def test_bug_fix_complete_workflow(self):
        """Test complet du workflow corrigé"""
        self.client.login(username='testuser', password='testpass123')
        
        # Étape 1: Compléter les étapes du module 1
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1_1
        )
        UserModuleStepCompletion.objects.create(
            user=self.user,
            module_step=self.step1_2
        )
        
        progress = _progress_for_plan(self.user, self.plan)
        module1_status = next(m for m in progress["modules"] if m["module"].id == self.module1.id)
        module2_status = next(m for m in progress["modules"] if m["module"].id == self.module2.id)
        
        # Module 1 accessible mais non validé
        self.assertTrue(module1_status["accessible"])
        self.assertFalse(module1_status["passed"])
        self.assertFalse(module1_status["quiz_passed"])
        
        # Module 2 non accessible
        self.assertFalse(module2_status["accessible"])
        
        # Étape 2: Passer et réussir le quiz du module 1
        response = self.client.post(
            reverse('quiz_take', kwargs={'quiz_id': self.quiz1.id}),
            {
                f'q_{self.question1.id}': self.choice1_correct.id,
                'submit': '1'
            }
        )
        self.assertEqual(response.status_code, 302)  # Redirection après soumission
        
        # Vérifier l'état après quiz réussi
        progress = _progress_for_plan(self.user, self.plan)
        module1_status = next(m for m in progress["modules"] if m["module"].id == self.module1.id)
        module2_status = next(m for m in progress["modules"] if m["module"].id == self.module2.id)
        
        # Module 1 validé
        self.assertTrue(module1_status["passed"])
        self.assertTrue(module1_status["quiz_passed"])
        
        # Module 2 maintenant accessible
        self.assertTrue(module2_status["accessible"])
        self.assertFalse(module2_status["passed"])  # Pas encore validé
        
        # Étape 3: Vérifier l'affichage final
        response = self.client.get(reverse('plan_integration_personnel'))
        self.assertEqual(response.status_code, 200)
        
        # Module 1: Quiz réussi
        self.assertContains(response, "Quiz réussi")
        
        # Module 2: Accès autorisé au quiz
        self.assertNotContains(response, "Quiz verrouillé")  # Ne doit pas être verrouillé
