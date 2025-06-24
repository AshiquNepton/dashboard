from django.db import models


class Company(models.Model):
    company_code = models.IntegerField(primary_key=True)
    under = models.IntegerField(default=0)
    name = models.CharField(max_length=50)
    reg_date = models.DateField()
    expiry_date = models.DateField()
    contact_person = models.CharField(max_length=50)
    mobile = models.CharField(max_length=15)  # Changed to CharField for better phone number handling
    email = models.CharField(max_length=50)
    authentication=models.CharField(max_length=20,unique=True)

class ItemGroups(models.Model):
    group_id = models.IntegerField( primary_key=True)
    description = models.CharField(max_length=30)
    category = models.IntegerField()
    date = models.DateField()
    narration = models.CharField(max_length=100)
    company_code = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    typeCode = models.IntegerField(null=True, blank=True)


class Transaction(models.Model):
    trans_id = models.IntegerField(primary_key=True)
    trans_date = models.DateField()
    company_code = models.ForeignKey(Company, on_delete=models.CASCADE)
    typeCode = models.IntegerField()
    amount = models.FloatField()
    narration = models.CharField(max_length=100)
    count = models.IntegerField()
    trans_type=models.IntegerField()


