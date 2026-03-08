from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection, IntegrityError, transaction
from .models import Customer, Loan
from datetime import date


def _sync_customer_sequence():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('api_customer', 'customer_id'),
                COALESCE((SELECT MAX(customer_id) FROM api_customer), 0) + 1,
                false
            )
            """
        )


# 1. /register
class RegisterView(APIView):
    def post(self, request):
        data = request.data
        monthly_income = data.get('monthly_income')
        approved_limit = round((36 * monthly_income) / 100000) * 100000
        try:
            with transaction.atomic():
                customer = Customer.objects.create(
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    age=data['age'],
                    monthly_salary=monthly_income,
                    phone_number=data['phone_number'],
                    approved_limit=approved_limit,
                )
        except IntegrityError:
            # If sequence drifted due to manual/seeded IDs, repair and retry once.
            _sync_customer_sequence()
            with transaction.atomic():
                customer = Customer.objects.create(
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    age=data['age'],
                    monthly_salary=monthly_income,
                    phone_number=data['phone_number'],
                    approved_limit=approved_limit,
                )
        return Response({
            'customer_id': customer.customer_id,
            'name': f"{customer.first_name} {customer.last_name}",
            'age': customer.age,
            'monthly_income': customer.monthly_salary,
            'approved_limit': customer.approved_limit,
            'phone_number': customer.phone_number,
        }, status=status.HTTP_201_CREATED)


# 2. /check-eligibility
class CheckEligibilityView(APIView):
    def post(self, request):
        data = request.data
        customer_id = data.get('customer_id')
        loan_amount = data.get('loan_amount')
        interest_rate = data.get('interest_rate')
        tenure = data.get('tenure')

        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=404)

        credit_score = calculate_credit_score(customer)
        approved, corrected_rate = check_approval(credit_score, interest_rate, customer)

        monthly_installment = calculate_emi(loan_amount, corrected_rate, tenure)

        return Response({
            'customer_id': customer_id,
            'approval': approved,
            'interest_rate': interest_rate,
            'corrected_interest_rate': corrected_rate,
            'tenure': tenure,
            'monthly_installment': monthly_installment,
        })


# 3. /create-loan
class CreateLoanView(APIView):
    def post(self, request):
        data = request.data
        customer_id = data.get('customer_id')
        loan_amount = data.get('loan_amount')
        interest_rate = data.get('interest_rate')
        tenure = data.get('tenure')

        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=404)

        credit_score = calculate_credit_score(customer)
        approved, corrected_rate = check_approval(credit_score, interest_rate, customer)
        monthly_installment = calculate_emi(loan_amount, corrected_rate, tenure)

        if not approved:
            return Response({
                'loan_id': None,
                'customer_id': customer_id,
                'loan_approved': False,
                'message': 'Loan not approved based on credit score',
                'monthly_installment': None,
            })

        loan = Loan.objects.create(
            customer=customer,
            loan_amount=loan_amount,
            interest_rate=corrected_rate,
            tenure=tenure,
            monthly_repayment=monthly_installment,
            start_date=date.today(),
        )
        return Response({
            'loan_id': loan.loan_id,
            'customer_id': customer_id,
            'loan_approved': True,
            'message': 'Loan approved',
            'monthly_installment': monthly_installment,
        })


# 4. /view-loan/<loan_id>
class ViewLoanView(APIView):
    def get(self, request, loan_id):
        try:
            loan = Loan.objects.get(loan_id=loan_id)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=404)

        customer = loan.customer
        return Response({
            'loan_id': loan.loan_id,
            'customer': {
                'id': customer.customer_id,
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'phone_number': customer.phone_number,
                'age': customer.age,
            },
            'loan_amount': loan.loan_amount,
            'interest_rate': loan.interest_rate,
            'monthly_installment': loan.monthly_repayment,
            'tenure': loan.tenure,
        })


# 5. /view-loans/<customer_id>
class ViewLoansView(APIView):
    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=404)

        loans = customer.loan_set.all()
        result = []
        for loan in loans:
            emis_left = loan.tenure - loan.emis_paid_on_time
            result.append({
                'loan_id': loan.loan_id,
                'loan_amount': loan.loan_amount,
                'interest_rate': loan.interest_rate,
                'monthly_installment': loan.monthly_repayment,
                'repayments_left': emis_left,
            })
        return Response(result)


# --- Helper Functions ---

def calculate_credit_score(customer):
    loans = customer.loan_set.all()
    if not loans.exists():
        return 50

    # Check if current debt > approved limit
    current_debt = sum(
        l.loan_amount for l in loans
        if l.end_date and l.end_date >= date.today()
    )
    if current_debt > customer.approved_limit:
        return 0

    total_emis = sum(l.tenure for l in loans)
    paid_on_time = sum(l.emis_paid_on_time for l in loans)
    on_time_ratio = paid_on_time / total_emis if total_emis else 0

    num_loans = loans.count()

    current_year = date.today().year
    active_this_year = loans.filter(start_date__year=current_year).count()

    total_volume = sum(l.loan_amount for l in loans)

    score = (
        on_time_ratio * 40 +
        min(num_loans, 5) * 2 +
        min(active_this_year, 3) * 5 +
        min(total_volume / 100000, 1) * 35
    )
    return min(int(score), 100)


def check_approval(credit_score, interest_rate, customer):
    # Check EMI burden
    active_loans = customer.loan_set.filter(end_date__gte=date.today())
    total_emis = sum(l.monthly_repayment for l in active_loans)
    if total_emis > 0.5 * customer.monthly_salary:
        return False, interest_rate

    if credit_score > 50:
        return True, interest_rate
    elif credit_score > 30:
        if interest_rate < 12:
            return True, 12.0
        return True, interest_rate
    elif credit_score > 10:
        if interest_rate < 16:
            return True, 16.0
        return True, interest_rate
    else:
        return False, interest_rate


def calculate_emi(loan_amount, annual_rate, tenure):
    # Compound interest EMI formula
    monthly_rate = annual_rate / (12 * 100)
    if monthly_rate == 0:
        return loan_amount / tenure
    emi = loan_amount * monthly_rate * (1 + monthly_rate)**tenure / ((1 + monthly_rate)**tenure - 1)
    return round(emi, 2)
