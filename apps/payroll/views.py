"""
Payroll App Views
Employee management, monthly payroll processing, and casual labor tracking

ACCESS CONTROL: All views restricted to SUPERADMIN role only
Payroll data is sensitive and should only be accessible to CEO/owner

SUPERADMIN PROTECTION: SUPERADMINs cannot edit each other's payroll data
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date
from calendar import month_name

from .models import Employee, MonthlyPayroll, PayrollItem, CasualLabor, MiscExpenseRecord, MiscExpenseCategory
from apps.accounts.views import superadmin_required
from apps.accounts.models import User


@superadmin_required
def dashboard(request):
    """
    Payroll dashboard with key metrics
    Shows active employees, current month payroll status, casual labor summary
    """
    today = timezone.now().date()
    current_month = today.month
    current_year = today.year
    
    # Employee metrics
    total_employees = Employee.objects.filter(status='ACTIVE').count()
    total_permanent = Employee.objects.filter(status='ACTIVE', employee_type='PERMANENT').count()
    total_contract = Employee.objects.filter(status='ACTIVE', employee_type='CONTRACT').count()
    
    # Calculate total monthly salary obligation
    active_employees = Employee.objects.filter(status='ACTIVE')
    salary_obligation = sum(emp.gross_salary for emp in active_employees)
    
    # Current month payroll status
    current_payroll = MonthlyPayroll.objects.filter(
        month=current_month,
        year=current_year
    ).first()
    
    # Recent payroll periods
    recent_payrolls = MonthlyPayroll.objects.order_by('-year', '-month')[:6]
    
    # Casual labor this month
    casual_this_month = CasualLabor.objects.filter(
        date__month=current_month,
        date__year=current_year
    ).aggregate(
        total_amount=Sum('total_amount'),
        total_workers=Sum('number_of_workers'),
        entries=Count('id')
    )
    
    # Pending payments
    pending_casual = CasualLabor.objects.filter(payment_status='PENDING').aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Misc expenses this month
    misc_this_month = MiscExpenseRecord.objects.filter(
        expense_date__month=current_month,
        expense_date__year=current_year
    ).aggregate(
        total_amount=Sum('amount'),
        entries=Count('id')
    )
    
    context = {
        'total_employees': total_employees,
        'total_permanent': total_permanent,
        'total_contract': total_contract,
        'salary_obligation': salary_obligation,
        'current_payroll': current_payroll,
        'current_month_name': month_name[current_month],
        'current_year': current_year,
        'recent_payrolls': recent_payrolls,
        'casual_this_month': casual_this_month,
        'pending_casual': pending_casual,
        'misc_this_month': misc_this_month,
        'today': today,
    }
    
    return render(request, 'payroll/dashboard.html', context)


@superadmin_required
def employee_list(request):
    """
    List all employees with filtering
    Filters: status, employee_type, search
    """
    employees = Employee.objects.select_related('user').order_by('employee_id')
    
    # Filters
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    search = request.GET.get('search', '')
    
    if status_filter:
        employees = employees.filter(status=status_filter)
    
    if type_filter:
        employees = employees.filter(employee_type=type_filter)
    
    if search:
        employees = employees.filter(
            Q(employee_id__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(position__icontains=search)
        )
    
    # Summary stats
    total_count = employees.count()
    active_count = employees.filter(status='ACTIVE').count()
    
    # Pagination
    paginator = Paginator(employees, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'employees': page_obj,
        'page_obj': page_obj,
        'total_count': total_count,
        'active_count': active_count,
        'filters': {
            'status': status_filter,
            'type': type_filter,
            'search': search,
        },
        'status_choices': Employee.STATUS_CHOICES,
        'type_choices': Employee.EMPLOYEE_TYPE_CHOICES,
        'current_user': request.user,  # For SUPERADMIN protection check in template
    }
    
    return render(request, 'payroll/employee_list.html', context)


@superadmin_required
def employee_create(request):
    """
    Add existing user to payroll system
    - Shows users who don't have an employee record yet
    - Pre-populates form with user's existing profile data
    - Links Employee to User account
    - Cannot add other SUPERADMINs to payroll (protect each other)
    """
    # Get users who are NOT already in payroll and are NOT other SUPERADMINs
    existing_employee_user_ids = Employee.objects.filter(user__isnull=False).values_list('user_id', flat=True)
    available_users = User.objects.filter(
        is_active=True,
        is_approved=True
    ).exclude(
        id__in=existing_employee_user_ids
    ).exclude(
        # Cannot add other SUPERADMINs (only yourself)
        Q(role='SUPERADMIN') & ~Q(id=request.user.id)
    ).order_by('first_name', 'last_name')
    
    # If a user_id is provided, pre-populate the form
    selected_user = None
    form_data = {}
    errors = []
    
    user_id = request.GET.get('user_id') or request.POST.get('user_id')
    if user_id:
        try:
            selected_user = available_users.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, 'Selected user not found or already in payroll.')
    
    if request.method == 'POST' and selected_user:
        # Collect form data for re-display on error
        form_data = {
            'employee_type': request.POST.get('employee_type', 'PERMANENT'),
            'position': request.POST.get('position', ''),
            'department': request.POST.get('department', ''),
            'hire_date': request.POST.get('hire_date', ''),
            'basic_salary': request.POST.get('basic_salary', '0'),
            'housing_allowance': request.POST.get('housing_allowance', '0'),
            'transport_allowance': request.POST.get('transport_allowance', '0'),
            'other_allowances': request.POST.get('other_allowances', '0'),
            'kra_pin': request.POST.get('kra_pin', ''),
            'nssf_number': request.POST.get('nssf_number', ''),
            'nhif_number': request.POST.get('nhif_number', ''),
            'bank_name': request.POST.get('bank_name', ''),
            'bank_account_number': request.POST.get('bank_account_number', ''),
            'bank_branch': request.POST.get('bank_branch', ''),
            'pension_contribution_rate': request.POST.get('pension_contribution_rate', '0'),
            'notes': request.POST.get('notes', ''),
            # Checkbox state (True if checked, False if not)
            'employer_remits_paye': request.POST.get('employer_remits_paye') == 'on',
            'employer_remits_nhif': request.POST.get('employer_remits_nhif') == 'on',
            'employer_remits_nssf': request.POST.get('employer_remits_nssf') == 'on',
        }
        
        # Validate required fields
        if not form_data['hire_date']:
            errors.append('Hire date is required.')
        
        if not form_data['position']:
            errors.append('Position/Job title is required.')
        
        # Validate salary is a number
        try:
            basic_salary = Decimal(form_data['basic_salary'] or '0')
            if basic_salary < 0:
                errors.append('Basic salary cannot be negative.')
        except:
            errors.append('Basic salary must be a valid number.')
            basic_salary = Decimal('0')
        
        # Validate allowances are numbers
        try:
            housing_allowance = Decimal(form_data['housing_allowance'] or '0')
        except:
            errors.append('Housing allowance must be a valid number.')
            housing_allowance = Decimal('0')
        
        try:
            transport_allowance = Decimal(form_data['transport_allowance'] or '0')
        except:
            errors.append('Transport allowance must be a valid number.')
            transport_allowance = Decimal('0')
        
        try:
            other_allowances = Decimal(form_data['other_allowances'] or '0')
        except:
            errors.append('Other allowances must be a valid number.')
            other_allowances = Decimal('0')
        
        try:
            pension_rate = Decimal(form_data['pension_contribution_rate'] or '0')
            if pension_rate < 0 or pension_rate > 100:
                errors.append('Pension rate must be between 0 and 100.')
        except:
            errors.append('Pension rate must be a valid number.')
            pension_rate = Decimal('0')
        
        # If no errors, create the employee
        if not errors:
            try:
                # Generate employee ID
                last_employee = Employee.objects.order_by('-id').first()
                next_id = (last_employee.id + 1) if last_employee else 1
                employee_id = f"EMP{next_id:04d}"
                
                employee = Employee(
                    user=selected_user,
                    employee_id=employee_id,
                    first_name=selected_user.first_name,
                    last_name=selected_user.last_name,
                    email=selected_user.email,
                    phone=selected_user.mobile_primary or None,  # User model uses mobile_primary
                    employee_type=form_data['employee_type'],
                    status='ACTIVE',
                    position=form_data['position'] or selected_user.get_role_display(),
                    department=form_data['department'] or None,
                    hire_date=form_data['hire_date'],
                    basic_salary=basic_salary,
                    housing_allowance=housing_allowance,
                    transport_allowance=transport_allowance,
                    other_allowances=other_allowances,
                    kra_pin=form_data['kra_pin'] or None,
                    nssf_number=form_data['nssf_number'] or None,
                    nhif_number=form_data['nhif_number'] or None,
                    # Remittance preferences (checkboxes - unchecked = not in POST)
                    employer_remits_paye=request.POST.get('employer_remits_paye') == 'on',
                    employer_remits_nhif=request.POST.get('employer_remits_nhif') == 'on',
                    employer_remits_nssf=request.POST.get('employer_remits_nssf') == 'on',
                    bank_name=form_data['bank_name'] or None,
                    bank_account_number=form_data['bank_account_number'] or None,
                    bank_branch=form_data['bank_branch'] or None,
                    pension_contribution_rate=pension_rate,
                    notes=form_data['notes'] or None,
                )
                employee.full_clean()
                employee.save()
                
                messages.success(request, f'{employee.full_name} added to payroll as {employee_id}!')
                return redirect('payroll:employee_detail', pk=employee.pk)
                
            except ValidationError as e:
                # Django validation errors
                for field, field_errors in e.message_dict.items():
                    for error in field_errors:
                        errors.append(f'{field.replace("_", " ").title()}: {error}')
            except Exception as e:
                errors.append(f'Unexpected error: Please contact support if this persists.')
        
        # Show errors
        for error in errors:
            messages.error(request, error)
    
    context = {
        'available_users': available_users,
        'selected_user': selected_user,
        'type_choices': Employee.EMPLOYEE_TYPE_CHOICES,
        'today': timezone.now().date().isoformat(),
        'form_data': form_data,  # Retain form data on error
    }
    return render(request, 'payroll/employee_form.html', context)


@superadmin_required
def employee_detail(request, pk):
    """
    View employee details including payroll history
    YTD totals are calculated from PayrollItem records for the current year
    """
    employee = get_object_or_404(Employee, pk=pk)
    
    # Get payroll history for this employee
    payroll_history = PayrollItem.objects.filter(
        employee=employee
    ).select_related('payroll').order_by('-payroll__year', '-payroll__month')[:12]
    
    # Calculate YTD totals from PayrollItem records
    # These are calculated on-the-fly from stored PayrollItem data (ACID compliant)
    current_year = timezone.now().year
    ytd_items = PayrollItem.objects.filter(
        employee=employee,
        payroll__year=current_year
    )
    
    ytd_gross = sum(item.gross_salary for item in ytd_items)
    ytd_paye = sum(item.paye for item in ytd_items)
    ytd_nhif = sum(item.nhif for item in ytd_items)
    ytd_nssf = sum(item.nssf for item in ytd_items)
    ytd_pension = sum(item.pension for item in ytd_items)
    ytd_loan = sum(item.loan_deduction for item in ytd_items)
    ytd_advance = sum(item.advance_deduction for item in ytd_items)
    ytd_other = sum(item.other_deductions for item in ytd_items)
    ytd_net = sum(item.net_salary for item in ytd_items)
    
    ytd_totals = {
        'total_gross': ytd_gross,
        'total_paye': ytd_paye,
        'total_nhif': ytd_nhif,
        'total_nssf': ytd_nssf,
        'total_pension': ytd_pension,
        'total_loan': ytd_loan,
        'total_advance': ytd_advance,
        'total_other': ytd_other,
        'total_deductions': ytd_paye + ytd_nhif + ytd_nssf + ytd_pension + ytd_loan + ytd_advance + ytd_other,
        'total_net': ytd_net,
        'months_count': ytd_items.count(),
    }
    
    # Check if this is another SUPERADMIN's record (cannot edit)
    is_protected = employee.user and employee.user.role == 'SUPERADMIN' and employee.user != request.user
    can_edit = not is_protected
    is_own_record = employee.user == request.user if employee.user else False
    
    context = {
        'employee': employee,
        'payroll_history': payroll_history,
        'ytd_totals': ytd_totals,
        'current_year': current_year,
        'is_linked_user': employee.user is not None,
        'is_protected': is_protected,
        'can_edit': can_edit,
        'is_own_record': is_own_record,
    }
    
    return render(request, 'payroll/employee_detail.html', context)


@superadmin_required
def employee_edit(request, pk):
    """
    Edit employee details
    SUPERADMIN PROTECTION: Cannot edit other SUPERADMINs' payroll data
    """
    employee = get_object_or_404(Employee, pk=pk)
    
    # SUPERADMIN protection: Cannot edit another SUPERADMIN's record
    if employee.user and employee.user.role == 'SUPERADMIN' and employee.user != request.user:
        messages.error(request, 'Access denied. You cannot modify another administrator\'s payroll data.')
        return redirect('payroll:employee_list')
    
    if request.method == 'POST':
        try:
            # Don't allow changing employee_id for linked users
            if not employee.user:
                employee.employee_id = request.POST.get('employee_id')
            
            # Don't allow changing name/email for linked users (sync from User model)
            if employee.user:
                # These stay synced with User model
                pass
            else:
                employee.first_name = request.POST.get('first_name')
                employee.last_name = request.POST.get('last_name')
                employee.email = request.POST.get('email') or None
                employee.phone = request.POST.get('phone') or None
            
            employee.employee_type = request.POST.get('employee_type', 'PERMANENT')
            employee.status = request.POST.get('status', 'ACTIVE')
            employee.position = request.POST.get('position')
            employee.department = request.POST.get('department') or None
            employee.hire_date = request.POST.get('hire_date')
            employee.termination_date = request.POST.get('termination_date') or None
            employee.basic_salary = Decimal(request.POST.get('basic_salary', '0'))
            employee.housing_allowance = Decimal(request.POST.get('housing_allowance', '0') or '0')
            employee.transport_allowance = Decimal(request.POST.get('transport_allowance', '0') or '0')
            employee.other_allowances = Decimal(request.POST.get('other_allowances', '0') or '0')
            employee.kra_pin = request.POST.get('kra_pin') or None
            employee.nssf_number = request.POST.get('nssf_number') or None
            employee.nhif_number = request.POST.get('nhif_number') or None
            # Remittance preferences (checkboxes - unchecked = not in POST)
            employee.employer_remits_paye = request.POST.get('employer_remits_paye') == 'on'
            employee.employer_remits_nhif = request.POST.get('employer_remits_nhif') == 'on'
            employee.employer_remits_nssf = request.POST.get('employer_remits_nssf') == 'on'
            employee.bank_name = request.POST.get('bank_name') or None
            employee.bank_account_number = request.POST.get('bank_account_number') or None
            employee.bank_branch = request.POST.get('bank_branch') or None
            employee.pension_contribution_rate = Decimal(request.POST.get('pension_contribution_rate', '0') or '0')
            employee.notes = request.POST.get('notes') or None
            
            employee.full_clean()
            employee.save()
            
            messages.success(request, f'Employee {employee.full_name} updated successfully!')
            return redirect('payroll:employee_detail', pk=employee.pk)
            
        except Exception as e:
            messages.error(request, f'Error updating employee: {str(e)}')
    
    context = {
        'employee': employee,
        'type_choices': Employee.EMPLOYEE_TYPE_CHOICES,
        'status_choices': Employee.STATUS_CHOICES,
        'editing': True,
        'is_linked_user': employee.user is not None,
        'is_own_record': employee.user == request.user if employee.user else False,
    }
    return render(request, 'payroll/employee_form.html', context)


@superadmin_required
def payroll_list(request):
    """
    List all payroll periods
    """
    payrolls = MonthlyPayroll.objects.all().order_by('-year', '-month')
    
    # Filter by year
    year_filter = request.GET.get('year', '')
    if year_filter:
        payrolls = payrolls.filter(year=int(year_filter))
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        payrolls = payrolls.filter(status=status_filter)
    
    # Get available years for filter
    years = MonthlyPayroll.objects.values_list('year', flat=True).distinct().order_by('-year')
    
    # Pagination
    paginator = Paginator(payrolls, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'payrolls': page_obj,
        'page_obj': page_obj,
        'years': years,
        'filters': {
            'year': year_filter,
            'status': status_filter,
        },
        'status_choices': MonthlyPayroll.STATUS_CHOICES,
    }
    
    return render(request, 'payroll/payroll_list.html', context)


@superadmin_required
def payroll_create(request):
    """
    Create new payroll period and generate payroll items for all active employees
    """
    if request.method == 'POST':
        month = int(request.POST.get('month'))
        year = int(request.POST.get('year'))
        
        # Check if payroll already exists
        if MonthlyPayroll.objects.filter(month=month, year=year).exists():
            messages.error(request, f'Payroll for {month_name[month]} {year} already exists!')
            return redirect('payroll:payroll_create')
        
        try:
            # Create payroll period
            payroll = MonthlyPayroll.objects.create(
                month=month,
                year=year,
                status='DRAFT',
                notes=request.POST.get('notes') or None,
            )
            
            # Generate payroll items for all active employees
            active_employees = Employee.objects.filter(status='ACTIVE')
            items_created = 0
            
            for emp in active_employees:
                item = PayrollItem.objects.create(
                    payroll=payroll,
                    employee=emp,
                    basic_salary=emp.basic_salary,
                    housing_allowance=emp.housing_allowance,
                    transport_allowance=emp.transport_allowance,
                    other_allowances=emp.other_allowances,
                    days_worked=30,  # Default full month
                )
                # Calculate statutory deductions
                item.calculate_statutory_deductions()
                items_created += 1
            
            # Recalculate totals
            payroll.calculate_totals()
            
            messages.success(request, f'Payroll for {month_name[month]} {year} created with {items_created} employees!')
            return redirect('payroll:payroll_detail', pk=payroll.pk)
            
        except Exception as e:
            messages.error(request, f'Error creating payroll: {str(e)}')
    
    # Default to next month
    today = timezone.now().date()
    next_month = today.month + 1 if today.month < 12 else 1
    next_year = today.year if today.month < 12 else today.year + 1
    
    context = {
        'months': [(i, month_name[i]) for i in range(1, 13)],
        'years': range(today.year - 1, today.year + 3),
        'default_month': next_month,
        'default_year': next_year,
    }
    
    return render(request, 'payroll/payroll_form.html', context)


@superadmin_required
def payroll_detail(request, pk):
    """
    View payroll period details with all payroll items
    Shows breakdown of all earnings and deductions
    """
    payroll = get_object_or_404(MonthlyPayroll, pk=pk)
    payroll_items = payroll.payroll_items.select_related('employee').order_by('employee__employee_id')
    
    # Calculate totals for display - ALL deduction types
    total_paye = sum(item.paye for item in payroll_items)
    total_nhif = sum(item.nhif for item in payroll_items)
    total_nssf = sum(item.nssf for item in payroll_items)
    total_pension = sum(item.pension for item in payroll_items)
    total_loan = sum(item.loan_deduction for item in payroll_items)
    total_advance = sum(item.advance_deduction for item in payroll_items)
    total_other = sum(item.other_deductions for item in payroll_items)
    
    # Statutory deductions (PAYE + NHIF + NSSF + Pension)
    total_statutory = total_paye + total_nhif + total_nssf + total_pension
    # Other deductions (Loans + Advances + Other)
    total_other_deductions = total_loan + total_advance + total_other
    # All deductions combined
    total_deductions = total_statutory + total_other_deductions
    
    context = {
        'payroll': payroll,
        'payroll_items': payroll_items,
        # Statutory deductions
        'total_paye': total_paye,
        'total_nhif': total_nhif,
        'total_nssf': total_nssf,
        'total_pension': total_pension,
        'total_statutory': total_statutory,
        # Other deductions
        'total_loan': total_loan,
        'total_advance': total_advance,
        'total_other': total_other,
        'total_other_deductions': total_other_deductions,
        # Grand totals
        'total_deductions': total_deductions,
    }
    
    return render(request, 'payroll/payroll_detail.html', context)


@superadmin_required
def payroll_process(request, pk):
    """
    Process payroll - advance status through workflow
    """
    payroll = get_object_or_404(MonthlyPayroll, pk=pk)
    
    if payroll.is_locked:
        messages.error(request, 'This payroll is finalized and cannot be modified.')
        return redirect('payroll:payroll_detail', pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        status_transitions = {
            'process': ('DRAFT', 'PROCESSING'),
            'approve': ('PROCESSING', 'APPROVED'),
            'pay': ('APPROVED', 'PAID'),
            'finalize': ('PAID', 'FINALIZED'),
        }
        
        if action in status_transitions:
            expected_status, new_status = status_transitions[action]
            
            if payroll.status != expected_status:
                messages.error(request, f'Cannot {action} payroll. Current status is {payroll.get_status_display()}.')
            else:
                payroll.status = new_status
                
                # Set timestamps and perform actions
                if action == 'process':
                    # Recalculate statutory deductions for all payroll items
                    items_recalculated = 0
                    for item in payroll.payroll_items.all():
                        item.calculate_statutory_deductions()
                        items_recalculated += 1
                    
                    # Recalculate payroll totals
                    payroll.calculate_totals()
                    
                    payroll.processed_at = timezone.now()
                    payroll.processed_by = request.user.get_full_name() or request.user.username
                    messages.info(request, f'Recalculated statutory deductions for {items_recalculated} employee(s).')
                elif action == 'approve':
                    payroll.approved_at = timezone.now()
                    payroll.approved_by = request.user.get_full_name() or request.user.username
                elif action == 'pay':
                    payroll.paid_at = timezone.now()
                elif action == 'finalize':
                    payroll.finalized_at = timezone.now()
                
                payroll.save()
                messages.success(request, f'Payroll status updated to {payroll.get_status_display()}')
        else:
            messages.error(request, 'Invalid action')
    
    return redirect('payroll:payroll_detail', pk=pk)


@superadmin_required
def payroll_item_edit(request, pk, item_pk):
    """
    Edit individual PayrollItem - Only allowed when payroll is in DRAFT status
    Allows adjusting ALL earnings and deductions manually
    """
    payroll = get_object_or_404(MonthlyPayroll, pk=pk)
    item = get_object_or_404(PayrollItem, pk=item_pk, payroll=payroll)
    
    # Only allow editing in DRAFT status
    if payroll.status != 'DRAFT':
        messages.error(request, f'Cannot edit payroll items. Payroll is in {payroll.get_status_display()} status.')
        return redirect('payroll:payroll_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            # Update earnings adjustments
            item.overtime_pay = Decimal(request.POST.get('overtime_pay', '0') or '0')
            item.bonus = Decimal(request.POST.get('bonus', '0') or '0')
            
            # Update STATUTORY deductions (can be manually overridden)
            item.paye = Decimal(request.POST.get('paye', '0') or '0')
            item.nhif = Decimal(request.POST.get('nhif', '0') or '0')
            item.nssf = Decimal(request.POST.get('nssf', '0') or '0')
            item.pension = Decimal(request.POST.get('pension', '0') or '0')
            
            # Update OTHER deductions
            item.loan_deduction = Decimal(request.POST.get('loan_deduction', '0') or '0')
            item.advance_deduction = Decimal(request.POST.get('advance_deduction', '0') or '0')
            item.other_deductions = Decimal(request.POST.get('other_deductions', '0') or '0')
            
            # Days worked (for pro-rata calculations)
            item.days_worked = int(request.POST.get('days_worked', '30') or '30')
            
            # Notes
            item.notes = request.POST.get('notes') or None
            
            item.full_clean()
            item.save()
            
            # Recalculate payroll totals
            payroll.calculate_totals()
            
            messages.success(request, f'Updated payroll entry for {item.employee.full_name}')
            return redirect('payroll:payroll_detail', pk=pk)
            
        except Exception as e:
            messages.error(request, f'Error updating payroll item: {str(e)}')
    
    context = {
        'payroll': payroll,
        'item': item,
        'employee': item.employee,
    }
    return render(request, 'payroll/payroll_item_form.html', context)


@superadmin_required
def casual_labor_list(request):
    """
    List casual labor entries with filtering
    """
    entries = CasualLabor.objects.all().order_by('-date')
    
    # Filters
    status_filter = request.GET.get('status', '')
    month_filter = request.GET.get('month', '')
    year_filter = request.GET.get('year', '')
    
    if status_filter:
        entries = entries.filter(payment_status=status_filter)
    
    if month_filter and year_filter:
        entries = entries.filter(date__month=int(month_filter), date__year=int(year_filter))
    elif year_filter:
        entries = entries.filter(date__year=int(year_filter))
    
    # Summary
    totals = entries.aggregate(
        total_amount=Sum('total_amount'),
        total_workers=Sum('number_of_workers'),
        entry_count=Count('id')
    )
    
    pending = entries.filter(payment_status='PENDING').aggregate(
        pending_amount=Sum('total_amount'),
        pending_count=Count('id')
    )
    
    # Pagination
    paginator = Paginator(entries, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available years
    years = CasualLabor.objects.dates('date', 'year', order='DESC')
    
    context = {
        'entries': page_obj,
        'page_obj': page_obj,
        'totals': totals,
        'pending': pending,
        'years': [d.year for d in years],
        'months': [(i, month_name[i]) for i in range(1, 13)],
        'filters': {
            'status': status_filter,
            'month': month_filter,
            'year': year_filter,
        },
    }
    
    return render(request, 'payroll/casual_labor_list.html', context)


@superadmin_required
def casual_labor_create(request):
    """
    Record casual labor work
    """
    if request.method == 'POST':
        try:
            # Handle payment status from checkbox
            payment_status = 'PAID' if request.POST.get('payment_status') == 'PAID' else 'PENDING'
            
            # Get values for calculation
            number_of_workers = int(request.POST.get('number_of_workers', 1))
            daily_rate = Decimal(request.POST.get('daily_rate'))
            
            # Calculate total_amount before validation
            total_amount = (Decimal(number_of_workers) * daily_rate).quantize(Decimal('0.01'))
            
            entry = CasualLabor(
                date=request.POST.get('date'),
                worker_name=request.POST.get('worker_name'),
                number_of_workers=number_of_workers,
                task_description=request.POST.get('task_description'),
                daily_rate=daily_rate,
                total_amount=total_amount,
                payment_status=payment_status,
                notes=request.POST.get('notes') or None,
            )
            entry.full_clean()
            entry.save()
            
            messages.success(request, f'Casual labor entry recorded: {entry.worker_name} - KES {entry.total_amount:,.2f}')
            return redirect('payroll:casual_labor_list')
            
        except Exception as e:
            messages.error(request, f'Error recording casual labor: {str(e)}')
            context = {
                'form_data': request.POST,
                'today': timezone.now().date().isoformat(),
            }
            return render(request, 'payroll/casual_labor_form.html', context)
    
    context = {
        'today': timezone.now().date().isoformat(),
    }
    return render(request, 'payroll/casual_labor_form.html', context)


@superadmin_required
def casual_labor_mark_paid(request, pk):
    """
    Mark a casual labor entry as paid
    """
    entry = get_object_or_404(CasualLabor, pk=pk)
    
    if request.method == 'POST':
        if entry.payment_status == 'PENDING':
            entry.payment_status = 'PAID'
            entry.paid_at = timezone.now()
            entry.save()
            messages.success(request, f'Payment for {entry.worker_name} marked as paid.')
        else:
            messages.info(request, 'This entry is already marked as paid.')
    
    return redirect('payroll:casual_labor_list')


# =============================================================================
# MISCELLANEOUS EXPENSES
# =============================================================================

@superadmin_required
def misc_expense_list(request):
    """
    List miscellaneous expense records with filtering
    """
    expenses = MiscExpenseRecord.objects.select_related('category', 'recorded_by').all()
    
    # Filters
    category_filter = request.GET.get('category', '')
    month_filter = request.GET.get('month', '')
    year_filter = request.GET.get('year', '')
    
    # Apply category filter
    if category_filter:
        try:
            expenses = expenses.filter(category_id=int(category_filter))
        except (ValueError, TypeError):
            pass
    
    # Apply date filters
    if month_filter and year_filter:
        try:
            expenses = expenses.filter(
                expense_date__month=int(month_filter), 
                expense_date__year=int(year_filter)
            )
        except (ValueError, TypeError):
            pass
    elif year_filter:
        try:
            expenses = expenses.filter(expense_date__year=int(year_filter))
        except (ValueError, TypeError):
            pass
    elif month_filter:
        # Month only - filter by that month across all years
        try:
            expenses = expenses.filter(expense_date__month=int(month_filter))
        except (ValueError, TypeError):
            pass
    
    # Summary (calculated on filtered queryset)
    totals = expenses.aggregate(
        total_amount=Sum('amount'),
        entry_count=Count('id')
    )
    
    # Category breakdown
    category_breakdown = expenses.values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Pagination with configurable page size
    per_page_options = [50, 100, 500, 1000]
    per_page = request.GET.get('per_page', '50')
    try:
        per_page_int = int(per_page)
        if per_page_int not in per_page_options:
            per_page_int = 50
    except (ValueError, TypeError):
        per_page_int = 50
    
    paginator = Paginator(expenses, per_page_int)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available years and categories
    years = MiscExpenseRecord.objects.dates('expense_date', 'year', order='DESC')
    categories = MiscExpenseCategory.objects.filter(is_active=True)
    
    context = {
        'expenses': page_obj,
        'page_obj': page_obj,
        'totals': totals,
        'category_breakdown': category_breakdown,
        'years': [d.year for d in years] if years else [timezone.now().year],
        'months': [(i, month_name[i]) for i in range(1, 13)],
        'categories': categories,
        'per_page_options': per_page_options,
        'filters': {
            'category': category_filter,
            'month': month_filter,
            'year': year_filter,
            'per_page': str(per_page_int),
        },
    }
    
    return render(request, 'payroll/misc_expense_list.html', context)


@superadmin_required
def misc_expense_create(request):
    """
    Record a new miscellaneous expense
    """
    categories = MiscExpenseCategory.objects.filter(is_active=True)
    
    if request.method == 'POST':
        try:
            from django.db.models import Max
            from datetime import datetime
            
            # Parse expense date and generate expense number
            expense_date_str = request.POST.get('expense_date')
            expense_date = datetime.strptime(expense_date_str, '%Y-%m-%d').date()
            
            # Generate expense number: EXP-YYYYMMDD-XXX
            date_str = expense_date.strftime('%Y%m%d')
            prefix = f"EXP-{date_str}-"
            
            last_expense = MiscExpenseRecord.objects.filter(
                expense_number__startswith=prefix
            ).aggregate(Max('expense_number'))['expense_number__max']
            
            if last_expense:
                last_seq = int(last_expense.split('-')[-1])
                new_seq = last_seq + 1
            else:
                new_seq = 1
            
            expense_number = f"{prefix}{new_seq:03d}"
            
            expense = MiscExpenseRecord(
                expense_number=expense_number,
                category_id=int(request.POST.get('category')),
                description=request.POST.get('description'),
                expense_date=expense_date,
                amount=Decimal(request.POST.get('amount')),
                reference_number=request.POST.get('reference_number', '') or '',
                notes=request.POST.get('notes', '') or '',
                recorded_by=request.user,
            )
            expense.full_clean()
            expense.save()
            
            messages.success(request, f'Expense recorded: {expense.expense_number} - KES {expense.amount:,.2f}')
            return redirect('payroll:misc_expense_list')
            
        except Exception as e:
            messages.error(request, f'Error recording expense: {str(e)}')
            context = {
                'form_data': request.POST,
                'categories': categories,
                'today': timezone.now().date().isoformat(),
            }
            return render(request, 'payroll/misc_expense_form.html', context)
    
    context = {
        'categories': categories,
        'today': timezone.now().date().isoformat(),
    }
    return render(request, 'payroll/misc_expense_form.html', context)


@superadmin_required
def misc_expense_detail(request, pk):
    """
    View details of a miscellaneous expense record
    Note: Expense records are immutable (bank ledger policy)
    """
    expense = get_object_or_404(
        MiscExpenseRecord.objects.select_related('category', 'recorded_by'),
        pk=pk
    )
    
    context = {
        'expense': expense,
    }
    
    return render(request, 'payroll/misc_expense_detail.html', context)

