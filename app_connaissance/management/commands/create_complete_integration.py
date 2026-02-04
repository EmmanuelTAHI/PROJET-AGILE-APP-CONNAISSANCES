from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app_connaissance.models import (
    Department, Poste, PlanIntegration, Module, ModuleStep, 
    Quiz, QuizQuestion, QuizChoice, UserModuleStepCompletion, 
    UserQuizAttempt, Progression, UserProfile, KnowledgeItem,
    KnowledgeKind, ModuleKnowledgeItem
)
import random

class Command(BaseCommand):
    help = 'Crée un plan d intégration entièrement fonctionnel avec contenus riches et quiz complets'

    def handle(self, *args, **options):
        self.stdout.write('Création du plan d intégration entièrement fonctionnel...')

        # Récupérer l'utilisateur bk
        try:
            user = User.objects.get(username='bk')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Utilisateur bk non trouvé. Exécutez d abord create_test_user'))
            return

        # Récupérer le profil et le plan
        profile = UserProfile.objects.filter(user=user).select_related('poste', 'poste__plan_integration', 'department').first()
        if not profile or not profile.poste or not profile.poste.plan_integration:
            self.stdout.write(self.style.ERROR('Aucun plan d intégration trouvé pour bk'))
            return

        plan = profile.poste.plan_integration
        department = profile.department
        
        self.stdout.write(f'Plan: {plan.titre}')
        self.stdout.write(f'Département: {department.name}')

        # Créer les kinds de connaissances
        self._create_knowledge_kinds()
        
        # Récupérer tous les modules et créer des contenus riches
        modules = list(plan.modules.prefetch_related('steps', 'quiz', 'quiz__questions', 'quiz__questions__choices').all())
        
        for i, module in enumerate(modules):
            self.stdout.write(f'\n📚 Module {i+1}: {module.titre}')
            
            # Créer ou mettre à jour le quiz avec des questions riches
            quiz = self._create_rich_quiz(module, department)
            
            # Créer des connaissances riches pour ce module
            self._create_rich_knowledge_items(module, department)
            
            # Créer des étapes détaillées si elles n'existent pas
            if not module.steps.exists():
                self._create_detailed_steps(module)
        
        # Créer une progression réaliste
        self._create_realistic_progression(user, plan)
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Plan d intégration entièrement fonctionnel créé!'))
        self.stdout.write('\n📋 Ce que vous pouvez maintenant faire:')
        self.stdout.write('  ✅ Voir tous les contenus détaillés des modules')
        self.stdout.write('  ✅ Consulter les connaissances liées (articles, vidéos, procédures)')
        self.stdout.write('  ✅ Passer des quiz complets avec questions pertinentes')
        self.stdout.write('  ✅ Suivre votre progression étape par étape')
        self.stdout.write('  ✅ Interagir avec toutes les fonctionnalités')

    def _create_knowledge_kinds(self):
        """Crée les types de connaissances"""
        kinds_data = [
            {'name': 'Guide pratique', 'slug': 'guide-pratique'},
            {'name': 'Procédure', 'slug': 'procedure'},
            {'name': 'Vidéo', 'slug': 'video'},
            {'name': 'Document', 'slug': 'document'},
            {'name': 'Article', 'slug': 'article'},
            {'name': 'Tutoriel', 'slug': 'tutoriel'},
        ]
        
        for kind_data in kinds_data:
            kind, created = KnowledgeKind.objects.get_or_create(
                slug=kind_data['slug'],
                defaults={'name': kind_data['name']}
            )
            if created:
                self.stdout.write(f'  📝 Kind créé: {kind.name}')

    def _create_rich_quiz(self, module, department):
        """Crée un quiz riche et pertinent pour le module"""
        # Supprimer l'ancien quiz s'il existe
        if hasattr(module, 'quiz') and module.quiz:
            module.quiz.delete()
        
        quiz = Quiz.objects.create(
            module=module,
            titre=f"Quiz - {module.titre}",
            seuil_reussite_pct=70
        )

        # Questions riches selon le type de module
        questions_data = self._get_questions_for_module(module, department)
        
        for i, q_data in enumerate(questions_data):
            question = QuizQuestion.objects.create(
                quiz=quiz,
                enonce=q_data["question"],
                ordre=i + 1
            )

            for j, choice_data in enumerate(q_data["choices"]):
                QuizChoice.objects.create(
                    question=question,
                    texte=choice_data["text"],
                    is_correct=choice_data["correct"],
                )

        self.stdout.write(f'  📝 Quiz créé: {quiz.titre} ({len(questions_data)} questions)')
        return quiz

    def _get_questions_for_module(self, module, department):
        """Génère des questions pertinentes selon le module"""
        module_title = module.titre.lower()
        
        if "découverte" in module_title and "entreprise" in module_title:
            return [
                {
                    "question": "Quelle est la mission principale de notre entreprise ?",
                    "choices": [
                        {"text": "Développer des solutions innovantes pour nos clients", "correct": True},
                        {"text": "Vendre des produits en ligne", "correct": False},
                        {"text": "Fournir des services de consulting", "correct": False},
                        {"text": "Créer des applications mobiles", "correct": False},
                    ]
                }
            ]
        
        elif "département" in module_title and "informatique" in module_title.lower():
            return [
                {
                    "question": "Quel est le rôle principal du département informatique ?",
                    "choices": [
                        {"text": "Assurer la stabilité et l'évolution des systèmes", "correct": True},
                        {"text": "Gérer uniquement les ordinateurs", "correct": False},
                        {"text": "Faire du marketing digital", "correct": False},
                        {"text": "Vendre des logiciels", "correct": False},
                    ]
                }
            ]
        
        elif "développeur" in module_title or "poste" in module_title:
            return [
                {
                    "question": "Quelle est votre principale responsabilité en tant que développeur ?",
                    "choices": [
                        {"text": "Produire du code propre et maintenable", "correct": True},
                        {"text": "Faire uniquement des présentations", "correct": False},
                        {"text": "Gérer le commercial", "correct": False},
                        {"text": "Nettoyer les bureaux", "correct": False},
                    ]
                }
            ]
        
        elif "outils" in module_title or "systèmes" in module_title:
            return [
                {
                    "question": "Quel outil utilisez-vous pour le suivi des tâches ?",
                    "choices": [
                        {"text": "Jira ou Trello avec méthodologie agile", "correct": True},
                        {"text": "Post-it sur un mur", "correct": False},
                        {"text": "Excel de base", "correct": False},
                        {"text": "Aucun outil de suivi", "correct": False},
                    ]
                }
            ]
        
        else:
            return [
                {
                    "question": f"Quel est l'objectif principal de {module.titre} ?",
                    "choices": [
                        {"text": "Acquérir les compétences nécessaires", "correct": True},
                        {"text": "Perdre du temps", "correct": False},
                        {"text": "Faire joli sur le CV", "correct": False},
                        {"text": "Éviter de travailler", "correct": False},
                    ]
                }
            ]

    def _create_rich_knowledge_items(self, module, department):
        """Crée des connaissances riches et détaillées pour le module"""
        # Supprimer anciennes connaissances liées
        ModuleKnowledgeItem.objects.filter(module=module).delete()
        
        knowledge_data = self._get_knowledge_content_for_module(module, department)
        
        for i, k_data in enumerate(knowledge_data):
            kind = KnowledgeKind.objects.filter(slug=k_data['kind_slug']).first()
            
            knowledge = KnowledgeItem.objects.create(
                title=k_data['title'],
                description=k_data['description'],
                kind=kind,
                department=department,
                author='Équipe Integration',
                content=k_data['content'],
                status='published',
                read_time_min=k_data['read_time'],
                video_url=k_data.get('video_url', '')
            )
            
            # Lier la connaissance au module
            ModuleKnowledgeItem.objects.create(
                module=module,
                knowledge_item=knowledge,
                ordre=i + 1
            )
            
            self.stdout.write(f'    📄 {knowledge.title} ({kind.name})')

    def _get_knowledge_content_for_module(self, module, department):
        """Génère le contenu riche selon le module"""
        module_title = module.titre.lower()
        
        if "découverte" in module_title and "entreprise" in module_title:
            return [
                {
                    'title': 'Notre histoire et nos valeurs',
                    'description': 'Découvrez l\'histoire de notre entreprise et les valeurs qui nous animent',
                    'kind_slug': 'article',
                    'read_time': 8,
                    'content': '<h2>Notre histoire</h2><p>Fondée en 2015, notre entreprise a su évoluer pour devenir un leader dans notre domaine.</p>'
                }
            ]
        
        elif "département" in module_title and "informatique" in module_title.lower():
            return [
                {
                    'title': 'Guide du développeur chez nous',
                    'description': 'Tout ce qu\'il faut savoir pour être efficace dans notre équipe tech',
                    'kind_slug': 'guide-pratique',
                    'read_time': 12,
                    'content': '<h2>Bienvenue dans l\'équipe technique !</h2><h3>Notre stack technique</h3><ul><li>React, TypeScript</li><li>Python/Django</li><li>Docker</li></ul>'
                }
            ]
        
        elif "développeur" in module_title or "poste" in module_title:
            return [
                {
                    'title': 'Missions et responsabilités du développeur',
                    'description': 'Votre rôle détaillé au sein de l\'équipe',
                    'kind_slug': 'guide-pratique',
                    'read_time': 10,
                    'content': '<h2>Votre rôle de développeur</h2><h3>Missions principales</h3><ul><li>Développement</li><li>Qualité</li><li>Collaboration</li></ul>'
                }
            ]
        
        elif "outils" in module_title or "systèmes" in module_title:
            return [
                {
                    'title': 'Guide des accès et permissions',
                    'description': 'Tous vos accès aux systèmes et outils',
                    'kind_slug': 'guide-pratique',
                    'read_time': 8,
                    'content': '<h2>Vos accès principaux</h2><h3>Développement</h3><ul><li>GitHub/GitLab</li><li>VS Code</li><li>Docker</li></ul>'
                }
            ]
        
        else:
            return [
                {
                    'title': f'Guide complet : {module.titre}',
                    'description': 'Ressources complètes pour ce module',
                    'kind_slug': 'guide-pratique',
                    'read_time': 10,
                    'content': f'<h2>{module.titre}</h2><p>Ce guide vous accompagnera dans votre apprentissage.</p>'
                }
            ]

    def _create_detailed_steps(self, module):
        """Crée des étapes détaillées pour un module"""
        steps_data = self._get_steps_for_module(module)
        
        for i, step_title in enumerate(steps_data):
            ModuleStep.objects.create(
                module=module,
                titre=step_title,
                ordre=i + 1
            )
        
        self.stdout.write(f'  📋 {len(steps_data)} étapes créées')

    def _get_steps_for_module(self, module):
        """Génère les étapes selon le module"""
        module_title = module.titre.lower()
        
        if "découverte" in module_title and "entreprise" in module_title:
            return [
                'Lire la présentation de l\'entreprise',
                'Comprendre nos valeurs et culture',
                'Explorer l\'organigramme',
                'Rencontrer les membres clés',
                'Visiter les locaux et équipements'
            ]
        
        elif "département" in module_title and "informatique" in module_title.lower():
            return [
                'Comprendre l\'organisation du département',
                'Installer l\'environnement de développement',
                'Lire les guides techniques',
                'Configurer les accès aux outils',
                'Participer à la première réunion d\'équipe'
            ]
        
        elif "développeur" in module_title or "poste" in module_title:
            return [
                'Comprendre les missions principales',
                'Analyser les compétences requises',
                'Étudier les objectifs de performance',
                'Rencontrer le manager et le mentor',
                'Définir le plan de développement personnel'
            ]
        
        elif "outils" in module_title or "systèmes" in module_title:
            return [
                'Configurer tous les accès systèmes',
                'Maîtriser les outils de communication',
                'Apprendre les procédures de sécurité',
                'Tester l\'environnement de développement',
                'Valider la compréhension des bonnes pratiques'
            ]
        
        else:
            return [
                'Lire la documentation du module',
                'Compléter les exercices pratiques',
                'Valider les connaissances acquises',
                'Préparer le quiz final'
            ]

    def _create_realistic_progression(self, user, plan):
        """Crée une progression réaliste et partielle"""
        modules = list(plan.modules.prefetch_related('steps', 'quiz').all())
        
        # Simuler 60% de progression
        total_steps = sum(len(module.steps.all()) for module in modules)
        completed_steps = 0
        
        for i, module in enumerate(modules):
            steps = list(module.steps.all())
            steps_to_complete = len(steps) // 2 if i < len(modules) - 1 else len(steps)
            
            for j, step in enumerate(steps[:steps_to_complete]):
                completion, created = UserModuleStepCompletion.objects.get_or_create(
                    user=user,
                    module_step=step
                )
                if created:
                    completed_steps += 1
            
            # Simuler quiz réussis pour les premiers modules
            if i < len(modules) - 1 and hasattr(module, 'quiz') and module.quiz:
                UserQuizAttempt.objects.get_or_create(
                    user=user,
                    quiz=module.quiz,
                    defaults={'score_pct': 85, 'passed': True}
                )
        
        # Calculer et sauvegarder la progression
        progression_percentage = round((completed_steps / total_steps) * 100) if total_steps > 0 else 0
        
        progression, created = Progression.objects.get_or_create(
            user=user,
            plan=plan,
            defaults={'pourcentage': progression_percentage}
        )
        
        if not created:
            progression.pourcentage = progression_percentage
            progression.save()
        
        self.stdout.write(f'📊 Progression finale: {progression_percentage}% ({completed_steps}/{total_steps} étapes)')
