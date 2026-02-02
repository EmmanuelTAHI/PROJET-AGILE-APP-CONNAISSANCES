"""
Commande de gestion : enrichit la base avec de nombreux enregistrements dans chaque modèle.
Usage : python manage.py populate_extended
"""
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from app_connaissance.models import (
    Competence,
    Department,
    Entreprise,
    KnowledgeItem,
    KnowledgeKind,
    KnowledgeVersion,
    Module,
    ModuleKnowledgeItem,
    ModuleStep,
    OnboardingStep,
    PlanIntegration,
    Poste,
    Progression,
    Quiz,
    QuizChoice,
    QuizQuestion,
    Tag,
    UserModuleStepCompletion,
    UserProfile,
    UserQuizAttempt,
)
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Enrichit la base de données avec davantage d'enregistrements dans chaque modèle."

    def handle(self, *args, **options):
        now = timezone.now()

        # ========== ENTREPRISES ==========
        self.stdout.write("Entreprises...")
        entreprises_data = [
            ("TechCorp France",),
            ("InnovSolutions SARL",),
            ("DataFlow Consulting",),
            ("AgileSoft SAS",),
        ]
        entreprises = {}
        for name in entreprises_data:
            ent, _ = Entreprise.objects.get_or_create(name=name[0])
            entreprises[name[0]] = ent

        # ========== DÉPARTEMENTS (lier aux entreprises si pas déjà) ==========
        self.stdout.write("Départements...")
        dept_names = [
            "Développement", "Ressources Humaines", "Marketing", "Finance",
            "Support", "Comptabilité", "Informatique", "Gestion de stocks",
            "Qualité", "Logistique", "Juridique", "Direction"
        ]
        depts = {}
        ent_list = list(entreprises.values())
        for i, name in enumerate(dept_names):
            dept, created = Department.objects.get_or_create(
                name=name,
                defaults={
                    "description": f"Département {name} - Gestion et opérations",
                    "entreprise": ent_list[i % len(ent_list)] if ent_list else None,
                }
            )
            if not created and not dept.entreprise_id and ent_list:
                dept.entreprise = ent_list[i % len(ent_list)]
                dept.save()
            depts[name] = dept

        # ========== UTILISATEURS ET PROFILS ==========
        self.stdout.write("Utilisateurs et profils...")
        users_data = [
            ("admin", "admin@company.com", "Admin", "Principal", "admin", "Direction", None),
            ("manager", "manager@company.com", "Marie", "Dupont", "manager", "Développement", "Manager Développement"),
            ("employee1", "jean@company.com", "Jean", "Martin", "employee", "Développement", "Développeur Frontend"),
            ("employee2", "sophie@company.com", "Sophie", "Bernard", "employee", "Ressources Humaines", "Chargée Recrutement"),
            ("employee3", "pierre@company.com", "Pierre", "Dubois", "employee", "Marketing", "Responsable Marketing"),
            ("employee4", "luc@company.com", "Luc", "Moreau", "employee", "Finance", "Comptable"),
            ("employee5", "anne@company.com", "Anne", "Leroy", "employee", "Support", "Technicien Support"),
            ("employee6", "thomas@company.com", "Thomas", "Simon", "employee", "Développement", "Développeur Backend"),
            ("employee7", "camille@company.com", "Camille", "Michel", "employee", "Marketing", "Community Manager"),
            ("employee8", "alex@company.com", "Alexandre", "Laurent", "employee", "Informatique", "Admin Système"),
            ("employee9", "lea@company.com", "Léa", "Rousseau", "new_employee", "Ressources Humaines", "Stagiaire RH"),
            ("employee10", "hugo@company.com", "Hugo", "Vincent", "employee", "Qualité", "Responsable Qualité"),
            ("manager2", "paul@company.com", "Paul", "Durand", "manager", "Finance", "Responsable Finance"),
        ]
        users = {}
        for username, email, first, last, role, dept_name, poste_name in users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": first,
                    "last_name": last,
                    "is_staff": role == "admin",
                    "is_superuser": role == "admin",
                },
            )
            if created:
                user.set_password("demo123")
                user.save()
            users[username] = user

            dept = depts.get(dept_name) if dept_name else None
            poste = None
            if dept and poste_name:
                poste, _ = Poste.objects.get_or_create(
                    department=dept, intitule=poste_name, defaults={"description": ""}
                )
            display = f"{first} {last}"
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "display_name": display if not UserProfile.objects.filter(display_name=display).exists() else f"{display} ({username})",
                    "role": role,
                    "department": dept,
                    "poste": poste,
                    "type_contrat": "cdi" if role != "new_employee" else "stage",
                    "date_embauche": now.date() - timedelta(days=random.randint(30, 700)),
                },
            )

        # Managers des départements
        dev = depts.get("Développement")
        if dev and "manager" in users:
            dev.manager = users["manager"]
            dev.save()
        fin = depts.get("Finance")
        if fin and "manager2" in users:
            fin.manager = users["manager2"]
            fin.save()

        # ========== TAGS ==========
        self.stdout.write("Tags...")
        tag_names = [
            "onboarding", "sécurité", "PostgreSQL", "CI/CD", "recrutement",
            "JavaScript", "marketing", "qualité", "Python", "Django", "React",
            "API", "DevOps", "Docker", "Kubernetes", "AWS", "tests", "documentation",
            "budget", "comptabilité", "support", "SLA", "RGPD", "conformité"
        ]
        tags = {}
        for name in tag_names:
            t, _ = Tag.objects.get_or_create(name=name)
            tags[name] = t

        # ========== COMPÉTENCES ==========
        self.stdout.write("Compétences...")
        comp_names = [
            "PostgreSQL", "Administration", "DevOps", "CI/CD", "RH", "Recrutement",
            "JavaScript", "Qualité Code", "Marketing", "Digital", "Python", "Django",
            "React", "Communication", "Comptabilité", "Excel", "Support client",
            "Rédaction", "SEO", "Design", "Gestion de projet", "Agile", "Scrum"
        ]
        comps = {}
        for name in comp_names:
            c, _ = Competence.objects.get_or_create(name=name)
            comps[name] = c

        # ========== POSTES (compléter) ==========
        self.stdout.write("Postes...")
        postes_data = [
            ("Développement", "Développeur Frontend"),
            ("Développement", "Développeur Backend"),
            ("Développement", "Manager Développement"),
            ("Développement", "Administrateur BDD"),
            ("Développement", "DevOps Engineer"),
            ("Ressources Humaines", "Chargée Recrutement"),
            ("Ressources Humaines", "Stagiaire RH"),
            ("Marketing", "Responsable Marketing"),
            ("Marketing", "Community Manager"),
            ("Finance", "Comptable"),
            ("Finance", "Responsable Finance"),
            ("Support", "Technicien Support"),
            ("Informatique", "Admin Système"),
            ("Qualité", "Responsable Qualité"),
            ("Logistique", "Chef de dépôt"),
            ("Juridique", "Juriste"),
        ]
        postes_obj = {}
        for dept_name, intitule in postes_data:
            dept = depts.get(dept_name)
            if dept:
                poste, _ = Poste.objects.get_or_create(
                    department=dept, intitule=intitule, defaults={"description": f"Poste {intitule}"}
                )
                postes_obj[(dept_name, intitule)] = poste

        # ========== PLANS D'INTÉGRATION + MODULES + QUIZ ==========
        self.stdout.write("Plans d'intégration, modules et quiz...")
        plans_data = [
            ("Plan Développeur Frontend", "Parcours onboarding développeur frontend", 10,
             [("Introduction à l'entreprise", 3), ("Environnement de développement", 4), ("Standards de code", 3)]),
            ("Plan Développeur Backend", "Parcours onboarding développeur backend", 12,
             [("Architecture backend", 4), ("Bases de données", 3), ("API REST", 5)]),
            ("Plan Chargée Recrutement", "Parcours recrutement", 5,
             [("Processus de recrutement", 2), ("Outils et bonnes pratiques", 3)]),
            ("Plan Responsable Marketing", "Parcours marketing", 5,
             [("Stratégie et canaux", 3), ("Outils digitaux", 2)]),
            ("Plan Comptable", "Parcours comptabilité", 7,
             [("Processus comptable", 3), ("Outil de gestion", 4)]),
            ("Plan Support", "Parcours support client", 4,
             [("Produits et services", 2), ("Outils de ticketing", 2)]),
            ("Plan DevOps", "Parcours DevOps", 14,
             [("Infrastructure", 5), ("CI/CD", 5), ("Monitoring", 4)]),
            ("Plan Admin Système", "Parcours administrateur système", 10,
             [("Sécurité et accès", 3), ("Sauvegardes", 3), ("Monitoring serveurs", 4)]),
            ("Plan Responsable Qualité", "Parcours qualité", 8,
             [("Normes qualité", 3), ("Procédures d'audit", 3), ("Indicateurs et reporting", 2)]),
        ]
        plans = {}
        for titre, desc, duree, modules_data in plans_data:
            plan, _ = PlanIntegration.objects.get_or_create(
                titre=titre,
                defaults={"description": desc, "duree_estimee_jours": duree}
            )
            plans[titre] = plan
            for ordre, (mod_titre, mod_jours) in enumerate(modules_data, 1):
                mod, _ = Module.objects.get_or_create(
                    plan=plan, ordre=ordre,
                    defaults={"titre": mod_titre, "duree_jours": mod_jours}
                )
                # Quiz par module
                quiz, _ = Quiz.objects.get_or_create(
                    module=mod,
                    defaults={"titre": f"Quiz {mod_titre[:30]}", "seuil_reussite_pct": 70}
                )
                # 2 à 4 questions par quiz
                for q_ordre in range(1, 4):
                    q, _ = QuizQuestion.objects.get_or_create(
                        quiz=quiz, ordre=q_ordre,
                        defaults={"enonce": f"Question {q_ordre} du module {mod_titre[:40]} : Quelle est l'étape correcte ?"}
                    )
                    if not q.choices.exists():
                        QuizChoice.objects.create(question=q, texte="Option correcte", is_correct=True)
                        QuizChoice.objects.create(question=q, texte="Option incorrecte 1", is_correct=False)
                        QuizChoice.objects.create(question=q, texte="Option incorrecte 2", is_correct=False)

        # ========== SOUS-ÉTAPES (ModuleStep) par module ==========
        self.stdout.write("Sous-étapes des modules...")
        steps_by_module = {
            "Introduction à l'entreprise": [
                "Présentation à l'équipe",
                "Visite des locaux",
                "Lecture de la charte entreprise",
                "Configuration de la messagerie",
            ],
            "Environnement de développement": [
                "Installation de l'IDE",
                "Configuration de Git",
                "Accès au dépôt de code",
                "Création de la branche personnelle",
            ],
            "Standards de code": [
                "Lecture du guide de style",
                "Configuration Prettier/ESLint",
                "Code review d'un premier PR",
            ],
            "Architecture backend": [
                "Découverte de l'architecture",
                "Lecture de la documentation technique",
                "Lancer le projet en local",
                "Comprendre les services principaux",
            ],
            "Bases de données": [
                "Connexion à la base de dev",
                "Lecture du schéma",
                "Exécuter les migrations",
                "Créer une requête de test",
            ],
            "API REST": [
                "Tester les endpoints avec Postman",
                "Comprendre l'authentification",
                "Documentation Swagger",
                "Implémenter un endpoint simple",
            ],
            "Processus de recrutement": [
                "Formation ATS (logiciel recrutement)",
                "Lecture des fiches de poste types",
                "Préparation d'un premier entretien fictif",
            ],
            "Outils et bonnes pratiques": [
                "Configuration LinkedIn Recruiter",
                "Checklist avant entretien",
                "Rédaction d'une offre type",
            ],
            "Stratégie et canaux": [
                "Présentation des objectifs marketing",
                "Découverte des canaux utilisés",
                "Analyse des campagnes en cours",
            ],
            "Outils digitaux": [
                "Accès à la suite Google/Meta",
                "Configuration des tableaux de bord",
                "Création d'un rapport test",
            ],
            "Processus comptable": [
                "Formation logiciel comptable",
                "Circuit de validation des factures",
                "Clôture mensuelle : étapes",
            ],
            "Outil de gestion": [
                "Configuration des accès",
                "Saisie d'une écriture test",
                "Génération d'un premier bilan",
            ],
            "Produits et services": [
                "Catalogue produits",
                "Procédures de remboursement",
                "Niveaux de support (SLA)",
            ],
            "Outils de ticketing": [
                "Configuration du ticketing",
                "Workflow de résolution",
                "Premier ticket pris en charge",
            ],
            "Infrastructure": [
                "Accès aux serveurs (SSH/VPN)",
                "Découverte de l'infra (schéma)",
                "Déploiement d'un service test",
            ],
            "CI/CD": [
                "Lecture du pipeline",
                "Déclencher un build manuel",
                "Corriger un job en échec",
            ],
            "Monitoring": [
                "Accès aux dashboards",
                "Configurer une alerte",
                "Simuler et résoudre une alerte",
            ],
            "Sécurité et accès": [
                "Politique de mots de passe",
                "Gestion des accès LDAP/AD",
                "Audit des droits",
            ],
            "Sauvegardes": [
                "Vérifier les jobs de backup",
                "Test de restauration",
                "Documentation des procédures",
            ],
            "Monitoring serveurs": [
                "Outils de surveillance",
                "Seuils et alertes",
                "Procédure d'escalade",
            ],
            "Normes qualité": [
                "ISO 9001 : principes",
                "Documentation qualité",
                "Revue des processus",
            ],
            "Procédures d'audit": [
                "Planification d'audit",
                "Checklist audit interne",
                "Rapport et plan d'action",
            ],
            "Indicateurs et reporting": [
                "Tableaux de bord qualité",
                "KPIs à suivre",
                "Revue mensuelle",
            ],
        }
        for mod in Module.objects.all():
            default_steps = [
                f"Étape 1 du module {mod.titre[:30]}",
                f"Étape 2 du module {mod.titre[:30]}",
                f"Étape 3 du module {mod.titre[:30]}",
            ]
            step_titres = steps_by_module.get(mod.titre, default_steps)
            for s_ordre, st in enumerate(step_titres, 1):
                ModuleStep.objects.get_or_create(
                    module=mod, ordre=s_ordre,
                    defaults={"titre": st}
                )

        # Peupler des complétions de sous-étapes pour certains utilisateurs
        all_steps = list(ModuleStep.objects.all()[:50])
        for user in list(users.values())[:6]:
            for step in random.sample(all_steps, min(10, len(all_steps))):
                UserModuleStepCompletion.objects.get_or_create(user=user, module_step=step)

        # Lier plans aux postes
        plan_links = [
            ("Plan Développeur Frontend", "Développement", "Développeur Frontend"),
            ("Plan Développeur Backend", "Développement", "Développeur Backend"),
            ("Plan Chargée Recrutement", "Ressources Humaines", "Chargée Recrutement"),
            ("Plan Responsable Marketing", "Marketing", "Responsable Marketing"),
            ("Plan Comptable", "Finance", "Comptable"),
            ("Plan Support", "Support", "Technicien Support"),
            ("Plan DevOps", "Développement", "DevOps Engineer"),
            ("Plan Admin Système", "Informatique", "Admin Système"),
            ("Plan Responsable Qualité", "Qualité", "Responsable Qualité"),
        ]
        for plan_titre, dept_name, poste_intitule in plan_links:
            key = (dept_name, poste_intitule)
            if key in postes_obj and plan_titre in plans:
                poste = postes_obj[key]
                if not poste.plan_integration_id:
                    poste.plan_integration = plans[plan_titre]
                    poste.save()

        # ========== KNOWLEDGE KINDS ==========
        self.stdout.write("Types de connaissance...")
        kind_names = ["Procédure", "Document", "Guide", "Vidéo", "FAQ", "Tutoriel", "Référence"]
        kinds = {}
        for name in kind_names:
            k, _ = KnowledgeKind.objects.get_or_create(name=name)
            kinds[name] = k

        # ========== ONBOARDING STEPS ==========
        self.stdout.write("Étapes d'onboarding...")
        steps_data = [
            ("Compléter le profil", "Renseignez vos informations personnelles", 1, True),
            ("Signature du contrat", "Signez votre contrat et documents légaux", 2, True),
            ("Visite des locaux", "Découverte des bureaux et équipes", 3, True),
            ("Configuration du poste", "Installation logiciels et accès", 4, True),
            ("Formation sécurité", "Module obligatoire sécurité et RGPD", 5, True),
            ("Rencontre équipe", "Présentation à l'équipe de travail", 6, False),
            ("Objectifs 30 jours", "Définition des objectifs du premier mois", 7, False),
        ]
        for title, desc, order, required in steps_data:
            OnboardingStep.objects.get_or_create(
                title=title,
                defaults={"description": desc, "order": order, "is_required": required}
            )

        # ========== CONNAISSANCES (KnowledgeItem) ==========
        self.stdout.write("Connaissances...")
        knowledge_data = [
            ("Guide d'installation PostgreSQL", "Procédure PostgreSQL", "Guide", "Développement",
             "PostgreSQL, Administration", "PostgreSQL, sécurité", 8),
            ("Processus de Déploiement CI/CD", "Pipeline CI/CD", "Procédure", "Développement",
             "DevOps, CI/CD", "CI/CD", 6),
            ("Guide du Processus de Recrutement", "Recrutement interne", "Guide", "Ressources Humaines",
             "RH, Recrutement", "recrutement", 5),
            ("Standards de Code JavaScript", "Conventions JavaScript", "Document", "Développement",
             "JavaScript, Qualité Code", "JavaScript", 4),
            ("Stratégie Marketing Digital 2024", "Plan marketing", "Document", "Marketing",
             "Marketing, Digital", "marketing", 5),
            ("Introduction à Docker", "Conteneurisation", "Guide", "Développement",
             "DevOps", "Docker, documentation", 7),
            ("API REST - Bonnes pratiques", "Conception d'API", "Document", "Développement",
             "Django, React", "API, documentation", 6),
            ("Procédure de backup", "Sauvegarde des données", "Procédure", "Informatique",
             "Administration", "sécurité, documentation", 4),
            ("FAQ Support client", "Questions fréquentes support", "FAQ", "Support",
             "Support client", "support, documentation", 3),
            ("Charte graphique", "Identité visuelle entreprise", "Document", "Marketing",
             "Design, Marketing", "marketing", 2),
            ("Processus comptable mensuel", "Clôture mensuelle", "Procédure", "Finance",
             "Comptabilité", "budget, comptabilité", 5),
            ("Sécurité informatique et RGPD", "Conformité et sécurité", "Guide", "Informatique",
             "Administration", "sécurité, RGPD, conformité", 10),
            ("Tests unitaires avec pytest", "Tests Python", "Tutoriel", "Développement",
             "Python, Qualité Code", "Python, tests", 6),
            ("Réactiver un compte bloqué", "Procédure support", "Procédure", "Support",
             "Support client", "support", 2),
            ("Gestion des congés", "Demande et validation congés", "Guide", "Ressources Humaines",
             "RH, Communication", "documentation", 4),
            ("Configuration Kubernetes", "Déploiement conteneurs", "Tutoriel", "Développement",
             "DevOps", "Kubernetes, Docker", 12),
            ("Guide du télétravail", "Modalités télétravail", "Guide", "Ressources Humaines",
             "RH, Communication", "documentation", 3),
            ("Rédaction d'un cahier des charges", "Méthodologie CdC", "Document", "Développement",
             "Gestion de projet, Communication", "documentation", 6),
            ("Optimisation SEO", "Bonnes pratiques SEO", "Guide", "Marketing",
             "SEO, Marketing", "marketing", 5),
            ("Audit de sécurité", "Procédure d'audit", "Procédure", "Informatique",
             "Administration", "sécurité, conformité", 4),
            ("Utilisation de Git", "Workflow Git", "Tutoriel", "Développement",
             "DevOps", "documentation", 4),
            ("Préparation de réunion", "Checklist réunion", "Procédure", "Ressources Humaines",
             "Communication", "documentation", 2),
            ("Traitement des réclamations", "Processus réclamations", "Procédure", "Support",
             "Support client", "support", 3),
        ]
        knowledge_items = []
        dev_dept = depts.get("Développement")
        rh_dept = depts.get("Ressources Humaines")
        mkt_dept = depts.get("Marketing")
        fin_dept = depts.get("Finance")
        sup_dept = depts.get("Support")
        info_dept = depts.get("Informatique")

        dept_map = {
            "Développement": dev_dept,
            "Ressources Humaines": rh_dept,
            "Marketing": mkt_dept,
            "Finance": fin_dept,
            "Support": sup_dept,
            "Informatique": info_dept,
        }

        manager_user = users.get("manager") or users.get("admin")
        emp_users = [u for un, u in users.items() if un.startswith("employee")]

        for title, desc, kind_name, dept_name, comp_str, tag_str, read_min in knowledge_data:
            kind = kinds.get(kind_name, list(kinds.values())[0])
            dept = dept_map.get(dept_name)
            author_u = random.choice(emp_users) if emp_users else manager_user

            ki, created = KnowledgeItem.objects.get_or_create(
                title=title,
                defaults={
                    "description": desc,
                    "kind": kind,
                    "department": dept,
                    "author": author_u.get_full_name() or author_u.username,
                    "author_user": author_u,
                    "content": f"<h2>{title}</h2><p>{desc}. Contenu détaillé de la connaissance.</p>"
                               f"<h3>Section 1</h3><p>Contenu...</p><h3>Section 2</h3><p>Suite...</p>",
                    "status": random.choice(["published", "published", "published", "draft", "in_review"]),
                    "numero_version": "1.0",
                    "read_time_min": read_min,
                    "published_at": now if random.random() > 0.3 else None,
                },
            )
            if created:
                KnowledgeVersion.objects.create(
                    knowledge_item=ki,
                    numero_version="1.0",
                    content=ki.content,
                    author_name=ki.author,
                    est_actuelle=True,
                )
                for tag_name in [t.strip() for t in tag_str.split(",")]:
                    if tag_name in tags:
                        ki.tags.add(tags[tag_name])
                for comp_name in [c.strip() for c in comp_str.split(",")]:
                    if comp_name in comps:
                        ki.competences.add(comps[comp_name])
            knowledge_items.append(ki)

        # Liens Module <-> KnowledgeItem
        modules = list(Module.objects.all())
        for i, ki in enumerate(knowledge_items):
            if modules:
                mod = modules[i % len(modules)]
                ModuleKnowledgeItem.objects.get_or_create(
                    module=mod, knowledge_item=ki,
                    defaults={"ordre": (i % 3) + 1}
                )

        # ========== PROGRESSIONS ==========
        self.stdout.write("Progressions...")
        plans_list = list(PlanIntegration.objects.all())
        all_users = list(users.values())
        for user in all_users:
            for plan in random.sample(plans_list, min(4, len(plans_list))):
                Progression.objects.get_or_create(
                    user=user, plan=plan,
                    defaults={
                        "pourcentage": random.randint(0, 100),
                        "statut": random.choice(["en_cours", "en_cours", "termine", "certifie"]),
                        "date_fin": now - timedelta(days=random.randint(0, 90)) if random.random() > 0.6 else None,
                    }
                )

        # ========== USER QUIZ ATTEMPTS ==========
        self.stdout.write("Tentatives de quiz...")
        quizzes = list(Quiz.objects.all())
        for user in all_users:
            for quiz in random.sample(quizzes, min(5, len(quizzes))):
                UserQuizAttempt.objects.get_or_create(
                    user=user, quiz=quiz,
                    defaults={
                        "score_pct": random.randint(50, 100),
                        "passed": random.random() > 0.2,
                        "completed_at": now - timedelta(days=random.randint(1, 60)),
                    }
                )

        # ========== VERSIONS SUPPLÉMENTAIRES pour certaines connaissances ==========
        self.stdout.write("Versions supplémentaires...")
        for ki in KnowledgeItem.objects.all()[:8]:
            if ki.versions.count() < 2:
                last_num = "1.0"
                for v in ki.versions.all():
                    try:
                        n = float(v.numero_version)
                        if n >= float(last_num):
                            last_num = v.numero_version
                    except ValueError:
                        pass
                next_num = "1.1" if last_num == "1.0" else "2.0"
                KnowledgeVersion.objects.get_or_create(
                    knowledge_item=ki, numero_version=next_num,
                    defaults={
                        "content": ki.content + f"\n<p>Mise à jour version {next_num}.</p>",
                        "author_name": ki.author or "Système",
                        "est_actuelle": False,
                    }
                )

        self.stdout.write(self.style.SUCCESS("Enrichissement terminé avec succès."))
        self._print_counts()

    def _print_counts(self):
        from app_connaissance.models import (
            Entreprise, Department, Competence, PlanIntegration, Poste,
            Module, ModuleStep, UserModuleStepCompletion, Quiz, QuizQuestion, QuizChoice, UserQuizAttempt,
            KnowledgeKind, KnowledgeItem, KnowledgeVersion, ModuleKnowledgeItem,
            Progression, UserProfile, OnboardingStep, Tag,
        )
        from django.contrib.auth.models import User

        self.stdout.write("\n--- Comptage actuel ---")
        for name, model in [
            ("Entreprise", Entreprise),
            ("Department", Department),
            ("Competence", Competence),
            ("PlanIntegration", PlanIntegration),
            ("Poste", Poste),
            ("Module", Module),
            ("ModuleStep", ModuleStep),
            ("UserModuleStepCompletion", UserModuleStepCompletion),
            ("Quiz", Quiz),
            ("QuizQuestion", QuizQuestion),
            ("QuizChoice", QuizChoice),
            ("UserQuizAttempt", UserQuizAttempt),
            ("KnowledgeKind", KnowledgeKind),
            ("KnowledgeItem", KnowledgeItem),
            ("KnowledgeVersion", KnowledgeVersion),
            ("ModuleKnowledgeItem", ModuleKnowledgeItem),
            ("Progression", Progression),
            ("UserProfile", UserProfile),
            ("OnboardingStep", OnboardingStep),
            ("Tag", Tag),
            ("User", User),
        ]:
            count = model.objects.count()
            self.stdout.write(f"  {name}: {count}")
