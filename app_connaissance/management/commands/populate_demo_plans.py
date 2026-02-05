from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app_connaissance.models import (
    Department, Poste, PlanIntegration, Module, ModuleStep, 
    KnowledgeItem, KnowledgeKind, ModuleKnowledgeItem, UserProfile
)
import random

class Command(BaseCommand):
    help = 'Crée des plans d\'intégration de démonstration avec connaissances liées'

    def handle(self, *args, **options):
        self.stdout.write('Création des plans d\'intégration de démonstration...')
        
        # Création des kinds de connaissances si inexistants
        kinds_data = [
            {'name': 'Guide pratique', 'slug': 'guide-pratique'},
            {'name': 'Procédure', 'slug': 'procedure'},
            {'name': 'Vidéo', 'slug': 'video'},
            {'name': 'Document', 'slug': 'document'},
        ]
        
        for kind_data in kinds_data:
            kind, created = KnowledgeKind.objects.get_or_create(
                slug=kind_data['slug'],
                defaults={'name': kind_data['name']}
            )
            if created:
                self.stdout.write(f'Kind créé: {kind.name}')
        
        # Récupérer les départements et postes existants
        departments = list(Department.objects.all())
        if not departments:
            self.stdout.write(self.style.ERROR('Aucun département trouvé. Créez d\'abord des départements.'))
            return
        
        # Pour chaque département avec des postes, créer un plan d'intégration
        for dept in departments:
            postes = list(dept.postes.all())
            if not postes:
                continue
                
            for poste in postes:
                # Vérifier si le poste a déjà un plan
                if poste.plan_integration:
                    self.stdout.write(f'Le poste {poste.intitule} a déjà un plan d\'intégration.')
                    continue
                
                # Créer le plan d'intégration
                plan = PlanIntegration.objects.create(
                    titre=f'Plan d\'intégration - {poste.intitule}',
                    description=f'Parcours de formation complet pour le poste de {poste.intitule} dans le département {dept.name}',
                    duree_estimee_jours=random.randint(5, 15)
                )
                
                poste.plan_integration = plan
                poste.save()
                
                self.stdout.write(f'Plan créé pour {poste.intitule}: {plan.titre}')
                
                # Créer des modules pour ce plan
                modules_data = [
                    {
                        'titre': 'Découverte de l\'entreprise',
                        'duree': 2,
                        'steps': ['Présentation de l\'entreprise', 'Valeurs et culture', 'Organigramme']
                    },
                    {
                        'titre': f'Découverte du département {dept.name}',
                        'duree': 3,
                        'steps': ['Présentation de l\'équipe', 'Processus du département', 'Outils utilisés']
                    },
                    {
                        'titre': f'Formation au poste de {poste.intitule}',
                        'duree': 4,
                        'steps': ['Missions principales', 'Responsabilités', 'Objectifs']
                    },
                    {
                        'titre': 'Outils et systèmes',
                        'duree': 2,
                        'steps': ['Accès aux systèmes', 'Logiciels métiers', 'Procédures de sécurité']
                    }
                ]
                
                for i, module_data in enumerate(modules_data, 1):
                    module = Module.objects.create(
                        titre=module_data['titre'],
                        ordre=i,
                        plan=plan,
                        duree_jours=module_data['duree']
                    )
                    
                    # Créer les étapes du module
                    for j, step_title in enumerate(module_data['steps'], 1):
                        ModuleStep.objects.create(
                            module=module,
                            titre=step_title,
                            ordre=j
                        )
                    
                    # Créer des connaissances pour ce module
                    self._create_knowledge_for_module(module, dept, poste)
                
                self.stdout.write(self.style.SUCCESS(f'  {len(modules_data)} modules créés avec connaissances'))
        
        self.stdout.write(self.style.SUCCESS('Plans d\'intégration de démonstration créés avec succès!'))
    
    def _create_knowledge_for_module(self, module, department, poste):
        """Crée des connaissances liées à un module"""
        kinds = list(KnowledgeKind.objects.all())
        if not kinds:
            return
        
        # Connaissances spécifiques selon le module
        knowledge_templates = {
            'Découverte de l\'entreprise': [
                {'title': 'Historique et valeurs de l\'entreprise', 'kind': 'Guide pratique'},
                {'title': 'Présentation des services', 'kind': 'Document'},
                {'title': 'Politique RH et charte', 'kind': 'Procédure'},
            ],
            'Découverte du département': [
                {'title': f'Organisation du département {department.name}', 'kind': 'Guide pratique'},
                {'title': 'Processus métier principaux', 'kind': 'Procédure'},
                {'title': 'Présentation de l\'équipe', 'kind': 'Document'},
            ],
            'Formation au poste': [
                {'title': f'Description du poste de {poste.intitule}', 'kind': 'Guide pratique'},
                {'title': 'Compétences requises', 'kind': 'Document'},
                {'title': 'Objectifs et indicateurs', 'kind': 'Procédure'},
            ],
            'Outils et systèmes': [
                {'title': 'Guide des accès informatiques', 'kind': 'Guide pratique'},
                {'title': 'Sécurité des données', 'kind': 'Procédure'},
                {'title': 'Logiciels métier', 'kind': 'Vidéo'},
            ],
        }
        
        module_title = module.titre
        templates = knowledge_templates.get(module_title, [
            {'title': f'Connaissance pour {module_title}', 'kind': 'Guide pratique'}
        ])
        
        for i, template in enumerate(templates, 1):
            kind = KnowledgeKind.objects.filter(name=template['kind']).first()
            if not kind:
                kind = kinds[0]  # Default kind
            
            knowledge = KnowledgeItem.objects.create(
                title=template['title'],
                description=f'Description détaillée pour {template["title"]}',
                kind=kind,
                department=department,
                author='Système',
                content=f'<p>Contenu détaillé pour {template["title"]}.</p><p>Ce contenu fait partie du module "{module_title}" du plan d\'intégration.</p>',
                status='published',
                read_time_min=random.randint(5, 20)
            )
            
            # Lier la connaissance au module
            ModuleKnowledgeItem.objects.create(
                module=module,
                knowledge_item=knowledge,
                ordre=i
            )
