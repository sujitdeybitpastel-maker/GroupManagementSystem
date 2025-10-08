# models.py
from django.db import models
from django.db.models import JSONField

class Group(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    platform = models.CharField(max_length=255)
    group_type = models.CharField(max_length=255)
    status = models.IntegerField(default=1)  # 1=active, 0=inactive, 5=deleted
    added_time = models.DateTimeField(auto_now_add=True)
    last_updated_time = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = 'dashboard_app_group' 

    def __str__(self):
        return self.name

class Member(models.Model):
    id = models.IntegerField(primary_key=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    username = models.CharField(max_length=255)
    platforms = JSONField() # Change the data filed use JSONB
    last_updated_time = models.DateTimeField(auto_now=True)
    added_time = models.DateTimeField(auto_now_add=True)
    status = models.IntegerField(default=1)  # 1=active, 0=inactive, 5=deleted

    class Meta:
        db_table = 'dashboard_app_members'

    def __str__(self):
        return self.username

class GroupMemberships(models.Model):
    id = models.AutoField(primary_key=True)  # auto increment ID
    group = models.ForeignKey('Group', on_delete=models.CASCADE)   # FK to Group
    member = models.ForeignKey('Member', on_delete=models.CASCADE) # FK to Member
    is_admin = models.BooleanField(default=False)  # true/false flag
    last_updated_time = models.DateTimeField(auto_now=True)
    added_time = models.DateTimeField(auto_now_add=False)
    status = models.IntegerField(default=1)  # 1=active, 0=inactive, 5=deleted

    class Meta:
        db_table = 'dashboard_app_group_memberships'

    def __str__(self):
        return f"{self.member.full_name} in {self.group.name}"

class Message(models.Model):
    id = models.AutoField(primary_key=True)  
    group = models.ForeignKey('Group', on_delete=models.CASCADE)  
    sender = models.ForeignKey('Member', on_delete=models.CASCADE) 
    has_media = models.BooleanField(default=False)
    last_updated_time = models.DateTimeField(auto_now=True)
    added_time = models.DateTimeField(auto_now_add=False)
    status = models.IntegerField(default=1) 
    text_body = models.TextField()
    media_url = models.CharField(max_length=255)

    class Meta:
        db_table = 'dashboard_app_messages'

    def __str__(self):
        return f"{self.sender.full_name} in {self.group.name}"
