from django.contrib import admin
from django.urls import path

from my_app import views

urlpatterns = [
    path('login/', views.login, name='login'),
    path('login_post/', views.login_post, name='login_post'),
    path('admin_dash/', views.admin_dash, name='admin_dash'),
    path('add_company/', views.add_company_post, name='add_company'),
    path('edit_company/', views.edit_company_post, name='edit_company'),
    path('delete_company/', views.delete_company_post, name='delete_company'),
    path('get_company_data/', views.get_company_data, name='get_company_data'),

    path('add_item_group/', views.add_item_group_post, name='add_item_group'),
    path('edit_item_group/', views.edit_item_group_post, name='edit_item_group'),
    path('delete_item_group/', views.delete_item_group_post, name='delete_item_group'),
    path('get_item_group_data/', views.get_item_group_data, name='get_item_group_data'),
    path('get_next_group_id/', views.get_next_group_id, name='get_next_group_id'),  # Add this line

    path('get_companies/', views.get_companies_json, name='get_companies'),
    path('get_expiring_companies/', views.get_expiring_companies, name='get_expiring_companies'),

    path('user_dash/', views.user_dash, name='user_dash'),
    path('set_selected_company/', views.set_selected_company, name='set_selected_company'),
    path('get_transaction_data/', views.get_transaction_data, name='get_transaction_data'),
    path('get_companies_json/', views.get_companies_json, name='get_companies_json'),

]
