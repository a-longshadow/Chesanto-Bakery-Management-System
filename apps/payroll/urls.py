"""
Payroll App URLs
Routes for employee management, payroll processing, casual labor, and misc expenses
"""
from django.urls import path
from . import views

app_name = 'payroll'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Employees
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    
    # Monthly Payroll
    path('payroll/', views.payroll_list, name='payroll_list'),
    path('payroll/create/', views.payroll_create, name='payroll_create'),
    path('payroll/<int:pk>/', views.payroll_detail, name='payroll_detail'),
    path('payroll/<int:pk>/process/', views.payroll_process, name='payroll_process'),
    path('payroll/<int:pk>/item/<int:item_pk>/edit/', views.payroll_item_edit, name='payroll_item_edit'),
    
    # Casual Labor
    path('casual/', views.casual_labor_list, name='casual_labor_list'),
    path('casual/create/', views.casual_labor_create, name='casual_labor_create'),
    path('casual/<int:pk>/mark-paid/', views.casual_labor_mark_paid, name='casual_labor_mark_paid'),
    
    # Miscellaneous Expenses
    path('misc-expenses/', views.misc_expense_list, name='misc_expense_list'),
    path('misc-expenses/create/', views.misc_expense_create, name='misc_expense_create'),
    path('misc-expenses/<int:pk>/', views.misc_expense_detail, name='misc_expense_detail'),
]
