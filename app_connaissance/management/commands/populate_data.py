"""
Commande de gestion : insère des enregistrements réalistes en base.
Usage : python manage.py populate_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from app_connaissance.models import (
    Competence,
    Department,
    KnowledgeItem,
    KnowledgeKind,
    KnowledgeVersion,
    Module,
    ModuleKnowledgeItem,
    PlanIntegration,
    Poste,
    Quiz,
    QuizChoice,
    QuizQuestion,
    Tag,
    UserProfile,
)
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Insère des départements, utilisateurs, types, tags, compétences et connaissances de démo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-knowledge",
            action="store_true",
            help="Supprime toutes les connaissances avant d'en créer de nouvelles (garde le reste).",
        )

    def handle(self, *args, **options):
        if options["clear_knowledge"]:
            KnowledgeVersion.objects.all().delete()
            KnowledgeItem.objects.all().delete()
            self.stdout.write("Connaissances et versions supprimées.")

        # --- Départements ---
        self.stdout.write("Départements...")
        depts_data = [
            ("Développement", "Équipe de développement logiciel"),
            ("Ressources Humaines", "Gestion du personnel et recrutement"),
            ("Marketing", "Communication et stratégie digitale"),
            ("Finance", "Gestion financière et contrôle"),
            ("Support", "Support client et SAV"),
        ]
        depts = {}
        for name, desc in depts_data:
            dept, _ = Department.objects.get_or_create(name=name, defaults={"description": desc})
            depts[name] = dept

        # --- Utilisateurs et profils ---
        self.stdout.write("Utilisateurs et profils...")
        users_data = [
            ("admin", "admin@company.com", "Admin", "Principal", "admin", None, None),
            ("manager", "manager@company.com", "Marie", "Dupont", "manager", "Développement", "Manager Développement"),
            ("employee1", "jean@company.com", "Jean", "Martin", "employee", "Développement", "Développeur Frontend"),
            ("employee2", "sophie@company.com", "Sophie", "Bernard", "employee", "Ressources Humaines", "Chargée Recrutement"),
            ("employee3", "pierre@company.com", "Pierre", "Dubois", "employee", "Marketing", "Responsable Marketing"),
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
                    "display_name": display,
                    "role": role,
                    "department": dept,
                    "poste": poste,
                },
            )

        # Mettre le manager du département Développement
        dev = depts["Développement"]
        dev.manager = users["manager"]
        dev.save()

        # --- Types de connaissance ---
        self.stdout.write("Types de connaissance...")
        kinds_data = ["Procédure", "Document", "Guide", "Vidéo", "FAQ"]
        kinds = {}
        for name in kinds_data:
            k, _ = KnowledgeKind.objects.get_or_create(name=name)
            kinds[name] = k

        # --- Tags ---
        self.stdout.write("Tags...")
        tag_names = ["onboarding", "sécurité", "PostgreSQL", "CI/CD", "recrutement", "JavaScript", "marketing", "qualité"]
        tags = {}
        for name in tag_names:
            t, _ = Tag.objects.get_or_create(name=name)
            tags[name] = t

        # --- Compétences ---
        self.stdout.write("Compétences...")
        comp_names = ["PostgreSQL", "Administration", "DevOps", "CI/CD", "RH", "Recrutement", "JavaScript", "Qualité Code", "Marketing", "Digital"]
        comps = {}
        for name in comp_names:
            c, _ = Competence.objects.get_or_create(name=name)
            comps[name] = c

        # --- Postes (compléter si besoin) ---
        Poste.objects.get_or_create(department=depts["Développement"], intitule="Administrateur BDD", defaults={"description": ""})
        Poste.objects.get_or_create(department=depts["Ressources Humaines"], intitule="Chargée Recrutement", defaults={"description": ""})
        Poste.objects.get_or_create(department=depts["Marketing"], intitule="Responsable Marketing", defaults={"description": ""})

        # --- Plans d'intégration par poste/département + modules + quiz ---
        self.stdout.write("Plans d'intégration (par poste/département)...")

        # Plan Développement — Développeur Frontend
        plan_dev, _ = PlanIntegration.objects.get_or_create(
            titre="Plan Développeur Frontend",
            defaults={"description": "Parcours d'onboarding pour les développeurs frontend.", "duree_estimee_jours": 10},
        )
        mod1, _ = Module.objects.get_or_create(plan=plan_dev, ordre=1, defaults={"titre": "Introduction à l'entreprise", "duree_jours": 3})
        mod2, _ = Module.objects.get_or_create(plan=plan_dev, ordre=2, defaults={"titre": "Environnement de développement", "duree_jours": 4})
        mod3, _ = Module.objects.get_or_create(plan=plan_dev, ordre=3, defaults={"titre": "Standards de code", "duree_jours": 3})

        # Lier le plan au poste Développeur Frontend
        poste_dev_frontend, _ = Poste.objects.get_or_create(
            department=depts["Développement"], intitule="Développeur Frontend", defaults={"description": ""}
        )
        if not poste_dev_frontend.plan_integration_id:
            poste_dev_frontend.plan_integration = plan_dev
            poste_dev_frontend.save()

        # Quiz pour les modules du plan Dev (évite conflits : un quiz par module via get_or_create)
        quiz1, _ = Quiz.objects.get_or_create(module=mod1, defaults={"titre": "Quiz Introduction", "seuil_reussite_pct": 70})
        q1_1, _ = QuizQuestion.objects.get_or_create(quiz=quiz1, ordre=1, defaults={"enonce": "Quelle est la première étape d'intégration ?"})
        QuizChoice.objects.get_or_create(question=q1_1, texte="Présentation à l'équipe", defaults={"is_correct": True})
        QuizChoice.objects.get_or_create(question=q1_1, texte="Signer le contrat", defaults={"is_correct": False})
        QuizChoice.objects.get_or_create(question=q1_1, texte="Configurer son poste", defaults={"is_correct": False})

        quiz2, _ = Quiz.objects.get_or_create(module=mod2, defaults={"titre": "Quiz Environnement", "seuil_reussite_pct": 70})
        q2_1, _ = QuizQuestion.objects.get_or_create(quiz=quiz2, ordre=1, defaults={"enonce": "Quel outil est utilisé pour le versionning du code ?"})
        QuizChoice.objects.get_or_create(question=q2_1, texte="Git", defaults={"is_correct": True})
        QuizChoice.objects.get_or_create(question=q2_1, texte="Excel", defaults={"is_correct": False})
        QuizChoice.objects.get_or_create(question=q2_1, texte="Word", defaults={"is_correct": False})

        # Plan RH — Chargée Recrutement
        plan_rh, _ = PlanIntegration.objects.get_or_create(
            titre="Plan Chargée Recrutement",
            defaults={"description": "Parcours d'intégration pour le recrutement.", "duree_estimee_jours": 5},
        )
        mod_rh1, _ = Module.objects.get_or_create(plan=plan_rh, ordre=1, defaults={"titre": "Processus de recrutement", "duree_jours": 2})
        mod_rh2, _ = Module.objects.get_or_create(plan=plan_rh, ordre=2, defaults={"titre": "Outils et bonnes pratiques", "duree_jours": 3})
        poste_rh, _ = Poste.objects.get_or_create(
            department=depts["Ressources Humaines"], intitule="Chargée Recrutement", defaults={"description": ""}
        )
        if not poste_rh.plan_integration_id:
            poste_rh.plan_integration = plan_rh
            poste_rh.save()
        quiz_rh, _ = Quiz.objects.get_or_create(module=mod_rh1, defaults={"titre": "Quiz Recrutement", "seuil_reussite_pct": 70})
        q_rh, _ = QuizQuestion.objects.get_or_create(quiz=quiz_rh, ordre=1, defaults={"enonce": "Combien d'étapes comporte le processus de recrutement ?"})
        QuizChoice.objects.get_or_create(question=q_rh, texte="5 étapes", defaults={"is_correct": True})
        QuizChoice.objects.get_or_create(question=q_rh, texte="3 étapes", defaults={"is_correct": False})
        QuizChoice.objects.get_or_create(question=q_rh, texte="7 étapes", defaults={"is_correct": False})

        # Plan Marketing — Responsable Marketing
        plan_mkt, _ = PlanIntegration.objects.get_or_create(
            titre="Plan Responsable Marketing",
            defaults={"description": "Parcours d'intégration pour le marketing.", "duree_estimee_jours": 5},
        )
        mod_mkt1, _ = Module.objects.get_or_create(plan=plan_mkt, ordre=1, defaults={"titre": "Stratégie et canaux", "duree_jours": 3})
        mod_mkt2, _ = Module.objects.get_or_create(plan=plan_mkt, ordre=2, defaults={"titre": "Outils digitaux", "duree_jours": 2})
        poste_mkt, _ = Poste.objects.get_or_create(
            department=depts["Marketing"], intitule="Responsable Marketing", defaults={"description": ""}
        )
        if not poste_mkt.plan_integration_id:
            poste_mkt.plan_integration = plan_mkt
            poste_mkt.save()
        quiz_mkt, _ = Quiz.objects.get_or_create(module=mod_mkt1, defaults={"titre": "Quiz Marketing", "seuil_reussite_pct": 70})
        q_mkt, _ = QuizQuestion.objects.get_or_create(quiz=quiz_mkt, ordre=1, defaults={"enonce": "Quel canal est prioritaire dans notre stratégie ?"})
        QuizChoice.objects.get_or_create(question=q_mkt, texte="SEO et Content Marketing", defaults={"is_correct": True})
        QuizChoice.objects.get_or_create(question=q_mkt, texte="Télévision", defaults={"is_correct": False})
        QuizChoice.objects.get_or_create(question=q_mkt, texte="Flyers", defaults={"is_correct": False})

        # Compatibilité : variable "plan" pour la suite du script (connaissances liées à mod1, mod2, mod3)
        plan = plan_dev

        # --- Connaissances (avec versions) ---
        self.stdout.write("Connaissances...")
        manager = users["manager"]
        content_v1 = """<h2>Installation PostgreSQL Version 2019</h2>
<p>Cette version couvre l'installation manuelle de PostgreSQL 10 sur Ubuntu 18.04.</p>
<h3>Prérequis</h3>
<ul><li>Ubuntu 18.04 LTS</li><li>Droits sudo</li><li>Connexion internet</li></ul>
<h3>Étapes d'installation</h3>
<ol><li>Mise à jour du système : <code>sudo apt update</code></li>
<li>Installation PostgreSQL : <code>sudo apt install postgresql postgresql-contrib</code></li>
<li>Vérification du service : <code>sudo systemctl status postgresql</code></li></ol>
<p>Configuration basique dans /etc/postgresql/10/main/postgresql.conf</p>"""
        content_v2 = """<h2>Installation PostgreSQL Version 2022</h2>
<p>Cette version intègre Docker pour une installation simplifiée de PostgreSQL 13.</p>
<h3>Prérequis</h3>
<ul><li>Docker installé</li><li>Docker Compose</li></ul>
<h3>Installation via Docker</h3>
<p>Créer un fichier docker-compose.yml puis lancer : <code>docker-compose up -d</code></p>"""
        content_v3 = """<h2>Installation PostgreSQL Version 2024</h2>
<p>Version la plus récente avec PostgreSQL 15 et intégration Kubernetes.</p>
<h3>Prérequis</h3>
<ul><li>Cluster Kubernetes</li><li>Helm 3.x</li></ul>
<h3>Déploiement avec Helm</h3>
<ol><li>Ajouter le repo : <code>helm repo add bitnami https://charts.bitnami.com/bitnami</code></li>
<li>Installer : <code>helm install my-postgres bitnami/postgresql</code></li>
<li>Vérifier : <code>kubectl get pods</code></li></ol>"""

        k1, created = KnowledgeItem.objects.get_or_create(
            title="Guide d'installation PostgreSQL",
            defaults={
                "description": "Procédure complète d'installation et configuration de PostgreSQL.",
                "kind": kinds["Guide"],
                "department": depts["Développement"],
                "author": "Marie Dupont",
                "author_user": manager,
                "content": content_v3,
                "status": KnowledgeItem.Status.PUBLISHED,
                "numero_version": "2024",
                "read_time_min": 8,
                "published_at": timezone.now(),
            },
        )
        if created:
            for v_num, content, actuelle in [("2019", content_v1, False), ("2022", content_v2, False), ("2024", content_v3, True)]:
                KnowledgeVersion.objects.create(
                    knowledge_item=k1,
                    numero_version=v_num,
                    content=content,
                    author_name="Marie Dupont",
                    est_actuelle=actuelle,
                )
            k1.tags.add(tags["PostgreSQL"], tags["sécurité"])
            k1.competences.add(comps["PostgreSQL"], comps["Administration"])
            ModuleKnowledgeItem.objects.get_or_create(module=mod2, knowledge_item=k1, defaults={"ordre": 1})

        content_cicd_1 = """<h2>Pipeline CI/CD Version 1.0</h2>
<p>Configuration de base avec GitLab CI.</p>
<h3>Structure du .gitlab-ci.yml</h3>
<pre>stages:\n  - build\n  - test\n  - deploy\n\nbuild:\n  stage: build\n  script:\n    - npm install\n    - npm run build</pre>"""
        content_cicd_2 = """<h2>Pipeline CI/CD Version 2.0</h2>
<p>Migration vers GitHub Actions avec déploiement automatique.</p>
<h3>Workflow GitHub Actions</h3>
<pre>name: CI/CD Pipeline\non:\n  push:\n    branches: [main]\njobs:\n  deploy:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v2\n      - name: Deploy to production\n        run: ./deploy.sh</pre>
<p>Intégration avec AWS ECS pour le déploiement automatique.</p>"""
        k2, created = KnowledgeItem.objects.get_or_create(
            title="Processus de Déploiement CI/CD",
            defaults={
                "description": "Pipeline de déploiement automatisé (GitLab CI puis GitHub Actions).",
                "kind": kinds["Procédure"],
                "department": depts["Développement"],
                "author": "Marie Dupont",
                "author_user": manager,
                "content": content_cicd_2,
                "status": KnowledgeItem.Status.PUBLISHED,
                "numero_version": "2.0",
                "read_time_min": 6,
                "published_at": timezone.now(),
            },
        )
        if created:
            for v_num, content, actuelle in [("1.0", content_cicd_1, False), ("2.0", content_cicd_2, True)]:
                KnowledgeVersion.objects.create(
                    knowledge_item=k2,
                    numero_version=v_num,
                    content=content,
                    author_name="Marie Dupont",
                    est_actuelle=actuelle,
                )
            k2.tags.add(tags["CI/CD"])
            k2.competences.add(comps["DevOps"], comps["CI/CD"])
            ModuleKnowledgeItem.objects.get_or_create(module=mod2, knowledge_item=k2, defaults={"ordre": 2})

        content_rh = """<h2>Processus de Recrutement 2024</h2>
<p>Notre processus de recrutement en 5 étapes.</p>
<h3>1. Définition du besoin</h3>
<p>Analyse du poste avec le manager, définition du profil recherché.</p>
<h3>2. Publication de l'annonce</h3>
<p>Diffusion sur LinkedIn, Indeed et site carrière entreprise.</p>
<h3>3. Présélection des candidats</h3>
<p>Tri des CV selon critères définis, contact des candidats retenus.</p>
<h3>4. Entretiens</h3>
<ul><li>Entretien RH (30 min)</li><li>Entretien technique (1h)</li><li>Entretien manager (45 min)</li></ul>
<h3>5. Décision et proposition</h3>
<p>Débriefing équipe, proposition d'embauche, négociation conditions.</p>"""
        k3, created = KnowledgeItem.objects.get_or_create(
            title="Guide du Processus de Recrutement",
            defaults={
                "description": "Étapes complètes du recrutement interne.",
                "kind": kinds["Guide"],
                "department": depts["Ressources Humaines"],
                "author": "Marie Dupont",
                "author_user": manager,
                "content": content_rh,
                "status": KnowledgeItem.Status.PUBLISHED,
                "numero_version": "2024",
                "read_time_min": 5,
                "published_at": timezone.now(),
            },
        )
        if created:
            KnowledgeVersion.objects.create(
                knowledge_item=k3,
                numero_version="2024",
                content=content_rh,
                author_name="Marie Dupont",
                est_actuelle=True,
            )
            k3.tags.add(tags["recrutement"])
            k3.competences.add(comps["RH"], comps["Recrutement"])
            ModuleKnowledgeItem.objects.get_or_create(module=mod1, knowledge_item=k3, defaults={"ordre": 1})

        content_js = """<h2>Standards de Code JavaScript</h2>
<p>Règles à suivre pour maintenir la qualité du code.</p>
<h3>Naming Conventions</h3>
<ul><li>Variables : camelCase</li><li>Constantes : UPPER_CASE</li><li>Classes : PascalCase</li></ul>
<h3>Formatage</h3>
<p>Utilisation de Prettier avec configuration partagée.</p>"""
        k4, created = KnowledgeItem.objects.get_or_create(
            title="Standards de Code JavaScript",
            defaults={
                "description": "Conventions de développement et qualité de code.",
                "kind": kinds["Document"],
                "department": depts["Développement"],
                "author": "Sophie Bernard",
                "author_user": users["employee2"],
                "content": content_js,
                "status": KnowledgeItem.Status.IN_REVIEW,
                "numero_version": "1.0",
                "read_time_min": 4,
            },
        )
        if created:
            KnowledgeVersion.objects.create(
                knowledge_item=k4,
                numero_version="1.0",
                content=content_js,
                author_name="Sophie Bernard",
                est_actuelle=True,
            )
            k4.tags.add(tags["JavaScript"])
            k4.competences.add(comps["JavaScript"], comps["Qualité Code"])
            ModuleKnowledgeItem.objects.get_or_create(module=mod3, knowledge_item=k4, defaults={"ordre": 1})

        content_marketing = """<h2>Stratégie Marketing Digital 2024</h2>
<p>Notre plan marketing pour l'année.</p>
<h3>Objectifs</h3>
<ul><li>Augmentation trafic site : +40%</li><li>Génération leads : 500/mois</li><li>Taux conversion : 3%</li></ul>
<h3>Canaux prioritaires</h3>
<ol><li>SEO et Content Marketing</li><li>LinkedIn Ads</li><li>Email Marketing</li><li>Webinaires</li></ol>"""
        k5, created = KnowledgeItem.objects.get_or_create(
            title="Stratégie Marketing Digital 2024",
            defaults={
                "description": "Plan marketing annuel et canaux prioritaires.",
                "kind": kinds["Document"],
                "department": depts["Marketing"],
                "author": "Pierre Dubois",
                "author_user": users["employee3"],
                "content": content_marketing,
                "status": KnowledgeItem.Status.PUBLISHED,
                "numero_version": "2024",
                "read_time_min": 5,
                "published_at": timezone.now(),
            },
        )
        if created:
            KnowledgeVersion.objects.create(
                knowledge_item=k5,
                numero_version="2024",
                content=content_marketing,
                author_name="Pierre Dubois",
                est_actuelle=True,
            )
            k5.tags.add(tags["marketing"])
            k5.competences.add(comps["Marketing"], comps["Digital"])
            ModuleKnowledgeItem.objects.get_or_create(module=mod1, knowledge_item=k5, defaults={"ordre": 2})

        self.stdout.write(self.style.SUCCESS("Données insérées avec succès."))
        self.stdout.write("  Comptes de démo (mot de passe : demo123) : admin, manager, employee1, employee2, employee3")
