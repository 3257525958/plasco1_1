from django.urls import path

from cantact_app import views
app_name = 'cantact_app'

urlpatterns = [
    path('login/',views.logindef),
    path('logout/',views.logout_view),
    path('addcontact/',views.addcantactdef),
    path('ignor/',views.ignordef),
    path('addphon/',views.addphone),
    path('addreservecantact/',views.saveaccantdef),

    path('edit-profile/', views.edit_profile, name='edit_profile'),
    # -----------------ثبت شعب------------------------------------------------

    path('branch/create/', views.BranchCreateView.as_view(), name='branch_create'),
    path('branch/list/', views.branch_list, name='branch_list'),
    path('branch/<int:pk>/', views.branch_detail, name='branch_detail'),
    path('branch/<int:pk>/edit/', views.branch_edit, name='branch_edit'),
    path('branch/<int:pk>/delete/', views.branch_delete, name='branch_delete'),
    path('branch/search-sellers/', views.search_sellers, name='search_sellers'),

    # -------------------------برسی لاگین------------------------------------------------------------
    #
    # path('sessions/', views.session_management_view, name='session_management'),
    # path('sessions/terminate/', views.terminate_other_sessions_view, name='terminate_other_sessions'),
    #

]