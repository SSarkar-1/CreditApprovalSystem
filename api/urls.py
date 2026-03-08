from django.urls import path
from .views import (
    RegisterView, CheckEligibilityView,
    CreateLoanView, ViewLoanView, ViewLoansView
)

urlpatterns = [
    path('register', RegisterView.as_view()),
    path('check-eligibility', CheckEligibilityView.as_view()),
    path('create-loan', CreateLoanView.as_view()),
    path('view-loan/<int:loan_id>', ViewLoanView.as_view()),
    path('view-loans/<int:customer_id>', ViewLoansView.as_view()),
]