from django.urls import path
from django.contrib.auth import views as auth_views

from . import api_views, views

urlpatterns = [
    path("api/reference/create/", api_views.reference_create_api, name="api_reference_create"),
    path("api/postes-by-department/<int:department_id>/", api_views.postes_by_department_api, name="api_postes_by_department"),
    path('', views.index_redirect, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout_view'),
    path('login/change-password/', views.password_change_required, name='password_change_required'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('forbidden/', views.forbidden, name='forbidden'),

    # Réinitialisation mot de passe (email SMTP)
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='auth/password_reset.html',
        email_template_name='auth/password_reset_email.html',
        subject_template_name='auth/password_reset_subject.txt',
        success_url='/password-reset/done/',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='auth/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='auth/password_reset_complete.html',
    ), name='password_reset_complete'),

    # Connaissances
    path('connaissances/', views.knowledge_list, name='knowledge_list'),
    path('connaissances/nouvelle/', views.knowledge_create, name='knowledge_create'),
    path('connaissances/<int:knowledge_id>/', views.knowledge_detail, name='knowledge_detail'),
    path('connaissances/<int:knowledge_id>/modifier/', views.knowledge_edit, name='knowledge_edit'),
    path('connaissances/<int:knowledge_id>/dupliquer/', views.knowledge_duplicate, name='knowledge_duplicate'),
    path('connaissances/<int:knowledge_id>/generate-quiz/', views.knowledge_generate_quiz, name='knowledge_generate_quiz'),

    # Validation (manager)
    path('validation/', views.validation_queue, name='validation_queue'),
    path('validation/<int:knowledge_id>/approve/', views.validation_approve, name='validation_approve'),
    path('validation/<int:knowledge_id>/reject/', views.validation_reject, name='validation_reject'),

    # Administration (admin)
    path('admin-panel/departements/', views.departments, name='departments'),
    path('admin-panel/departements/nouveau/', views.department_create, name='department_create'),
    path('admin-panel/departements/<int:pk>/modifier/', views.department_edit, name='department_edit'),
    path('admin-panel/utilisateurs/', views.users_admin, name='users_admin'),
    path('admin-panel/utilisateurs/nouveau/', views.user_create, name='user_create'),
    path('admin-panel/etapes-integration/', views.onboarding_steps_admin, name='onboarding_steps_admin'),
    path('admin-panel/etapes-integration/nouvelle/', views.onboarding_step_create, name='onboarding_step_create'),
    path('admin-panel/etapes-integration/<int:pk>/modifier/', views.onboarding_step_edit, name='onboarding_step_edit'),

    # Intégration / formation
    path('integration/', views.onboarding_home, name='onboarding_home'),
    path('integration/mon-plan/', views.plan_integration_personnel, name='plan_integration_personnel'),
    path('integration/step/<int:step_id>/toggle/', views.module_step_toggle, name='module_step_toggle'),
    path('integration/quiz/<int:quiz_id>/', views.quiz_take, name='quiz_take'),
    path('formations/', views.trainings, name='trainings'),

    # Profil
    path('profil/', views.profile, name='profile'),
]
