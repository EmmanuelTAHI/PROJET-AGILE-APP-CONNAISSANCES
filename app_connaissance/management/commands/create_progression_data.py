from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app_connaissance.models import (
    Department, Poste, PlanIntegration, Module, ModuleStep, 
    Quiz, QuizQuestion, QuizChoice, UserModuleStepCompletion, 
    UserQuizAttempt, Progression, UserProfile
)

class Command(BaseCommand):
    help = 'Crée des fausses données de progression complètes pour l utilisateur bk'

    def handle(self, *args, **options):
        self.stdout.write('Création des fausses données de progression pour bk...')

        # Récupérer l'utilisateur bk
        try:
            user = User.objects.get(username='bk')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Utilisateur bk non trouvé. Exécutez d abord create_test_user'))
            return

        # Récupérer le profil et le plan
        profile = UserProfile.objects.filter(user=user).select_related('poste', 'poste__plan_integration').first()
        if not profile or not profile.poste or not profile.poste.plan_integration:
            self.stdout.write(self.style.ERROR('Aucun plan d intégration trouvé pour bk'))
            return

        plan = profile.poste.plan_integration
        self.stdout.write(f'Plan trouvé: {plan.titre}')

        # Récupérer tous les modules du plan
        modules = list(plan.modules.prefetch_related('steps', 'quiz', 'quiz__questions', 'quiz__questions__choices').all())
        
        if not modules:
            self.stdout.write(self.style.ERROR('Aucun module trouvé dans le plan'))
            return

        self.stdout.write(f'{len(modules)} modules trouvés')

        # Simuler une progression partielle (50% des étapes complétées)
        completed_steps = 0
        total_steps = 0

        for i, module in enumerate(modules):
            # Créer des quiz si ils n'existent pas
            if not hasattr(module, 'quiz') or not module.quiz:
                quiz = self._create_quiz_for_module(module)
                module.quiz = quiz
            else:
                quiz = module.quiz

            # Traiter les étapes du module
            steps = list(module.steps.all())
            total_steps += len(steps)

            # Compléter environ 50% des étapes selon le module
            steps_to_complete = len(steps) // 2 if i < len(modules) - 1 else len(steps)  # Dernier module complètement
            
            for j, step in enumerate(steps[:steps_to_complete]):
                completion, created = UserModuleStepCompletion.objects.get_or_create(
                    user=user,
                    module_step=step
                )
                if created:
                    completed_steps += 1
                    self.stdout.write(f'  ✓ Étape complétée: {step.titre}')

            # Simuler le quiz pour certains modules
            if i < len(modules) - 1:  # Pas pour le dernier module
                self._create_quiz_attempt(user, quiz, passed=True)

        # Créer la progression globale
        progression_percentage = round((completed_steps / total_steps) * 100) if total_steps > 0 else 0
        
        progression, created = Progression.objects.get_or_create(
            user=user,
            plan=plan,
            defaults={'pourcentage': progression_percentage}
        )
        
        if not created:
            progression.pourcentage = progression_percentage
            progression.save()

        self.stdout.write(self.style.SUCCESS(f'✅ Progression créée: {progression_percentage}% ({completed_steps}/{total_steps} étapes)'))
        
        # Afficher le résumé
        self.stdout.write('\n📋 RÉSUMÉ DU PLAN D INTÉGRATION:')
        self.stdout.write(f'👤 Utilisateur: {user.username} ({profile.display_name})')
        self.stdout.write(f'🏢 Département: {profile.department.name}')
        self.stdout.write(f'💼 Poste: {profile.poste.intitule}')
        self.stdout.write(f'📚 Plan: {plan.titre}')
        self.stdout.write(f'📊 Progression: {progression_percentage}%')
        self.stdout.write(f'📝 Modules: {len(modules)}')
        self.stdout.write(f'✅ Étapes complétées: {completed_steps}/{total_steps}')
        
        self.stdout.write('\n🎯 OBJECTIFS RESTANTS:')
        remaining_steps = total_steps - completed_steps
        if remaining_steps > 0:
            self.stdout.write(f'  • Compléter {remaining_steps} étapes restantes')
            self.stdout.write(f'  • Passer les quiz des modules restants')
        
        self.stdout.write(self.style.SUCCESS('\n🚀 Plan d intégration entièrement fonctionnel prêt!'))

    def _create_quiz_for_module(self, module):
        """Crée un quiz avec questions et réponses pour un module"""
        quiz = Quiz.objects.create(
            module=module,
            titre=f"Quiz - {module.titre}",
            seuil_reussite_pct=70
        )

        # Questions selon le type de module
        questions_data = [
            {
                "question": f"Quelle est l'importance de {module.titre} dans votre intégration ?",
                "choices": ["Très importante", "Importante", "Moyenne", "Faible"],
                "correct": 0
            },
            {
                "question": f"Combien de temps faut-il prévoir pour maîtriser {module.titre} ?",
                "choices": ["1-2 jours", "3-5 jours", "1 semaine", "Plus d'une semaine"],
                "correct": 1
            },
            {
                "question": f"Quelle compétence principale développez-vous avec {module.titre} ?",
                "choices": ["Technique", "Communication", "Organisation", "Leadership"],
                "correct": 0 if "Développeur" in module.titre or "Outils" in module.titre else 1
            }
        ]

        for i, q_data in enumerate(questions_data):
            question = QuizQuestion.objects.create(
                quiz=quiz,
                enonce=q_data["question"],
                ordre=i + 1
            )

            for j, choice_text in enumerate(q_data["choices"]):
                QuizChoice.objects.create(
                    question=question,
                    texte=choice_text,
                    is_correct=(j == q_data["correct"])
                )

        self.stdout.write(f'  📝 Quiz créé: {quiz.titre} ({len(questions_data)} questions)')
        return quiz

    def _create_quiz_attempt(self, user, quiz, passed=True):
        """Crée une tentative de quiz"""
        score = 85 if passed else 45  # Score simulé
        
        attempt, created = UserQuizAttempt.objects.get_or_create(
            user=user,
            quiz=quiz,
            defaults={'score_pct': score, 'passed': passed}
        )
        
        if created:
            status = "✅ Réussi" if passed else "❌ Échoué"
            self.stdout.write(f'  {status} Quiz: {quiz.titre} ({score}%)')
        
        return attempt
