from django.shortcuts import render
from django.http import HttpResponse
from .models import Group, Member,GroupMemberships,Message
from django.utils import timezone
from django.db import connection
from django.contrib import messages
from django.db import models
from django.contrib import auth
from django.contrib.auth.decorators import login_required
import json
from django.core.paginator import Paginator
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q
import re
import ast
from collections import defaultdict
import os
from django.conf import settings

# Create your views here.
def index(request):
    if not request.session.get('member_id'):
        return redirect('login')

    # Count where status != 5
    group_count = Group.objects.exclude(status=5).count()
    user_count = Member.objects.exclude(status=5).count()
    message_count = Message.objects.exclude(status=5).count()
    active_user_count = Member.objects.filter(status=1).count()


    contexts = {
        'group_count': group_count,
        'user_count': user_count,
        'message_count': message_count,
        'active_user_count': active_user_count,
        }

        #print("------------------------------------",contexts)
    return render(request, 'index.html', contexts)
# Django ORM is not added here
def show_groups(request):
    if not request.session.get('member_id'):
        return redirect('login')
    query = request.GET.get('group_search', '')
    with connection.cursor() as cursor:
        if query:
            cursor.execute("SELECT id, name, platform, group_type, added_time, status FROM dashboard_app_group WHERE name ILIKE %s AND status != 5", [f'%{query}%'])
            rows = cursor.fetchall()
        else:
            cursor.execute("SELECT id, name, platform, group_type, added_time, status FROM dashboard_app_group where status != 5")
            rows = cursor.fetchall()

    groups = [
        {
            "id": row[0],
            "name": row[1],
            "platform": row[2],
            "group_type": row[3],
            "added_time": row[4],
            "status": row[5],
        }
        for row in rows
    ]
    groups = sorted(groups, key=lambda x: x['id'], reverse=True)
    # Implement pagination
    paginator = Paginator(groups, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    #print("-----------page_number----------", page_number)
    #print("-----------groups----------", groups)
    print("-----------page_obj----------", page_obj)
    return render(request, 'show_groups.html', {'page_obj': page_obj})


def add_group_form(request):
    if not request.session.get('member_id'):
        return redirect('login')
    if request.method == 'POST':
        name = request.POST.get('name')
        platform = request.POST.get('platform')
        group_type = request.POST.get('group_type')

        group_type_validate = ["Group", "Channel","Broadcast"]
        platform_validation = ["WhatsApp","Telegram","Facebook","Instagram","Twitter","LinkedIn","YouTube","Snapchat","Pinterest","Reddit","Discord","Slack","WeChat","Line"]
        if not name or not platform or not group_type:
            messages.warning(request,"Please enter the details")
            return redirect('add_group')
        if group_type not in group_type_validate or platform not in platform_validation :
            messages.warning(request,"Please enter the correct value")
            return redirect('add_group')
        
        # Check if a group with same name/platform/type exists and is not deleted
        existing_group = Group.objects.filter(
            name=name,
            platform=platform,
            group_type=group_type
        ).exclude(status=5).first()

        print("------------------------",name,platform,group_type)

        if existing_group:
            messages.warning(
                request,
                f"Group with the same name '{name}', platform '{platform}', and group type '{group_type}' already exists."
            )
            return redirect('add_group')

        # Get the max id from existing groups
        last_id = Group.objects.aggregate(max_id=models.Max('id'))['max_id'] or 0
        new_id = last_id + 1

        # Create new group with custom id
        Group.objects.create(
            id=new_id,
            name=name,
            platform=platform,
            group_type=group_type,
            status=1  # active by default
        )

        messages.success(request, f"{name} Group created successfully.")
        return redirect('data_table_group')

    return HttpResponse("Invalid request method.")


def add_group(request):
    if not request.session.get('member_id'):
        return redirect('login')
    return render(request, 'add_group.html')


def delete_group(request, group_id):
    if not request.session.get('member_id'):
        return redirect('login')
    group = get_object_or_404(Group, id=group_id)
    group.status = 5
    group.save()
        
    messages.warning(request, f"{group.name}'s account deleted successfully.")
    return redirect('data_table_group')

#  Django ORM is not added here
def edit_group(request, group_id): # Fetch group details and render edit form
    if not request.session.get('member_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, name, platform, group_type FROM dashboard_app_group WHERE id = %s", [group_id])
        row = cursor.fetchone()
        if row:
            group = {
                "name": row[1],
                "platform": row[2],
                "group_type": row[3]
            }
            return render(request, 'edit_group.html', {'group': group, 'group_id': group_id})
        else:
            return HttpResponse("Group not found.")
#Add some logic to update the group details // Django ORM is not added here
def update_group(request, group_id):
    if not request.session.get('member_id'):
        return redirect('login')

    if request.method == 'POST':
        name = request.POST.get('name')
        platform = request.POST.get('platform')
        group_type = request.POST.get('group_type')
        last_updated = timezone.now()

        group_type_validate = ["Group", "Channel","Broadcast"]
        platform_validation = ["WhatsApp","Telegram","Facebook","Instagram","Twitter","LinkedIn","YouTube","Snapchat","Pinterest","Reddit","Discord","Slack","WeChat","Line"]
        if not name or not platform or not group_type:
            messages.warning(request,"Please enter the details")
            return redirect('edit_group', group_id=group_id)
        if group_type not in group_type_validate or platform not in platform_validation :
            messages.warning(request,"Please enter the correct value")
            return redirect('edit_group',group_id=group_id)

        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM dashboard_app_group WHERE (name = %s and platform = %s  and group_type = %s) and status != 5", [name, platform, group_type])
            if cursor.fetchone()[0] > 0:
                messages.success(request, f"Group with the same name '{name}', same platfrom '{platform}' and same group type '{group_type}' already exists.")
                # Redirect the edit_group
                return redirect('edit_group', group_id=group_id)
            else:
                cursor.execute(
                    """
                    UPDATE dashboard_app_group
                    SET name = %s, platform = %s, group_type = %s, last_updated_time = %s
                    WHERE id = %s
                    """,
                    [name, platform, group_type, last_updated, group_id]
                )

                messages.success(request, f"{name} updated successfully.")

        groups_del = Group.objects.filter(
            platform = platform,
            group_type = group_type,
            status = 5
        ).values_list('id', flat=True)
        groups_add_upadate = Group.objects.filter(
            platform = platform,
            group_type = group_type,
        ).exclude(status=5).values_list('id', flat=True)

        print("----------groups--------------",groups_del)
        print("----------groups--------------",groups_add_upadate)

        return redirect('data_table_group')
    else:
        return HttpResponse("Invalid request method.")
 
def add_member_form(request):
    if not request.session.get('member_id'):
        return redirect('login')
    if request.method == 'POST':
        name = request.POST.get('name')
        phone_number = request.POST.get('phone')
        email = request.POST.get('email')
        username = request.POST.get('username')
        group_ids = request.POST.getlist('group_id[]')
        print("-----------group id details----------",group_ids)
        date_submitted = timezone.now()
        last_updated = timezone.now()
        status = 1  # default
        #print(type(name), type(phone), type(email), type(username), type(platforms), type(date_submitted), type(last_updated), type(status))

        # Add here one condition to check if username already exists in the table then it not insert and return error message
        


        #print(platform)
        # For group validation
        group_id_validation = [str(i) for i in Group.objects.exclude(status=5).values_list("id", flat=True)]
        for grid in group_ids:
            if grid not in group_id_validation:
                messages.warning(request, 'Invalid Group ID')
                return redirect('add_member')
        # For blank data insertion
        if not name or not phone_number or not email or not username or not group_ids:
            messages.warning(request,"Please enter the details")
            return redirect('add_member')
        
        if len(phone_number)!= 10:
            messages.warning(request, 'Invalid Phone No')
            return redirect('add_member')
        else:
            existing_member = Member.objects.filter(
                Q(username=username) | Q(phone_number=phone_number)  # OR condition
            ).exclude(status=5).first()

            if existing_member:
                if existing_member.username == username and existing_member.phone_number == phone_number:
                    messages.warning(request, f"User with username '{username}' and '{phone_number}' already exists.")
                elif existing_member.username == username:
                    messages.warning(request, f"User with username '{username}' already exists.")
                elif existing_member.phone_number == phone_number:
                    messages.warning(request, f"User with phone number '{phone_number}' already exists.")
                return redirect('add_member')

            else:
                
                groups = Group.objects.filter(id__in=group_ids)
                platform = [g.platform for g in groups]
                last_id = Member.objects.aggregate(max_id=models.Max('id'))['max_id'] or 0
                new_id = last_id + 1
                Member.objects.create(
                    id = new_id,
                    full_name = name,
                    phone_number = phone_number,
                    email = email,
                    username = username,
                    added_time = date_submitted,
                    last_updated_time = last_updated,
                    platforms = platform,
                    status = status
                    )
                last_id_gm = GroupMemberships.objects.aggregate(max_id=models.Max('id'))['max_id'] or 0
                for group_id in group_ids:
                    last_id_member = Member.objects.aggregate(max_id=models.Max('id'))['max_id'] or 0
                    last_id_gm += 1
                    group = Group.objects.get(id=group_id)
                    member = Member.objects.get(id=new_id)
                    GroupMemberships.objects.create(
                        id=last_id_gm,
                        group=group,
                        member=member,
                        is_admin=False,
                        added_time=date_submitted,
                        last_updated_time=last_updated,
                        status=status
                    )

                messages.success(request, f'{name} created successfully')
                return redirect('show_members')

    else:
        return HttpResponse("Invalid request method.")

def add_member(request):
    if not request.session.get('member_id'):
        return redirect('login')
    all_entries = Group.objects.exclude(status=5).values_list("id", "name", "platform", "group_type")
    group_id_validation = list(Group.objects.exclude(status=5).values_list("id", flat=True))
    group_id_validation = [str(i) for i in Group.objects.exclude(status=5).values_list("id", flat=True)]


    print("----group_id_validation-----",group_id_validation)

    groups = []
    for id, name, platform, group_type in all_entries:
        groups.append({
            "group_id": id,
            "combo": f"{name} - {platform} - {group_type}",
        })

    context = {
        "groups": groups
    }
    return render(request, "add_member.html", context)

def show_members(request):
    if not request.session.get('member_id'):
        return redirect('login')
    memberships = memberships = GroupMemberships.objects.select_related('member', 'group') \
    .exclude(status=5)


    # Collect all group names per member
    member_groups = defaultdict(list)
    for gm in memberships:
        if gm.group.status == 5:
            member_groups[gm.member.id].append("Group is deleted")
        else:
            member_groups[gm.member.id].append(gm.group.name)

    # Prepare final members list
    members = []
    for gm in memberships:
        member_id = gm.member.id
        if not any(m['id'] == member_id for m in members):
            members.append({
                "id": member_id,
                "full_name": gm.member.full_name,
                "phone_number": gm.member.phone_number,
                "status": gm.member.status,
                "platforms": member_groups[member_id]
            })

    print("---------members_for_ui---------", members)


    members = sorted(members, key=lambda x: x["id"], reverse=True)
    return render(request, "data_table_member.html", {"members": members})

def activate_member(request, member_id):
    if not request.session.get('member_id'):
        return redirect('login')
    member = get_object_or_404(Member, id=member_id)
    member.status = 1
    member.save()

    #GroupMemberships.objects.filter(member=member).update(status=1)

    messages.success(request, f"{member.full_name}'s account Active successfully.")
    return redirect('show_members')


def deactivate_member(request, member_id):
    if not request.session.get('member_id'):
        return redirect('login')
    member = get_object_or_404(Member, id=member_id)
    member.status = 0
    member.save()

    #GroupMemberships.objects.filter(member=member).update(status=0)

    messages.warning(request, f"{member.full_name}'s account Deactive successfully.")
    return redirect('show_members')


def delete_member(request, member_id):
    if not request.session.get('member_id'):
        return redirect('login')
    member = get_object_or_404(Member, id=member_id)
    member.status = 5
    member.save()

    #GroupMemberships.objects.filter(member=member).update(status=5)

    messages.warning(request, f"{member.full_name}'s account deleted successfully.")
    return redirect('show_members')


def edit_member(request, member_id):
    if not request.session.get('member_id'):
        return redirect('login')
    #print("-----------member_id----------", member_id)
    member = get_object_or_404(Member, id = member_id)
    member_groups = GroupMemberships.objects.filter(
        member_id=member_id
    ).exclude(status=5).values_list("group_id", flat=True)
    #print("------------------all--------------",member_groups)

    selected_groups_qs = Group.objects.filter(
        id__in=member_groups
    ).exclude(status=5).values_list("id", "name", "platform", "group_type")
    selected_groups = []
    for id, name, platform, group_type in selected_groups_qs:
        selected_groups.append({
            "group_id": id,
            "combo": f"{name} - {platform} - {group_type}"
        })

    #print("------selected_groups------", selected_groups)

    
    all_entries = Group.objects.exclude(status=5).values_list("id","name", "platform", "group_type")
    #print("------------------all--------------",all_entries)

    groups = []
    for id, name, platform, group_type in all_entries:
        #print(platform)
        groups.append({
            "group_id":id,
            'combo': f"{name} - {platform} - {group_type}",
            "selected": id in [g['group_id'] for g in selected_groups]
        })

    context = {
        'selected_groups':list(selected_groups),
        'groups': groups
    }
    #print("--------------group-----------------------",groups)
    
    #print("-----------context----------", context)
    return render(request, 'edit_member.html', {'member': member, 'member_id': member_id, "groups":groups})


def update_member(request, member_id):
    if not request.session.get('member_id'):
        return redirect('login')
    print("-----------member_id in update----------", member_id)
    
    if request.method == 'POST':
        member = get_object_or_404(Member, id=member_id)
        member_username = member.username
        member_phone = member.phone_number
        #print("--------From Member table-----------",member_username, member_phone)
        full_name = request.POST.get('full_name')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email')
        username = request.POST.get('username')
        selected_groups = [int(gid) for gid in request.POST.getlist("group_id[]")]
        print("-----------member details for Update----------",selected_groups)
        last_updated = timezone.now()

        existing_groups = list(GroupMemberships.objects.filter(
            member_id=member_id
        ).values_list("group_id", flat=True))
        #print("---------------Existing--------------------",existing_groups)
        groups = Group.objects.filter(id__in=selected_groups)
        platform = [g.platform for g in groups]

        #print("after post form UI",username, phone_number)

        existing_count_username = Member.objects.filter(
        username=username
        ).exclude(status=5).count()
        #print("-------------existing_count_username---------------", existing_count_username)
        existing_count_phone = Member.objects.filter(
        phone_number=phone_number
        ).exclude(status=5).count()
        #print("-------------existing_count_phone---------------", existing_count_phone)

        # Add validation Part here
        # For blank data insertion
        # fields = {
        #     "Name": full_name,
        #     "Phone Number": phone_number,
        #     "Email": email,
        #     "Username": username,
        #     "Group Selection": selected_groups,
        # }

        # for field_name, value in fields.items():
        #     if not value:
        #         messages.warning(request, f"Please enter {field_name}")
        #         return redirect('edit_member', member_id=member_id)

        missing_fields = []

        if not full_name:
            missing_fields.append("Full name")
        if not phone_number:
            missing_fields.append("Phone number")
        if not email:
            missing_fields.append("Email")
        if not username:
            missing_fields.append("Username")
        if not selected_groups:
            missing_fields.append("Group")

        if missing_fields:
            # Join all missing field names in one message
            message_text = "Please enter: " + ", ".join(missing_fields)
            messages.warning(request, message_text)
            return redirect('edit_member', member_id=member_id)

        
        # Group Id Insertions validations
        group_id_validation = list(Group.objects.exclude(status=5).values_list("id", flat=True))
        for grid in selected_groups:
            if grid not in group_id_validation:
                messages.warning(request, 'Invalid Group ID')
                return redirect('edit_member',member_id=member_id)


        # Phone Number check condition here
        if len(phone_number)!= 10:
            messages.warning(request, 'Invalid Phone No')
            return redirect('edit_member', member_id = member_id)
        else:
            if member_username == username and member_phone == phone_number:
                member.full_name = full_name
                member.phone_number = phone_number
                member.email = email
                member.username = username
                member.platforms = platform
                member.last_updated_time = last_updated
                member.save()
                
                member = Member.objects.get(id=member_id)
                added_status = 1
                removed_status = 5

                existing_groups = list(
                    GroupMemberships.objects.filter(member_id=member_id)
                                            .exclude(status=5)
                                            .values_list("group_id", flat=True)
                )
                # Remove memberships not selected
                to_remove = set(existing_groups) - set(selected_groups)  # [5]
                if to_remove:
                    GroupMemberships.objects.filter(
                        member_id=member_id,
                        group_id__in=to_remove
                    ).update(status=removed_status, last_updated_time=last_updated)
                last_id_gm = GroupMemberships.objects.aggregate(max_id=models.Max('id'))['max_id'] or 0
                # Add new memberships
                to_add = set(selected_groups) - set(existing_groups)  # [6]
                for group_id in to_add:
                    last_id_gm += 1
                    group = Group.objects.get(id=group_id)
                    GroupMemberships.objects.create(
                        id = last_id_gm,
                        group=group,
                        member=member,
                        is_admin=False,
                        added_time=member.added_time,
                        last_updated_time=last_updated,
                        status=added_status
                    )

                #Update last_updated_time for memberships that are kept
                to_keep = set(existing_groups) & set(selected_groups)  # [4]
                if to_keep:
                    GroupMemberships.objects.filter(
                        member_id=member_id,
                        group_id__in=to_keep,
                        status__lt=1  # only active memberships
                    ).update(last_updated_time=last_updated)

                memberships = GroupMemberships.objects.filter(member_id=member_id)
                group_counts = memberships.values('group_id').annotate(count=models.Count('id')).filter(count__gt=1)
                print('----------group_count-------------',group_counts)

                for g in group_counts:
                    group_id = g['group_id']
                    
                    # Get all memberships for this group, ordered by added_time
                    group_memberships = memberships.filter(group_id=group_id).order_by('last_updated_time')
                    
                    # Keep the earliest (first) one
                    memberships_to_keep = group_memberships.last()
                    
                    print('---------------memberships_to_keep-----------',memberships_to_keep)
                    # Delete all other duplicates
                    memberships_to_delete = group_memberships.exclude(id=memberships_to_keep.id)
                    memberships_to_delete.delete()
                                
                messages.success(request, f"{member.full_name}'s account Updated successfully.")
                return redirect('show_members')
            elif member_username==username and existing_count_phone==0:
                member.full_name = full_name
                member.phone_number = phone_number
                member.email = email
                member.username = username
                member.platforms = platform
                member.last_updated_time = last_updated
                member.save()

                member = Member.objects.get(id=member_id)
                added_status = 1
                removed_status = 5

                existing_groups = list(
                    GroupMemberships.objects.filter(member_id=member_id)
                                            .exclude(status=5)
                                            .values_list("group_id", flat=True)
                )
                # Remove memberships not selected
                to_remove = set(existing_groups) - set(selected_groups)  # [5]
                if to_remove:
                    GroupMemberships.objects.filter(
                        member_id=member_id,
                        group_id__in=to_remove
                    ).update(status=removed_status, last_updated_time=last_updated)
                last_id_gm = GroupMemberships.objects.aggregate(max_id=models.Max('id'))['max_id'] or 0
                # Add new memberships
                to_add = set(selected_groups) - set(existing_groups)  # [6]
                for group_id in to_add:
                    last_id_gm += 1
                    group = Group.objects.get(id=group_id)
                    GroupMemberships.objects.create(
                        id = last_id_gm,
                        group=group,
                        member=member,
                        is_admin=False,
                        added_time=member.added_time,
                        last_updated_time=last_updated,
                        status=added_status
                    )

                #Update last_updated_time for memberships that are kept
                to_keep = set(existing_groups) & set(selected_groups)  # [4]
                if to_keep:
                    GroupMemberships.objects.filter(
                        member_id=member_id,
                        group_id__in=to_keep,
                        status__lt=1  # only active memberships
                    ).update(last_updated_time=last_updated)

                memberships = GroupMemberships.objects.filter(member_id=member_id)
                group_counts = memberships.values('group_id').annotate(count=models.Count('id')).filter(count__gt=1)
                print('----------group_count-------------',group_counts)

                for g in group_counts:
                    group_id = g['group_id']
                    
                    # Get all memberships for this group, ordered by added_time
                    group_memberships = memberships.filter(group_id=group_id).order_by('last_updated_time')
                    
                    # Keep the earliest (first) one
                    memberships_to_keep = group_memberships.last()
                    
                    print('---------------memberships_to_keep-----------',memberships_to_keep)
                    # Delete all other duplicates
                    memberships_to_delete = group_memberships.exclude(id=memberships_to_keep.id)
                    memberships_to_delete.delete()
                                
                messages.success(request, f"{member.full_name}'s account Updated successfully.")
                return redirect('show_members')
            elif member_phone==phone_number and existing_count_username==0:
                member.full_name = full_name
                member.phone_number = phone_number
                member.email = email
                member.username = username
                member.platforms = platform
                member.last_updated_time = last_updated
                member.save()

                member = Member.objects.get(id=member_id)
                added_status = 1
                removed_status = 5

                existing_groups = list(
                    GroupMemberships.objects.filter(member_id=member_id)
                                            .exclude(status=5)
                                            .values_list("group_id", flat=True)
                )
                # Remove memberships not selected
                to_remove = set(existing_groups) - set(selected_groups)  # [5]
                if to_remove:
                    GroupMemberships.objects.filter(
                        member_id=member_id,
                        group_id__in=to_remove
                    ).update(status=removed_status, last_updated_time=last_updated)
                last_id_gm = GroupMemberships.objects.aggregate(max_id=models.Max('id'))['max_id'] or 0
                # Add new memberships
                to_add = set(selected_groups) - set(existing_groups)  # [6]
                for group_id in to_add:
                    last_id_gm += 1
                    group = Group.objects.get(id=group_id)
                    GroupMemberships.objects.create(
                        id = last_id_gm,
                        group=group,
                        member=member,
                        is_admin=False,
                        added_time=member.added_time,
                        last_updated_time=last_updated,
                        status=added_status
                    )

                #Update last_updated_time for memberships that are kept
                to_keep = set(existing_groups) & set(selected_groups)  # [4]
                if to_keep:
                    GroupMemberships.objects.filter(
                        member_id=member_id,
                        group_id__in=to_keep,
                        status__lt=1  # only active memberships
                    ).update(last_updated_time=last_updated)

                memberships = GroupMemberships.objects.filter(member_id=member_id)
                group_counts = memberships.values('group_id').annotate(count=models.Count('id')).filter(count__gt=1)
                print('----------group_count-------------',group_counts)

                for g in group_counts:
                    group_id = g['group_id']
                    
                    # Get all memberships for this group, ordered by added_time
                    group_memberships = memberships.filter(group_id=group_id).order_by('last_updated_time')
                    
                    # Keep the earliest (first) one
                    memberships_to_keep = group_memberships.last()
                    
                    print('---------------memberships_to_keep-----------',memberships_to_keep)
                    # Delete all other duplicates
                    memberships_to_delete = group_memberships.exclude(id=memberships_to_keep.id)
                    memberships_to_delete.delete()
                                
                messages.success(request, f"{member.full_name}'s account Updated successfully.")
                return redirect('show_members')
            elif existing_count_phone==0 and existing_count_username==0:
                member.full_name = full_name
                member.phone_number = phone_number
                member.email = email
                member.username = username
                member.platforms = platform
                member.last_updated_time = last_updated
                member.save()

                member = Member.objects.get(id=member_id)
                added_status = 1
                removed_status = 5

                existing_groups = list(
                    GroupMemberships.objects.filter(member_id=member_id)
                                            .exclude(status=5)
                                            .values_list("group_id", flat=True)
                )
                # Remove memberships not selected
                to_remove = set(existing_groups) - set(selected_groups)  # [5]
                if to_remove:
                    GroupMemberships.objects.filter(
                        member_id=member_id,
                        group_id__in=to_remove
                    ).update(status=removed_status, last_updated_time=last_updated)
                last_id_gm = GroupMemberships.objects.aggregate(max_id=models.Max('id'))['max_id'] or 0
                # Add new memberships
                to_add = set(selected_groups) - set(existing_groups)  # [6]
                for group_id in to_add:
                    last_id_gm += 1
                    group = Group.objects.get(id=group_id)
                    GroupMemberships.objects.create(
                        id = last_id_gm,
                        group=group,
                        member=member,
                        is_admin=False,
                        added_time=member.added_time,
                        last_updated_time=last_updated,
                        status=added_status
                    )

                #Update last_updated_time for memberships that are kept
                to_keep = set(existing_groups) & set(selected_groups)  # [4]
                if to_keep:
                    GroupMemberships.objects.filter(
                        member_id=member_id,
                        group_id__in=to_keep,
                        status__lt=1  # only active memberships
                    ).update(last_updated_time=last_updated)

                memberships = GroupMemberships.objects.filter(member_id=member_id)
                group_counts = memberships.values('group_id').annotate(count=models.Count('id')).filter(count__gt=1)
                print('----------group_count-------------',group_counts)

                for g in group_counts:
                    group_id = g['group_id']
                    
                    # Get all memberships for this group, ordered by added_time
                    group_memberships = memberships.filter(group_id=group_id).order_by('last_updated_time')
                    
                    # Keep the earliest (first) one
                    memberships_to_keep = group_memberships.last()
                    
                    print('---------------memberships_to_keep-----------',memberships_to_keep)
                    # Delete all other duplicates
                    memberships_to_delete = group_memberships.exclude(id=memberships_to_keep.id)
                    memberships_to_delete.delete()
                                
                messages.success(request, f"{member.full_name}'s account Updated successfully.")
                return redirect('show_members')
            
            elif member_username==username and existing_count_phone>=1:
                messages.warning(request, f"{phone_number}' is allready present")
                return redirect('edit_member', member_id=member_id)
            elif member_phone==phone_number and existing_count_username>=1:
                messages.warning(request, f"{username}' is allready present")
                return redirect('edit_member', member_id=member_id)
            else:
                messages.warning(request, f"USer name '{username}' and Phone Number '{phone_number}' is allready present")
                return redirect('edit_member', member_id=member_id)
    else:
        return HttpResponse("This page is not working............")


def show_messages(request):
    if not request.session.get('member_id'):
        return redirect('login')
    if not request.session.get('member_id'):
        return redirect('login')
    messages_1 = (
        Message.objects
        .select_related("group", "sender")  # performs LEFT JOINs efficiently
        .values(
            "id",
            "text_body",
            "status",
            "group__name",
            "group__platform",
            "sender__full_name",
            "sender__phone_number",
            "group__status",
        )
    )

    # Convert rows into a list of dicts for easy template rendering
    messages_final = [
        {
            "id": m["id"],
            "message": m["text_body"],
            "status": m["status"],
            "group_name": m["group__name"],
            "platform": m["group__platform"],
            "sender_name": m["sender__full_name"],
            "phone_number": m["sender__phone_number"],
            "group_status": m["group__status"]
        }
        for m in messages_1
    ]
    messages_final = sorted(messages_final, key=lambda x: x['id'], reverse=True)  # Sort by id in ascending order
    print("final Message-------------------",messages_final)
    return render(request, 'data_table_message.html' , {'messages_final': messages_final})


def add_message(request):
    if not request.session.get('member_id'):
        return redirect('login')
    all_entries = GroupMemberships.objects.exclude(group__status=5).select_related("group", "member")

    groups = defaultdict(list)
    for gm in all_entries:
        groups[gm.group.id].append({
            "id": gm.member.id,
            "name": gm.member.full_name
        })
    groups_json = json.dumps(groups)
    
    group_list = [
        {"id": gm.group.id, "name": gm.group.name}
        for gm in all_entries
    ]

    context = {
        "groups": list({g["id"]: g for g in group_list}.values()),  # unique groups
        "groups_by_members": groups_json
    }
    print("----------------------context------------", context)
    return render(request, "add_message.html", context)


def add_message_form(request):
    if not request.session.get('member_id'):
        return redirect('login')
    if request.method == 'POST':
        text_body = request.POST.get('message')
        group_id = request.POST.get('group_id')
        sender_id = request.POST.get('member_id')
        added_time = timezone.now()
        last_updated_time = timezone.now()
        status = 1

        # Multiple file uploads
        uploaded_files = request.FILES.getlist('upload')
        saved_files = []

        for f in uploaded_files:
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            full_path = os.path.join(upload_dir, f.name)
            with open(full_path, 'wb+') as dest:
                for chunk in f.chunks():
                    dest.write(chunk)

            # Save relative path instead of full path
            relative_path = os.path.relpath(full_path, settings.MEDIA_ROOT).replace("\\", "/")
            saved_files.append(relative_path)

        print(text_body, group_id, sender_id, added_time)

        if not text_body and not saved_files:
            messages.warning(request,"Please Add Message or Upload Media file")
            return redirect('add_message')

        last_id = Message.objects.aggregate(max_id=models.Max('id'))['max_id'] or 0
        new_id = last_id + 1
        Message.objects.create(
            id = new_id,
            text_body = text_body,
            has_media = False if len(saved_files) == 0 else True,
            media_url = saved_files,
            group_id = group_id,
            sender_id = sender_id,
            added_time = added_time,
            last_updated_time = last_updated_time,
            status = status
        )
        
        return redirect('show_messages')

    return HttpResponse("Invalid request method")


def deactivate_message(request, message_id):
    if not request.session.get('member_id'):
        return redirect('login')
    message_1 = get_object_or_404(Message, id=message_id)
    message_1.status = 0
    message_1.save()

    #GroupMemberships.objects.filter(member=member).update(status=1)

    messages.success(request, f"{message_1.id}'s account Active successfully.")
    return redirect('show_messages')


def activate_message(request, message_id):
    if not request.session.get('member_id'):
        return redirect('login')
    message_1 = get_object_or_404(Message, id=message_id)
    message_1.status = 1
    message_1.save()

    #GroupMemberships.objects.filter(member=member).update(status=1)

    messages.success(request, f"{message_1.id}'s account Active successfully.")
    return redirect('show_messages')


def delete_message(request, message_id):
    if not request.session.get('member_id'):
        return redirect('login')
    message_1 = get_object_or_404(Message, id=message_id)
    message_1.status = 5
    message_1.save()

    #GroupMemberships.objects.filter(member=member).update(status=1)

    messages.success(request, f" Message delete successfully.")
    return redirect('show_messages')


def edit_message(request, message_id):
    if not request.session.get('member_id'):
        return redirect('login')
    print("-----------message_id----------", message_id)
    message_1 = get_object_or_404(Message, id=message_id)
    print("-----------message url----------", message_1.media_url,message_1.group_id,message_1.sender_id )
    
    media_url_str = message_1.media_url
    media_urls = []

    try:
        # Safely convert string to Python list (if stored as string)
        media_list = ast.literal_eval(media_url_str) if media_url_str else []

        # Convert full paths to relative paths for MEDIA_URL
        for path in media_list:
            # Remove MEDIA_ROOT prefix and fix slashes
            # relative_path = os.path.relpath(path, settings.MEDIA_ROOT).replace("\\", "/")
            media_urls.append(path)

    except Exception as e:
        print("Error parsing media_url:", e)
        media_urls = []

    print("--------------urls", media_urls)

    return render(request, 'edit_message_1.html', {
        'message': message_1,
        'media_urls': media_urls,
        "message_id": message_id,
        'MEDIA_URL': settings.MEDIA_URL
    })

def update_message(request, message_id):
    if not request.session.get('member_id'):
        return redirect('login')
    print("-----------message_id in update----------", message_id)
    if request.method == 'POST':
        text_body = request.POST.get('text_body')
        media_url = request.POST.getlist('media_url[]')
        updated_time = timezone.now()
        print("---------------------",text_body,media_url)

        uploaded_files = request.FILES.getlist('upload')
        saved_files = []

        for f in uploaded_files:
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)

            full_path = os.path.join(upload_dir, f.name)
            with open(full_path, 'wb+') as dest:
                for chunk in f.chunks():
                    dest.write(chunk)

            # Save relative path instead of full path
            relative_path = os.path.relpath(full_path, settings.MEDIA_ROOT).replace("\\", "/")
            saved_files.append(relative_path)
        # Validate the message part for upload or text message
        if not text_body and not saved_files and not media_url:
            messages.warning(request,"Please Add Message or Upload Media file")
            return redirect('edit_message',message_id=message_id)
        message_1 = get_object_or_404(Message, id=message_id)
        message_1.text_body = text_body
        message_1.has_media = bool(saved_files or media_url)
        # Combine lists, keeping both existing and new files
        message_1.media_url = (media_url or []) + (saved_files or [])
        message_1.last_updated_time = updated_time
        message_1.save()

        messages.success(request, f"Message updated successfully.")
        return redirect('show_messages')
    return HttpResponse("Invalid request method.")

def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        phone_no = request.POST.get('phone_no')

        try:
            # Try to get an active user
            user = Member.objects.get(username=username, phone_number=phone_no, status=1)
            print(user.full_name)
        except Member.DoesNotExist:
            # Check if user exists but is deleted
            if Member.objects.filter(username=username, phone_number=phone_no, status=5).exists():
                messages.warning(request, "User is Deleted.")
                return redirect('login')
            # Check if user exists but is inactive
            elif Member.objects.filter(username=username, phone_number=phone_no, status=0).exists():
                messages.warning(request, "User is Inactive.")
                return redirect('login')
            else:
                # User does not exist at all
                messages.warning(request, "Invalid username or phone number.")
                return redirect('login')

            

        #Store session
        request.session['member_id'] = user.id
        request.session['username'] = user.username
        request.session['full_name'] = user.full_name
        request.session['phone_no'] = user.phone_number

        messages.success(request, f"Hi Welcome {user.full_name}!")
        return redirect('index')

    return render(request, 'login.html')
    

def logout(request):
    auth.logout(request)
    return render(request, 'login.html')

def show_data_table_group(request):
    if not request.session.get('member_id'):
        return redirect('login')
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, name, platform, group_type, added_time, status FROM dashboard_app_group where status != 5")
        rows = cursor.fetchall()

    groups = [
        {
            "id": row[0],
            "name": row[1],
            "platform": row[2],
            "group_type": row[3],
            "added_time": row[4],
            "status": row[5],
        }
        for row in rows
    ]
    #print("----------------------------", groups)
    groups = sorted(groups, key=lambda x: x['id'], reverse=True)
    #print("----------------------------", groups)
    return render(request, 'data_table_group.html', {'groups': groups})

def activate_group(request, group_id):
    if not request.session.get('member_id'):
        return redirect('login')
    group = get_object_or_404(Group, id=group_id)
    group.status = 1
    group.save()
    messages.success(request, f"{group.name} Activated successfully.")
    return redirect('data_table_group')

def deactivate_group(request, group_id):
    if not request.session.get('member_id'):
        return redirect('login')
    group = get_object_or_404(Group, id=group_id)
    group.status = 0
    group.save()
    messages.success(request, f"{group.name} Deativated successfully.")
    return redirect('data_table_group')