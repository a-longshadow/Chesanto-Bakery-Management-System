"""
Seed Employees Management Command
=================================
Creates sample employees for the bakery system.

This creates:
- 4 Salesmen (SALESMAN role) - Required for dispatch workflows
- 1 Dispatch Officer (DISPATCH role) - For creating dispatches
- 1 Production Manager (PRODUCT_MANAGER role) - For production workflows
- 1 Accountant (ADMIN role) - For financial access

All employees are created with:
- Default password (must change on first login)
- Assigned employee_id (CHE001, CHE002, etc.)
- Commission rates for salesmen

Usage:
    python manage.py seed_employees
    python manage.py seed_employees --reset  # Reactivate/reset existing
    
After running:
    - System ready for dispatch creation (salesmen available)
    - Demo passwords: 'Chesanto2025!' (must change on first login)
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from django.utils import timezone

from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Seed employees for dispatch and production workflows'

    # Real Chesanto employees data
    # Format: (employee_id, email, first_name, last_name, role, mobile, id_number, position, department, basic_salary)
    
    # Salesmen (from provided list - essential for dispatch)
    SALESMEN = [
        ('CHE001', 'joel.enos@chesanto.co.ke', 'Joel', 'Enos', 'SALESMAN', 
         '+254700000001', '', 'Salesman', 'Sales', Decimal('0.00')),
        ('CHE002', 'jeremiah.atwoli@chesanto.co.ke', 'Jeremiah', 'Atwoli', 'SALESMAN', 
         '+254700000002', '', 'Salesman', 'Sales', Decimal('0.00')),
        ('CHE003', 'mike.salesman@chesanto.co.ke', 'Mike', '', 'SALESMAN', 
         '+254700000003', '', 'Salesman', 'Sales', Decimal('0.00')),
        ('CHE004', 'okiya.salesman@chesanto.co.ke', 'Okiya', '', 'SALESMAN', 
         '+254700000004', '', 'Salesman', 'Sales', Decimal('0.00')),
        ('CHE005', 'edwardo@chesanto.co.ke', 'Edwardo', '', 'SALESMAN', 
         '+254700000005', '', 'Salesman', 'Sales', Decimal('0.00')),
        ('CHE006', 'quinto.matayos@chesanto.co.ke', 'Quinto', 'Matayos', 'SALESMAN', 
         '+254700000006', '', 'Salesman', 'Sales', Decimal('0.00')),
        ('CHE007', 'mike.kimwanga@chesanto.co.ke', 'Mike', 'Kimwanga Depot', 'SALESMAN', 
         '+254700000007', '', 'Salesman - Depot', 'Sales', Decimal('0.00')),
    ]
    
    # General staff from employee records
    STAFF = [
        # Production/Bakery Staff
        ('CHE101', 'gabriel.imo@chesanto.co.ke', 'Gabriel', 'Imo', 'STAFF', 
         '+254757081548', '7421512', 'Baker', 'Production', Decimal('0.00')),
        ('CHE102', 'dominic.epale@chesanto.co.ke', 'Dominic', 'Epale', 'STAFF', 
         '+254799909389', '30233782', 'Baker', 'Production', Decimal('0.00')),
        ('CHE103', 'joseph.echikai@chesanto.co.ke', 'Joseph', 'Echikai', 'STAFF', 
         '+254757558508', '38686818', 'Baker', 'Production', Decimal('0.00')),
        ('CHE104', 'denis.ojakapel@chesanto.co.ke', 'Denis', 'Ojakapel', 'STAFF', 
         '+254799209746', '40460097', 'Baker', 'Production', Decimal('0.00')),
        ('CHE105', 'evans.omot@chesanto.co.ke', 'Evans', 'Omot', 'STAFF', 
         '+254703483276', '24198407', 'Baker', 'Production', Decimal('0.00')),
        ('CHE106', 'rose.ndiema@chesanto.co.ke', 'Rose', 'Ndiema', 'STAFF', 
         '+254703578772', '13717373', 'Baker', 'Production', Decimal('0.00')),
        ('CHE107', 'polycorp.ikwara@chesanto.co.ke', 'Polycorp', 'Ikwara', 'STAFF', 
         '+254793978880', '41312615', 'Baker', 'Production', Decimal('0.00')),
        ('CHE108', 'collins.ijaa@chesanto.co.ke', 'Collins', 'Ijaa', 'STAFF', 
         '+254797515677', '37578414', 'Baker', 'Production', Decimal('0.00')),
        ('CHE109', 'judith.atwani@chesanto.co.ke', 'Judith', 'Atwani', 'STAFF', 
         '+254797125144', '40214698', 'Baker', 'Production', Decimal('0.00')),
        ('CHE110', 'everline.barasa@chesanto.co.ke', 'Everline', 'Barasa', 'STAFF', 
         '+254700263765', '26373175', 'Baker', 'Production', Decimal('0.00')),
        ('CHE111', 'bramuel.emee@chesanto.co.ke', 'Bramuel', 'Emee', 'STAFF', 
         '+254700240616', '26900526', 'Baker', 'Production', Decimal('0.00')),
        ('CHE112', 'stephen.etyang@chesanto.co.ke', 'Stephen', 'Etyang', 'STAFF', 
         '+254748336513', '38463925', 'Baker', 'Production', Decimal('0.00')),
        ('CHE113', 'martin.ikapel@chesanto.co.ke', 'Martin', 'Ikapel', 'STAFF', 
         '+254740816376', '9955897', 'Baker', 'Production', Decimal('0.00')),
        ('CHE114', 'philis.atyang@chesanto.co.ke', 'Philis', 'Atyang', 'STAFF', 
         '+254707133942', '27078393', 'Baker', 'Production', Decimal('0.00')),
        ('CHE115', 'gladys.okitoi@chesanto.co.ke', 'Gladys', 'Okitoi', 'STAFF', 
         '+254757161657', '20967093', 'Baker', 'Production', Decimal('0.00')),
        ('CHE116', 'mary.ikadikor@chesanto.co.ke', 'Mary', 'Ikadikor', 'STAFF', 
         '+254718363307', '25348948', 'Baker', 'Production', Decimal('0.00')),
        ('CHE117', 'nancy.etyang@chesanto.co.ke', 'Nancy', 'Etyang', 'STAFF', 
         '+254793591511', '26452355', 'Baker', 'Production', Decimal('0.00')),
        ('CHE118', 'martina.emongiro@chesanto.co.ke', 'Martina', 'Emongiro', 'STAFF', 
         '+254742475992', '13170785', 'Baker', 'Production', Decimal('0.00')),
        ('CHE119', 'soitah.amos@chesanto.co.ke', 'Soitah', 'Amos', 'STAFF', 
         '+254757556876', '40785104', 'Baker', 'Production', Decimal('0.00')),
        ('CHE120', 'irene.nyangweso@chesanto.co.ke', 'Irene', 'Nyangweso', 'STAFF', 
         '+254793697100', '29660575', 'Baker', 'Production', Decimal('0.00')),
        ('CHE121', 'quinto.epuret@chesanto.co.ke', 'Quinto', 'Epuret', 'STAFF', 
         '+254798288785', '30760734', 'Baker', 'Production', Decimal('0.00')),
        ('CHE122', 'evans.etyang@chesanto.co.ke', 'Evans', 'Etyang', 'STAFF', 
         '+254768846085', '35808649', 'Baker', 'Production', Decimal('0.00')),
        ('CHE123', 'michael.iraat@chesanto.co.ke', 'Michael', 'Iraat', 'STAFF', 
         '+254743272070', '34810497', 'Baker', 'Production', Decimal('0.00')),
        ('CHE124', 'kevin.simiyo@chesanto.co.ke', 'Kevin', 'Masibo Simiyo', 'STAFF', 
         '+254727884367', '35876617', 'Baker', 'Production', Decimal('0.00')),
        ('CHE125', 'eddah.silungi@chesanto.co.ke', 'Eddah', 'Silungi', 'STAFF', 
         '+254724912696', '22751056', 'Baker', 'Production', Decimal('0.00')),
        ('CHE126', 'enous.mututu@chesanto.co.ke', 'Enous', 'Mututu', 'STAFF', 
         '+254726802396', '26027507', 'Baker', 'Production', Decimal('0.00')),
        ('CHE127', 'mike.okiya@chesanto.co.ke', 'Mike', 'Okiya', 'STAFF', 
         '+254700000000', '42760324', 'Baker', 'Production', Decimal('0.00')),
        ('CHE128', 'chrispinos.okochii@chesanto.co.ke', 'Chrispinos', 'Okochii', 'STAFF', 
         '+254758748970', '37867718', 'Baker', 'Production', Decimal('0.00')),
        ('CHE129', 'elizabeth.ichelai@chesanto.co.ke', 'Elizabeth', 'Ichelai', 'STAFF', 
         '+254769190710', '11111111', 'Baker', 'Production', Decimal('0.00')),
        ('CHE130', 'michael.opollo@chesanto.co.ke', 'Michael', 'Opollo', 'STAFF', 
         '+254712876102', '37036228', 'Baker', 'Production', Decimal('0.00')),
        ('CHE131', 'pamela.onyaa@chesanto.co.ke', 'Pamela', 'Onyaa', 'STAFF', 
         '+254743738116', '31913608', 'Baker', 'Production', Decimal('0.00')),
    ]
    
    # System/Management accounts (placeholders)
    MANAGEMENT = [
        # Dispatch Officer (placeholder)
        ('CHE010', 'dispatch@chesanto.co.ke', 'Dispatch', 'Officer', 'DISPATCH', 
         '+254700000010', '', 'Dispatch Officer', 'Operations', Decimal('0.00')),
        
        # Production Manager (placeholder)
        ('CHE020', 'production@chesanto.co.ke', 'Production', 'Manager', 'PRODUCT_MANAGER', 
         '+254700000020', '', 'Production Manager', 'Production', Decimal('0.00')),
    ]
    
    # Combine all employees
    SAMPLE_EMPLOYEES = SALESMEN + STAFF + MANAGEMENT

    # Default password for seed employees (must change on first login)
    DEFAULT_PASSWORD = 'Chesanto2025!'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing employees to active state and update passwords',
        )
        parser.add_argument(
            '--password',
            type=str,
            default=self.DEFAULT_PASSWORD,
            help=f'Password for new employees (default: {self.DEFAULT_PASSWORD})',
        )

    def handle(self, *args, **options):
        reset = options['reset']
        password = options['password']

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('👥 SEEDING EMPLOYEES: Chesanto Bakery'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        if reset:
            self.stdout.write(self.style.WARNING('⚠️  RESET mode: Will reactivate and reset passwords\n'))

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for emp_data in self.SAMPLE_EMPLOYEES:
                employee_id, email, first_name, last_name, role, mobile, id_number, position, department, salary = emp_data

                try:
                    # Check if user already exists
                    existing = User.objects.filter(email=email).first()

                    if existing:
                        if reset:
                            # Reset/update existing user
                            existing.employee_id = employee_id
                            existing.role = role
                            existing.is_active = True
                            existing.is_approved = True
                            existing.must_change_password = True
                            existing.position = position
                            existing.department = department
                            existing.basic_salary = salary
                            existing.pay_per_day = salary / 30 if salary else None
                            if id_number:
                                existing.national_id = id_number
                            existing.set_password(password)
                            existing.save()
                            updated_count += 1
                            status = self.style.WARNING('RESET')
                        else:
                            skipped_count += 1
                            status = self.style.SUCCESS('EXISTS')
                    else:
                        # Create new employee
                        user = User.objects.create_user(
                            email=email,
                            password=password,
                            first_name=first_name,
                            last_name=last_name,
                            mobile_primary=mobile,
                            role=role,
                            employee_id=employee_id,
                            position=position,
                            department=department,
                            basic_salary=salary,
                            pay_per_day=salary / 30 if salary else None,
                            national_id=id_number if id_number else None,
                            is_active=True,
                            is_approved=True,
                            must_change_password=True,  # Force password change on first login
                            email_verified=True,
                            email_verified_at=timezone.now(),
                        )
                        
                        # Set commission defaults for salesmen
                        if role == 'SALESMAN':
                            user.commission_rate = Decimal('7.00')
                            user.sales_target = Decimal('35000.00')
                            user.save()
                        
                        created_count += 1
                        status = self.style.SUCCESS('CREATED')

                    # Display result
                    role_label = User.Role(role).label if role in [r.value for r in User.Role] else role
                    self.stdout.write(f'  [{employee_id}] {first_name} {last_name} ({role_label}) - {status}')

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  [{employee_id}] {first_name} {last_name} - ERROR: {str(e)}')
                    )

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✅ Employee seeding complete!'))
        self.stdout.write(f'   Created: {created_count}')
        self.stdout.write(f'   Reset: {updated_count}')
        self.stdout.write(f'   Skipped (already exists): {skipped_count}')
        self.stdout.write('')
        
        # Show employee counts by role
        self.stdout.write(self.style.WARNING('📊 Employee Counts by Role:'))
        for role in User.Role:
            count = User.objects.filter(role=role.value, is_active=True).count()
            if count > 0:
                self.stdout.write(f'   {role.label}: {count}')
        
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('🔐 Login Credentials:'))
        self.stdout.write(f'   Password: {password}')
        self.stdout.write('   (All employees must change password on first login)')
        self.stdout.write('')
        self.stdout.write('Next steps:')
        self.stdout.write('  1. Create dispatches at /sales/dispatch/new/')
        self.stdout.write('  2. Manage employees at /admin/accounts/user/')
        self.stdout.write('  3. Update employee details as needed')
