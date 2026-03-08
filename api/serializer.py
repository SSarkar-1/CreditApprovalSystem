from rest_framework import serializers
from .models import Loan,Customer

class CustomerSerealizer(serializers.ModelSerializer):
    class Meta:
        model=Customer
        fields='__all__'

class LoanSerealizer(serializers.ModelSerializer):
    class Meta:
        model=Loan
        fields='__all__'
