from django.db import models



# Create your models here.
class Customer(models.Model):
    customer_id=models.AutoField(primary_key=True)
    first_name=models.CharField(max_length=255)
    last_name=models.CharField(max_length=255)
    age=models.IntegerField(null=True)
    phone_number=models.BigIntegerField()
    monthly_salary=models.IntegerField()
    approved_limit=models.IntegerField()

def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Loan(models.Model):
    loan_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    loan_amount = models.FloatField()
    tenure = models.IntegerField()        # in months
    interest_rate = models.FloatField()
    monthly_repayment = models.FloatField()
    emis_paid_on_time = models.IntegerField(default=0)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
def __str__(self):
        return f"Loan {self.loan_id} - Customer {self.customer_id}"