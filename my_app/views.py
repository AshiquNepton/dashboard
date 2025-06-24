import json
import re
import random
import string
from datetime import datetime, timedelta

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse

from my_app import models
from .models import Company
from django.http import JsonResponse
from django.db.models import Sum
from .models import Transaction
from django.db.models import Max

from django.db.models import Case, When, Value, CharField
from django.db.models import Subquery, OuterRef

# Create your views here.
from my_app.models import ItemGroups


# def is_mobile_device(request):
#     """Helper function to detect mobile devices"""
#     user_agent = request.META.get('HTTP_USER_AGENT', '')
#     mobile_patterns = [
#         r'Mobile|iP(hone|od|ad)|Android|BlackBerry|IEMobile|Kindle|NetFront|Silk-Accelerated|(hpw|web)OS|Fennec|Minimo|Opera M(obi|ini)|Blazer|Dolfin|Dolphin|Skyfire|Zune',
#         r'tablet|ipad|playbook|silk',
#     ]
#     mobile_regex = re.compile('|'.join(mobile_patterns), re.IGNORECASE)
#     return bool(mobile_regex.search(user_agent))


# def mobile_render(request, template_name, context=None):
#     """Enhanced render function with mobile detection"""
#     if context is None:
#         context = {}
#
#     # Add mobile detection to context
#     context.update({
#         'is_mobile': is_mobile_device(request),
#         'user_agent': request.META.get('HTTP_USER_AGENT', '')
#     })
#
#     return render(request, template_name, context)


def login(request):
    # """Login view with mobile detection"""
    context = {
        'page_title': 'Login',
    }
    return render(request, 'login.html',context)


def login_post(request):
    # Check if the request method is POST
    if request.method != 'POST':
        return HttpResponse("""<script> alert('Invalid request method'); window.location='/login';</script>""")

    # Safely get POST data with get() method instead of direct access
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()

    # Check if both username and password are provided
    if not username or not password:
        return HttpResponse("""<script> alert('Enter Username and password'); window.location='/login';</script>""")

    try:
        # Your authentication logic
        user = ItemGroups.objects.get(description=username, narration=password)

        # Store only JSON-serializable data in session
        request.session['lid'] = user.group_id
        request.session['username'] = username

        # Extract the actual company_code string from the ForeignKey
        if user.company_code:
            request.session['cmpny'] = user.company_code.company_code  # Get the primary key value

            # Optionally store company details for quick access
            request.session['company_info'] = {
                'company_code': user.company_code.company_code,
                'name': user.company_code.name,
                'under': user.company_code.under,
                'contact_person': user.company_code.contact_person,
                'mobile': user.company_code.mobile,
                'email': user.company_code.email
            }
        else:
            request.session['cmpny'] = None
            request.session['company_info'] = None

        if user.group_id == 1:
            return HttpResponse("""<script>window.location='/admin_dash';</script>""")
        else:
            return HttpResponse("""<script>window.location='/user_dash';</script>""")

    except ItemGroups.DoesNotExist:
        return HttpResponse("""<script> alert('Invalid username or password'); window.location='/login';</script>""")
    except Exception as e:
        print(f"Login error: {e}")
        return HttpResponse("""<script> alert('Login failed. Please try again.'); window.location='/login';</script>""")

def admin_dash(request):
    """Display the admin dashboard with data from database"""
    if 'lid' not in request.session:
        return HttpResponse("""<script> alert('Please login first'); window.location='/login';</script>""")

    # Get parent company names using subquery
    parent_name_subquery = Company.objects.filter(
        company_code=OuterRef('under')
    ).values('name')[:1]

    # Annotate companies with parent company names
    companies = Company.objects.annotate(
        parent_company_name=Case(
            When(under__isnull=True, then=Value('No Parent')),
            When(under=0, then=Value('Head Office')),  # Only check for integer 0
            default=Subquery(parent_name_subquery),
            output_field=CharField()
        )
    ).all()

    item_groups = ItemGroups.objects.all()

    # Get companies with expiry dates within next 30 days AND already expired companies
    today = datetime.now().date()
    expiry_threshold = today + timedelta(days=30)
    expiring_companies = Company.objects.filter(expiry_date__lte=expiry_threshold)

    # Generate next group ID
    try:
        last_group = ItemGroups.objects.order_by('-group_id').first()
        if last_group:
            next_group_id = (last_group.group_id + 1)
        else:
            next_group_id = 1  # Changed to integer to match your model
    except Exception as e:
        print(f"Error generating next group ID: {e}")
        next_group_id = 1  # Changed to integer to match your model

    next_company_code = generate_next_company_code()

    context = {
        'companies': companies,
        'item_groups': item_groups,
        'expiring_companies': expiring_companies,
        'next_group_id': next_group_id,
        'next_company_code': next_company_code,
    }
    return render(request, 'admin/admin_dash.html', context)


def generate_next_company_code():
    """Generate next company code as integer (1, 2, etc.)"""
    try:
        # Get max company code
        max_code = Company.objects.aggregate(max_code=Max('company_code'))['max_code']
        if max_code is None:
            return 1
        return max_code + 1
    except Exception as e:
        print(f"Error generating company code: {e}")
        return 1  # fallback to 1 if error occurs

def generate_authentication_code():
    """Generate 8-character alphanumeric code"""
    characters = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
    while True:
        code = ''.join(random.choices(characters, k=8))
        # Check if code already exists
        if not Company.objects.filter(authentication=code).exists():
            return code


def add_company_post(request):
    """Add new company to database"""
    if request.method != 'POST':
        return HttpResponse("""""")

    if 'lid' not in request.session:
        return HttpResponse("""""")

    # Generate company code automatically
    company_code = generate_next_company_code()
    # Generate authentication code
    auth_code = generate_authentication_code()

    # Get form data
    under = request.POST.get('companyUnder', '0').strip()  # Default to '0' if not provided
    company_name = request.POST['companyName'].strip()
    reg_date = request.POST['regDate']
    expiry_years = request.POST['expiryYears']
    contact_person = request.POST['contactPerson'].strip()
    mobile = request.POST['mobile'].strip()
    email = request.POST['email'].strip()

    # Validate required fields
    if not all([company_name, reg_date, expiry_years, contact_person, mobile, email]):
        return HttpResponse("""""")

    try:
        # Convert under to integer (default to 0 if empty)
        under_int = int(under) if under else 0

        # Calculate expiry date
        reg_date_obj = datetime.strptime(reg_date, '%Y-%m-%d').date()
        expiry_date_obj = reg_date_obj.replace(year=reg_date_obj.year + int(expiry_years))

        # Create new company
        Company.objects.create(
            company_code=company_code,
            under=under_int,
            name=company_name,
            reg_date=reg_date_obj,
            expiry_date=expiry_date_obj,
            contact_person=contact_person,
            mobile=mobile,
            email=email,
            authentication=auth_code
        )

        return HttpResponse("""<script> alert('Company Added'); window.location='/admin_dash';</script>""")
    except Exception as e:
        print(f"Error adding company: {e}")
        return HttpResponse("""<script> alert('Company Adding Failed'); window.location='/admin_dash';</script>""")

def edit_company_post(request):
    """Edit existing company"""
    if request.method != 'POST':
        return HttpResponse("""<script> alert('Invalid request method'); window.location='/admin_dash';</script>""")

    if 'lid' not in request.session:
        return HttpResponse("""<script> alert('Please login first'); window.location='/login';</script>""")

    # Get form data
    company_code = request.POST['editCompanyCode'].strip()  # This is the original company_code
    new_company_code = request.POST['editCompanyCode'].strip()  # This could be changed
    under = request.POST['editCompanyUnder'].strip()
    company_name = request.POST['editCompanyName'].strip()
    reg_date = request.POST['editRegDate']
    expiry_years = request.POST['editExpiryYears']
    contact_person = request.POST['editContactPerson'].strip()
    mobile = request.POST['editMobile'].strip()
    email = request.POST['editEmail'].strip()

    # Validate required fields
    if not all([new_company_code, company_name, reg_date, expiry_years, contact_person, mobile, email]):
        return HttpResponse("""<script> alert('All fields are required'); window.location='/admin_dash';</script>""")

    try:
        # Get the original company using the hidden field value
        original_company_code = request.POST['originalCompanyCode']  # We'll add this hidden field
        company = get_object_or_404(Company, company_code=original_company_code)

        # Check if new company code already exists for other companies
        if Company.objects.filter(company_code=new_company_code).exclude(company_code=original_company_code).exists():
            return HttpResponse(
                """<script> alert('Company code already exists'); window.location='/admin_dash';</script>""")

        # Calculate expiry date
        reg_date_obj = datetime.strptime(reg_date, '%Y-%m-%d').date()
        expiry_date_obj = reg_date_obj.replace(year=reg_date_obj.year + int(expiry_years))

        # Update company
        company.company_code = new_company_code
        company.under = under if under != '0' else 'Head Office'
        company.name = company_name
        company.reg_date = reg_date_obj
        company.expiry_date = expiry_date_obj
        company.contact_person = contact_person
        company.mobile = mobile
        company.email = email
        company.save()

        return HttpResponse(
            """<script> alert('Company updated successfully'); window.location='/admin_dash';</script>""")

    except Exception as e:
        print(f"Error updating company: {e}")
        return HttpResponse("""<script> alert('Failed to update company'); window.location='/admin_dash';</script>""")


def delete_company_post(request):
    """Delete company"""
    if request.method != 'POST':
        return HttpResponse("""<script> alert('Invalid request method'); window.location='/admin_dash';</script>""")

    if 'lid' not in request.session:
        return HttpResponse("""<script> alert('Please login first'); window.location='/login';</script>""")

    company_code = request.POST.get('companyCode')  # Changed from companyId

    try:
        company = get_object_or_404(Company, company_code=company_code)  # Changed from id=company_id

        # Check if company has associated item groups
        if ItemGroups.objects.filter(company_code=company).exists():
            return HttpResponse(
                """<script> alert('Cannot delete company. It has associated item groups.'); window.location='/admin_dash';</script>""")

        company.delete()
        return HttpResponse(
            """<script> alert('Company deleted successfully'); window.location='/admin_dash';</script>""")

    except Exception as e:
        print(f"Error deleting company: {e}")
        return HttpResponse("""<script> alert('Failed to delete company'); window.location='/admin_dash';</script>""")


def get_next_group_id(request):
    """Get the next available group ID"""
    if 'lid' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    try:
        # Get the last group ID
        last_group = ItemGroups.objects.order_by('-group_id').first()
        if last_group:
            next_id = int(last_group.group_id + 1)
        else:
            next_id = '1'

        return JsonResponse({'next_id': next_id})

    except Exception as e:
        print(f"Error generating next group ID: {e}")
        return JsonResponse({'error': 'Failed to generate group ID'}, status=500)


def add_item_group_post(request):
    """Add new item group to database"""
    if request.method != 'POST':
        return HttpResponse("""<script> alert('Invalid request method'); window.location='/admin_dash';</script>""")

    if 'lid' not in request.session:
        return HttpResponse("""<script> alert('Please login first'); window.location='/login';</script>""")

    # Get form data
    description = request.POST['groupDescription'].strip()
    category = request.POST['groupCategory'].strip()
    date = request.POST['groupDate']
    narration = request.POST['groupNarration'].strip()
    company_code = request.POST['groupCompany'].strip()
    type_code = request.POST.get('groupTypeCode', '').strip()

    # Validate required fields
    if not all([description, category]):
        return HttpResponse("""<script> alert('All fields are required'); window.location='/admin_dash';</script>""")

    try:
        # Get company instance or set to None
        company = None
        if company_code and company_code.strip():
            try:
                company = Company.objects.get(company_code=company_code)
            except Company.DoesNotExist:
                return HttpResponse(
                    """<script> alert('Selected company does not exist'); window.location='/admin_dash';</script>""")

        # Check if TypeCode already exists for the same company and category
        if type_code and company:
            existing_item = ItemGroups.objects.filter(
                company_code=company,
                category=category,
                typeCode=type_code
            ).exists()

            if existing_item:
                return HttpResponse(
                    """<script> alert('TypeCode already exists for this company and category'); window.location='/admin_dash';</script>""")

        # Generate group ID
        last_group = ItemGroups.objects.order_by('-group_id').first()
        if last_group:
            new_id = int(last_group.group_id + 1)
        else:
            new_id = '1'

        # Create new item group
        ItemGroups.objects.create(
            group_id=new_id,
            description=description,
            category=category,
            date=datetime.strptime(date, '%Y-%m-%d').date(),
            narration=narration,
            company_code=company,
            typeCode=type_code if type_code else None
        )

        return HttpResponse(
            """<script> alert('Item Group added successfully'); window.location='/admin_dash';</script>""")

    except Exception as e:
        print(f"Error adding item group: {e}")
        return HttpResponse("""<script> alert('Failed to add item group'); window.location='/admin_dash';</script>""")

    """Add new item group to database"""
    if request.method != 'POST':
        return HttpResponse("""<script> alert('Invalid request method'); window.location='/admin_dash';</script>""")

    if 'lid' not in request.session:
        return HttpResponse("""<script> alert('Please login first'); window.location='/login';</script>""")

    # Get form data
    description = request.POST['groupDescription'].strip()
    category = request.POST['groupCategory'].strip()
    date = request.POST['groupDate']
    narration = request.POST['groupNarration'].strip()
    company_code = request.POST['groupCompany'].strip()

    # Validate required fields
    if not all([description, category]):
        return HttpResponse("""<script> alert('All fields are required'); window.location='/admin_dash';</script>""")

    try:
        # Generate group ID
        last_group = ItemGroups.objects.order_by('-group_id').first()
        if last_group:
            # last_id = int(last_group.group_id.replace('GRP', ''))
            new_id = int(last_group.group_id + 1)
        else:
            new_id = '1'

        # Get company instance or set to None
        company = None
        if company_code and company_code.strip():  # Check if company_code is provided and not empty
            try:
                company = Company.objects.get(company_code=company_code)
            except Company.DoesNotExist:
                return HttpResponse(
                    """<script> alert('Selected company does not exist'); window.location='/admin_dash';</script>""")

        # Create new item group - assign the company instance, not just the code
        ItemGroups.objects.create(
            group_id=new_id,
            description=description,
            category=category,
            date=datetime.strptime(date, '%Y-%m-%d').date(),
            narration=narration,
            company_code=company  # Assign the Company instance, not the string
        )

        return HttpResponse(
            """<script> alert('Item Group added successfully'); window.location='/admin_dash';</script>""")

    except Exception as e:
        print(f"Error adding item group: {e}")
        return HttpResponse("""<script> alert('Failed to add item group'); window.location='/admin_dash';</script>""")


def edit_item_group_post(request):
    """Edit existing item group"""
    if request.method != 'POST':
        return HttpResponse("""<script> alert('Invalid request method'); window.location='/admin_dash';</script>""")

    if 'lid' not in request.session:
        return HttpResponse("""<script> alert('Please login first'); window.location='/login';</script>""")

    # Get form data
    group_id = request.POST['editGroupId']
    description = request.POST['editGroupDescription'].strip()
    category = request.POST['editGroupCategory'].strip()
    date = request.POST['editGroupDate']
    narration = request.POST['editGroupNarration'].strip()
    company_code = request.POST['editGroupCompany'].strip()
    type_code = request.POST.get('editGroupTypeCode', '').strip()

    # Validate required fields
    if not all([description, category]):
        return HttpResponse("""<script> alert('All fields are required'); window.location='/admin_dash';</script>""")

    try:
        item_group = get_object_or_404(ItemGroups, group_id=group_id)

        # Get company instance or set to None
        company = None
        if company_code and company_code.strip():
            try:
                company = Company.objects.get(company_code=company_code)
            except Company.DoesNotExist:
                return HttpResponse(
                    """<script> alert('Selected company does not exist'); window.location='/admin_dash';</script>""")

        # Check if TypeCode already exists for the same company and category (excluding current record)
        if type_code and company:
            existing_item = ItemGroups.objects.filter(
                company_code=company,
                category=category,
                typeCode=type_code
            ).exclude(group_id=group_id).exists()

            if existing_item:
                return HttpResponse(
                    """<script> alert('TypeCode already exists for this company and category'); window.location='/admin_dash';</script>""")

        # Update item group
        item_group.description = description
        item_group.category = category
        item_group.date = datetime.strptime(date, '%Y-%m-%d').date()
        item_group.narration = narration
        item_group.company_code = company
        item_group.typeCode = type_code if type_code else None
        item_group.save()

        return HttpResponse(
            """<script> alert('Item Group updated successfully'); window.location='/admin_dash';</script>""")

    except Exception as e:
        print(f"Error updating item group: {e}")
        return HttpResponse(
            """<script> alert('Failed to update item group'); window.location='/admin_dash';</script>""")


def delete_item_group_post(request):
    """Delete item group"""
    if request.method != 'POST':
        return HttpResponse("""<script> alert('Invalid request method'); window.location='/admin_dash';</script>""")

    if 'lid' not in request.session:
        return HttpResponse("""<script> alert('Please login first'); window.location='/login';</script>""")

    group_id = request.POST.get('groupId')

    try:
        item_group = get_object_or_404(ItemGroups, group_id=group_id)
        item_group.delete()
        return HttpResponse(
            """<script> alert('Item Group deleted successfully'); window.location='/admin_dash';</script>""")
    except:
        return HttpResponse(
            """<script> alert('Item Group cannot be deleted'); window.location='/admin_dash';</script>""")

def get_company_data(request):
    """Get single company data for editing"""
    if 'lid' not in request.session:
        return HttpResponse('Unauthorized', status=401)

    company_code = request.GET.get('company_code')

    if not company_code:
        return JsonResponse({'error': 'Company code is required'}, status=400)

    try:
        company = Company.objects.get(company_code=company_code)
        # Calculate years difference for expiry
        years_diff = company.expiry_date.year - company.reg_date.year

        data = {
            'company_code': company.company_code,  # This will be readonly in edit mode
            'under': company.under,
            'name': company.name,
            'reg_date': company.reg_date.strftime('%Y-%m-%d'),
            'expiry_years': years_diff,
            'contact_person': company.contact_person,
            'mobile': company.mobile,
            'email': company.email
        }
        return JsonResponse(data)
    except Company.DoesNotExist:
        return JsonResponse({'error': 'Company not found'}, status=404)
    except Exception as e:
        print(f"Error getting company data: {e}")
        return JsonResponse({'error': 'Failed to get company data'}, status=500)


def get_item_group_data(request):
    """Get single item group data for editing"""
    if 'lid' not in request.session:
        return HttpResponse('Unauthorized', status=401)

    group_id = request.GET.get('id')
    try:
        item_group = ItemGroups.objects.get(group_id=group_id)
        data = {
            'group_id': item_group.group_id,
            'description': item_group.description,
            'category': item_group.category,
            'date': item_group.date.strftime('%Y-%m-%d'),
            'narration': item_group.narration,
            'company_code': item_group.company_code.company_code if item_group.company_code else ''
        }
        return JsonResponse(data)
    except ItemGroups.DoesNotExist:
        return JsonResponse({'error': 'Item Group not found'}, status=404)


def get_expiring_companies(request):
    """Get companies that are expiring soon for dashboard alerts"""
    if 'lid' not in request.session:
        return HttpResponse('Unauthorized', status=401)

    # Get companies expiring in next 30 days AND already expired
    today = datetime.now().date()
    expiry_threshold = today + timedelta(days=30)

    expiring_companies = Company.objects.filter(
        expiry_date__lte=expiry_threshold
    ).values('company_code', 'name', 'expiry_date')

    companies_list = []
    for company in expiring_companies:
        days_remaining = (company['expiry_date'] - today).days
        companies_list.append({
            'company_code': company['company_code'],
            'company_name': company['name'],
            'expiry_date': company['expiry_date'].strftime('%Y-%m-%d'),
            'days_remaining': days_remaining
        })

    return JsonResponse({'expiring_companies': companies_list})


def user_dash(request):
    """Display the user dashboard with company data"""
    if 'lid' not in request.session:
        return HttpResponse("""<script> alert('Please login first'); window.location='/login';</script>""")

    # Get user's company information
    user_company_code = request.session.get('cmpny')
    user_company_info = request.session.get('company_info')

    context = {
        'user_company_code': user_company_code,
        'user_company_info': user_company_info,
        'page_title': 'User Dashboard'
    }

    return render(request, 'user/user_dash.html', context)


def set_selected_company(request):
    """Set selected company in session"""
    if 'lid' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            company_code = data.get('company_code')

            if company_code:
                # Convert to integer if it's a string
                if isinstance(company_code, str):
                    try:
                        company_code = int(company_code)
                    except ValueError:
                        return JsonResponse({'error': 'Invalid company code format'}, status=400)

                # Validate that the company exists and user has access to it
                user_company_code = request.session.get('cmpny')

                # Check if it's user's own company or a company under user's company
                valid_company = False

                if company_code == user_company_code:
                    valid_company = True
                else:
                    # Check if it's a company under user's company
                    try:
                        company = Company.objects.get(company_code=company_code, under=user_company_code)
                        valid_company = True
                    except Company.DoesNotExist:
                        pass

                if not valid_company:
                    return JsonResponse({'error': 'Invalid company access'}, status=403)

                request.session['selected_company'] = company_code
                return JsonResponse({'success': True, 'company_code': company_code})
            else:
                return JsonResponse({'error': 'Company code is required'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"Error setting selected company: {e}")
            return JsonResponse({'error': 'Failed to set selected company'}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

def get_transaction_data(request):
    """Get transaction data for the selected company or user's company - Enhanced with Current Date Support and Liquidity"""
    if 'lid' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    # Get the company to filter data for
    selected_company = request.session.get('selected_company')
    user_company = request.session.get('cmpny')
    selected_date = request.GET.get('date')

    # If no date is provided, use current date
    if not selected_date:
        selected_date = date.today().strftime('%Y-%m-%d')
        print(f"DEBUG: No date provided, using current date: {selected_date}")

    # Debug logging
    print(f"DEBUG: selected_company = {selected_company}")
    print(f"DEBUG: user_company = {user_company}")
    print(f"DEBUG: selected_date = {selected_date}")

    # Use selected company if available, otherwise use user's company
    filter_company = selected_company if selected_company else user_company

    if not filter_company:
        return JsonResponse({'error': 'No company selected'}, status=400)

    try:
        # Ensure filter_company is an integer
        if isinstance(filter_company, str):
            try:
                filter_company = int(filter_company)
            except ValueError:
                return JsonResponse({'error': 'Invalid company code'}, status=400)

        print(f"DEBUG: filter_company = {filter_company}")

        # Validate company access
        user_company_code = request.session.get('cmpny')
        if filter_company != user_company_code:
            try:
                Company.objects.get(company_code=filter_company, under=user_company_code)
            except Company.DoesNotExist:
                return JsonResponse({'error': 'Access denied to this company'}, status=403)

        # Base query for transactions filtered by company
        base_query = Transaction.objects.filter(company_code__company_code=filter_company)

        # DEBUG: Check total transactions before date filter
        total_transactions = base_query.count()
        print(f"DEBUG: Total transactions for company {filter_company}: {total_transactions}")

        # Apply date filter - ALWAYS apply date filter now
        try:
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
            print(f"DEBUG: Applying date filter for: {date_obj}")
            base_query = base_query.filter(trans_date=date_obj)
            filtered_count = base_query.count()
            print(f"DEBUG: Filtered by date {date_obj}: {filtered_count} transactions")

            if filtered_count == 0:
                print(f"DEBUG: No transactions found for date {date_obj}")
                # Let's check what dates do exist
                all_dates = Transaction.objects.filter(
                    company_code__company_code=filter_company
                ).values_list('trans_date', flat=True).distinct().order_by('-trans_date')[:10]
                print(f"DEBUG: Available dates: {list(all_dates)}")

        except ValueError as ve:
            print(f"DEBUG: Date parsing error: {ve}")
            return JsonResponse({'error': 'Invalid date format'}, status=400)

        # DEBUG: Print some sample transactions
        sample_transactions = base_query[:5]
        for i, trans in enumerate(sample_transactions):
            print(f"DEBUG Transaction {i+1}:")
            print(f"  - ID: {trans.trans_id}")
            print(f"  - Amount: {trans.amount}")
            print(f"  - Trans Type: {trans.trans_type}")
            print(f"  - Date: {trans.trans_date}")

            # Handle typeCode debugging
            if hasattr(trans, 'typeCode') and trans.typeCode:
                if hasattr(trans.typeCode, 'typeCode'):
                    print(f"  - TypeCode (FK): {trans.typeCode.typeCode}")
                    print(f"  - TypeCode Category: {getattr(trans.typeCode, 'category', 'N/A')}")
                else:
                    print(f"  - TypeCode (direct): {trans.typeCode}")
            elif hasattr(trans, 'typeCode_id') and trans.typeCode_id:
                print(f"  - TypeCode_id: {trans.typeCode_id}")
            else:
                print(f"  - TypeCode: None")

        # Initialize data structures
        sales_data = {}
        purchase_data = {}
        payments_data = {}
        receipts_data = {}
        liquidity_data = {}  # NEW: Liquidity data structure

        # Transaction type mapping - EXCLUDE NETSALES (4)
        trans_type_mapping = {
            0: 'default',  # Include trans_type 0 as default (though receipts/payments will use specific mapping)
            1: 'cash',
            2: 'card',
            3: 'credit',
            5: 'online'
        }

        # Add 'bank' to available transaction types since receipts/payments use it
        available_trans_types = list(trans_type_mapping.values()) + ['bank']

        # Get ItemGroups for categorization
        sales_item_groups = {}
        purchase_item_groups = {}
        payments_item_groups = {}
        receipts_item_groups = {}
        liquidity_item_groups = {}  # NEW: Liquidity item groups

        try:
            # Get all ItemGroups for this company
            item_groups = ItemGroups.objects.filter(company_code__company_code=filter_company)
            print(f"DEBUG: Found {item_groups.count()} ItemGroups for company {filter_company}")

            for group in item_groups:
                print(
                    f"DEBUG ItemGroup: typeCode={group.typeCode}, category={group.category}, description={group.description}")

                if group.category == 2:  # Sales items
                    sales_item_groups[group.typeCode] = group.description
                    sales_data[group.typeCode] = {trans_type: 0 for trans_type in available_trans_types}
                elif group.typeCode == 11:  # Purchase
                    purchase_item_groups[group.typeCode] = group.description
                elif group.typeCode in [36, 38]:  # Payments
                    payments_item_groups[group.typeCode] = group.description
                elif group.typeCode in [35, 37]:  # Receipts
                    receipts_item_groups[group.typeCode] = group.description
                elif group.typeCode in [150, 151]:  # NEW: Liquidity
                    liquidity_item_groups[group.typeCode] = group.description

        except Exception as e:
            print(f"ERROR loading ItemGroups: {e}")

        # Initialize purchase data with transaction types (including 'bank')
        purchase_data = {trans_type: 0 for trans_type in available_trans_types}

        # Initialize other data structures (including 'bank')
        payments_data = {trans_type: 0 for trans_type in available_trans_types}
        receipts_data = {trans_type: 0 for trans_type in available_trans_types}
        liquidity_data = {'cash': 0, 'bank': 0}  # NEW: Initialize liquidity with cash and bank

        # Process each transaction
        processed_count = 0
        for transaction in base_query:
            processed_count += 1

            # Skip netsales transactions (trans_type = 4)
            if transaction.trans_type == 4:
                print(f"DEBUG: Skipping netsales transaction {transaction.trans_id}")
                continue

            # Get typeCode - handle both direct integer and ForeignKey cases
            typecode = None
            if hasattr(transaction, 'typeCode') and transaction.typeCode:
                if hasattr(transaction.typeCode, 'typeCode'):
                    typecode = transaction.typeCode.typeCode
                else:
                    typecode = transaction.typeCode
            elif hasattr(transaction, 'typeCode_id') and transaction.typeCode_id:
                typecode = transaction.typeCode_id

            trans_type = transaction.trans_type
            amount = float(transaction.amount) if transaction.amount else 0

            # Special handling for receipts/payments (typeCodes 35,36,37,38) - they use trans_type=0
            if typecode in [35, 36, 37, 38]:
                # Map specific typeCode to specific transaction type name
                typecode_mapping = {
                    35: 'cash',      # Cash Receipt
                    36: 'card',      # Card Payment
                    37: 'bank',      # Bank Receipt
                    38: 'bank'       # Bank Payment
                }
                trans_type_name = typecode_mapping[typecode]
                print(f"DEBUG: Receipt/Payment transaction - TypeCode: {typecode}, using '{trans_type_name}' trans_type")
            # NEW: Special handling for liquidity (typeCodes 150, 151)
            elif typecode in [150, 151]:
                # Map liquidity typeCode to transaction type name
                liquidity_mapping = {
                    150: 'cash',     # Cash Liquidity
                    151: 'bank'      # Bank Liquidity
                }
                trans_type_name = liquidity_mapping[typecode]
                print(f"DEBUG: Liquidity transaction - TypeCode: {typecode}, using '{trans_type_name}' trans_type")
            else:
                trans_type_name = trans_type_mapping.get(trans_type)
                # Skip if transaction type is not in our mapping (excludes netsales)
                if trans_type_name is None:
                    print(f"DEBUG: Skipping transaction with unmapped trans_type: {trans_type}")
                    continue

            # DEBUG: Log first few transactions processing
            if processed_count <= 5:
                print(f"DEBUG Processing Transaction {processed_count}:")
                print(f"  - TypeCode: {typecode}")
                print(f"  - Trans Type: {trans_type} -> {trans_type_name}")
                print(f"  - Amount: {amount}")

            # Enhanced categorization logic
            if typecode == 11:  # Purchase - NOW CATEGORIZED BY TRANS_TYPE
                purchase_data[trans_type_name] += amount
                print(f"DEBUG: Added {amount} to purchase_{trans_type_name}")

            elif typecode in [36, 38]:  # Payments (Card=36, Bank=38)
                payments_data[trans_type_name] += amount
                print(f"DEBUG: Added {amount} to payments_{trans_type_name} (TypeCode: {typecode})")

            elif typecode in [35, 37]:  # Receipts (Cash=35, Bank=37)
                receipts_data[trans_type_name] += amount
                print(f"DEBUG: Added {amount} to receipts_{trans_type_name} (TypeCode: {typecode})")

            # NEW: Handle liquidity transactions
            elif typecode in [150, 151]:  # Liquidity (Cash=150, Bank=151)
                liquidity_data[trans_type_name] += amount
                print(f"DEBUG: Added {amount} to liquidity_{trans_type_name} (TypeCode: {typecode})")

            else:
                # Check if it's a sales transaction (category=2)
                if typecode and typecode in sales_item_groups:
                    if typecode not in sales_data:
                        sales_data[typecode] = {trans_type: 0 for trans_type in available_trans_types}
                    sales_data[typecode][trans_type_name] += amount
                    print(f"DEBUG: Added {amount} to sales[{typecode}][{trans_type_name}]")
                elif transaction.typeCode and hasattr(transaction.typeCode, 'category'):
                    if transaction.typeCode.category == 2:
                        if typecode not in sales_data:
                            sales_data[typecode] = {trans_type: 0 for trans_type in available_trans_types}
                        sales_data[typecode][trans_type_name] += amount
                        print(f"DEBUG: Added {amount} to sales[{typecode}][{trans_type_name}] via FK")
                else:
                    # Log unhandled transactions for debugging
                    print(f"DEBUG: Unhandled transaction - TypeCode: {typecode}, Trans_Type: {trans_type}, Amount: {amount}")

        print(f"DEBUG: Processed {processed_count} transactions")
        print(f"DEBUG: Raw sales_data: {sales_data}")
        print(f"DEBUG: Raw purchase_data: {purchase_data}")
        print(f"DEBUG: Raw payments_data: {payments_data}")
        print(f"DEBUG: Raw receipts_data: {receipts_data}")
        print(f"DEBUG: Raw liquidity_data: {liquidity_data}")  # NEW: Debug liquidity data

        # Filter out categories with no data
        filtered_sales_data = {}
        filtered_sales_item_groups = {}
        for typecode, transactions in sales_data.items():
            if any(amount > 0 for amount in transactions.values()):
                filtered_transactions = {trans_type: amount for trans_type, amount in transactions.items() if
                                         amount > 0}
                if filtered_transactions:
                    filtered_sales_data[typecode] = filtered_transactions
                    if typecode in sales_item_groups:
                        filtered_sales_item_groups[typecode] = sales_item_groups[typecode]

        # Filter other categories
        filtered_purchase = {k: v for k, v in purchase_data.items() if v > 0}
        filtered_payments = {k: v for k, v in payments_data.items() if v > 0}
        filtered_receipts = {k: v for k, v in receipts_data.items() if v > 0}
        filtered_liquidity = {k: v for k, v in liquidity_data.items() if v > 0}  # NEW: Filter liquidity

        print(f"DEBUG: Filtered sales_data: {filtered_sales_data}")
        print(f"DEBUG: Filtered purchase_data: {filtered_purchase}")
        print(f"DEBUG: Filtered payments_data: {filtered_payments}")
        print(f"DEBUG: Filtered receipts_data: {filtered_receipts}")
        print(f"DEBUG: Filtered liquidity_data: {filtered_liquidity}")  # NEW: Debug filtered liquidity

        # Create descriptions for sales
        sales_descriptions = {}
        for typecode, transactions in filtered_sales_data.items():
            category_name = sales_item_groups.get(typecode, f'Sales Type {typecode}')
            sales_descriptions[typecode] = {}
            for trans_type in transactions.keys():
                sales_descriptions[typecode][trans_type] = f"{category_name} ({trans_type.title()})"

        # Create descriptions for other categories
        purchase_descriptions = {}
        payments_descriptions = {}
        receipts_descriptions = {}
        liquidity_descriptions = {}  # NEW: Liquidity descriptions

        for trans_type_name in available_trans_types:
            if trans_type_name in filtered_purchase:
                purchase_descriptions[trans_type_name] = f"Purchase ({trans_type_name.title()})"
            if trans_type_name in filtered_payments:
                payments_descriptions[trans_type_name] = f"Payment ({trans_type_name.title()})"
            if trans_type_name in filtered_receipts:
                receipts_descriptions[trans_type_name] = f"Receipt ({trans_type_name.title()})"

        # NEW: Create liquidity descriptions
        for liquidity_type in ['cash', 'bank']:
            if liquidity_type in filtered_liquidity:
                liquidity_descriptions[liquidity_type] = f"Liquidity ({liquidity_type.title()})"

        # Prepare response data
        response_data = {
            'sales': filtered_sales_data,
            'purchase': filtered_purchase,
            'payments': filtered_payments,
            'receipts': filtered_receipts,
            'liquidity': filtered_liquidity,  # NEW: Include liquidity in response
            'descriptions': {
                'sales': sales_descriptions,
                'purchase': purchase_descriptions,
                'payments': payments_descriptions,
                'receipts': receipts_descriptions,
                'liquidity': liquidity_descriptions  # NEW: Include liquidity descriptions
            },
            'item_groups': {
                'sales': filtered_sales_item_groups,
                'purchase': purchase_item_groups,
                'payments': payments_item_groups,
                'receipts': receipts_item_groups,
                'liquidity': liquidity_item_groups  # NEW: Include liquidity item groups
            },
            'transaction_types': available_trans_types,
            # DEBUG INFO
            'debug_info': {
                'total_transactions': total_transactions,
                'processed_transactions': processed_count,
                'filter_company': filter_company,
                'selected_date': selected_date,
                'item_groups_count': item_groups.count() if 'item_groups' in locals() else 0
            }
        }

        return JsonResponse({
            'success': True,
            'data': response_data,
            'company_code': filter_company,
            'date_filtered': selected_date if selected_date else 'all'
        })

    except Exception as e:
        print(f"ERROR getting transaction data: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Failed to get transaction data: {str(e)}'}, status=500)



def get_companies_json(request):
    """Get companies data as JSON for dropdown population"""
    if 'lid' not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    # Get the logged-in user's company code
    user_company_code = request.session.get('cmpny')

    if not user_company_code:
        return JsonResponse({'companies': [], 'user_company': None})

    try:
        # Ensure user_company_code is integer
        if isinstance(user_company_code, str):
            try:
                user_company_code = int(user_company_code)
            except ValueError:
                return JsonResponse({'error': 'Invalid user company code'}, status=400)

        # Check if company info is already in session
        company_info = request.session.get('company_info')

        if company_info:
            # Use company info from session
            user_company_data = company_info
        else:
            # Fetch user's company details from database
            try:
                user_company = Company.objects.get(company_code=user_company_code)
                user_company_data = {
                    'company_code': user_company.company_code,
                    'name': user_company.name,
                    'under': user_company.under
                }
                # Store in session for future use
                request.session['company_info'] = user_company_data
            except Company.DoesNotExist:
                return JsonResponse({
                    'companies': [],
                    'user_company': None,
                    'error': 'User company not found'
                })

        # Get companies under the user's company
        companies_under = Company.objects.filter(under=user_company_code).values(
            'company_code', 'name', 'under'
        )

        companies_list = list(companies_under)

        return JsonResponse({
            'companies': companies_list,
            'user_company': user_company_data,
            'total_companies': len(companies_list)
        })

    except Exception as e:
        print(f"Error getting companies: {e}")
        return JsonResponse({
            'companies': [],
            'user_company': None,
            'error': 'Failed to get companies data'
        }, status=500)