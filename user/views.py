import json
import random
import datetime
from zoneinfo import ZoneInfo

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from django.utils import timezone
from user import models
from user.utils import post_test
from .models import Schedule, GroupSchedule
from .resource.scheduler import genetic_algorithm, check_conflicts
from .services.parser import ScheduleParser
from django.db.models import Q
from .services.asr_json import speech_recognize


def login(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)
            user = models.User.objects.get(username=data["username"])

            if models.User.objects.filter(username=data["username"], password=data["password"]).exists():
                return JsonResponse({
                    "success": True,
                    "user": {
                        "username": user.username,
                        "nickname": user.nickname
                    }
                })
            else:
                return JsonResponse({"success": False, "message": "密码错误"})
        except models.User.DoesNotExist:
            return JsonResponse({"success": False, "message": "用户不存在"})

    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


@post_test
def register(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)
        if models.User.objects.filter(username=data["username"]).exists():
            return JsonResponse({"success": False, "message": "用户名已存在"})

        models.User.objects.create(
            username=data["username"],
            password=data["password"],
            nickname=data["nickname"]
        )
        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def update_user_data(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)
        try:
            user = models.User.objects.filter(username=data["username"]).first()
            user.nickname = data["nickname"]
            user.save()
            return JsonResponse({
                "success": True,
            })
        except models.TeamGroup.DoesNotExist:
            return JsonResponse({"success": False, "message": "用户信息不存在"})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"服务器错误: {str(e)}"})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def get_group_info(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)
        try:
            members = models.TeamMember.objects.filter(username=data['username'])
            if not members.exists():
                return JsonResponse({"success": False, "message": "用户未加入任何群组"})

            group_info_list = []
            for member in members:
                group = models.TeamGroup.objects.get(groupID=member.groupID)
                group_info_list.append({
                    "groupID": group.groupID,
                    "groupName": group.groupName,
                    "groupDescription": group.groupDescription,
                    "groupOwner": group.groupOwner
                })

            return JsonResponse({
                "success": True,
                "groupInfo": group_info_list
            })
        except models.TeamGroup.DoesNotExist:
            return JsonResponse({"success": False, "message": "群组信息不存在"})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"服务器错误: {str(e)}"})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def get_schedule(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)
        try:
            events = []
            schedules = models.Schedule.objects.filter(executor=data['username'])
            for schedule in schedules:
                events.append({
                    "id": schedule.id,
                    "content": schedule.scheduleContent,
                    "startTime": schedule.startTime,
                    "endTime": schedule.endTime,
                    "resource": schedule.resource,
                    "priority": schedule.priority,
                    "state": schedule.state,
                    "class": 'personal',
                    "groupName": None
                })
            user_groups = models.TeamMember.objects.filter(
                username=data['username']
            ).values_list('groupID', flat=True)
            group_schedules = models.GroupSchedule.objects.filter(
                groupID__in=user_groups,
                executor=data['username']
            )
            groups = models.TeamGroup.objects.filter(groupID__in=user_groups)
            group_map = {group.groupID: group for group in groups}
            for group_schedule in group_schedules:
                group_info = group_map.get(group_schedule.groupID)
                events.append({
                    "id": group_schedule.id,
                    "content": group_schedule.scheduleContent,
                    "startTime": group_schedule.startTime,
                    "endTime": group_schedule.endTime,
                    "resource": group_schedule.resource,
                    "priority": group_schedule.priority,
                    "state": group_schedule.state,
                    "class": 'team',
                    "groupName": group_info.groupName
                })
            return JsonResponse({
                "success": True,
                "events": events
            })
        except models.Schedule.DoesNotExist and models.GroupSchedule.DoesNotExist:
            return JsonResponse({"success": False, "message": "日程信息不存在"})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"服务器错误: {str(e)}"})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def update_schedule(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)

        try:
            if data['class'] == 'personal':
                schedule = models.Schedule.objects.get(id=data['id'])

            elif data['class'] == 'team':
                schedule = models.GroupSchedule.objects.get(id=data['id'])

            schedule.scheduleContent = data.get('content')
            schedule.startTime = datetime.fromtimestamp(data.get("startTime"), ZoneInfo("Asia/Shanghai")).replace(
                tzinfo=None)
            schedule.endTime = datetime.fromtimestamp(data.get("endTime"), ZoneInfo("Asia/Shanghai")).replace(
                tzinfo=None)
            schedule.state = data.get('state')
            schedule.priority = data.get('priority')
            schedule.resource = data.get('resource')
            schedule.save()
            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def update_team_schedule(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)

        try:
            schedule = models.GroupSchedule.objects.get(id=data['id'])
            schedule.executor = models.TeamMember.objects.get(
                groupID=schedule.groupID,
                memberName=data.get("executor")
            ).username
            schedule.scheduleContent = data.get('content')
            schedule.startTime = datetime.fromtimestamp(data.get("startTime"), ZoneInfo("Asia/Shanghai")).replace(
                tzinfo=None)
            schedule.endTime = datetime.fromtimestamp(data.get("endTime"), ZoneInfo("Asia/Shanghai")).replace(
                tzinfo=None)
            schedule.state = data.get('state')
            schedule.priority = data.get('priority')
            schedule.resource = data.get('resource')
            schedule.save()
            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def delete_schedule(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)
        try:
            if data['class'] == 'personal':
                schedule = models.Schedule.objects.get(id=data['id'])
            elif data['class'] == 'team':
                schedule = models.GroupSchedule.objects.get(id=data['id'])
            schedule.delete()
            return JsonResponse({'success': True})
        except models.GroupSchedule.DoesNotExist:
            return JsonResponse({"success": False, "message": "日程不存在"})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def update_schedule_state(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)

        try:
            if data['class'] == 'personal':
                schedule = models.Schedule.objects.get(id=data['id'])

            elif data['class'] == 'team':
                schedule = models.GroupSchedule.objects.get(id=data['id'])

            schedule.state = data.get('state')
            schedule.save()
            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def get_all_tasks(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        if not username:
            return JsonResponse({"success": False, 'message': '用户名不能为空'})

        personal_tasks = list(Schedule.objects.filter(executor=username).values())
        group_ids = models.TeamMember.objects.filter(username=username).values_list('groupID', flat=True)
        group_tasks = list(GroupSchedule.objects.filter(groupID__in=group_ids, executor=username).values())

        all_tasks = personal_tasks + group_tasks
        return JsonResponse({"success": True, 'data': all_tasks})
    except Exception as e:
        return JsonResponse({"success": False, 'message': str(e)})


def get_personal_tasks(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        if not username:
            return JsonResponse({"success": False, 'message': '用户名不能为空'})

        tasks = list(Schedule.objects.filter(executor=username).values())
        return JsonResponse({"success": True, 'data': tasks})
    except Exception as e:
        return JsonResponse({"success": False, 'message': str(e)})


def get_user_groups(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        if not username:
            return JsonResponse({"success": False, 'message': '用户名不能为空'})

        group_ids = models.TeamMember.objects.filter(username=username).values_list('groupID', flat=True)
        groups = list(models.TeamGroup.objects.filter(groupID__in=group_ids).values())
        return JsonResponse({"success": True, 'data': groups})
    except Exception as e:
        return JsonResponse({"success": False, 'message': str(e)})


def get_group_tasks(request):
    try:
        data = json.loads(request.body)
        group_id = data.get('group_id')
        username = data.get('username')

        if not group_id or not username:
            return JsonResponse({'success': False, 'message': '参数不完整'})

        is_member = models.TeamMember.objects.filter(groupID=group_id, username=username).exists()
        if not is_member:
            return JsonResponse({'success': False, 'message': '无权限访问该群组任务'})

        tasks = list(GroupSchedule.objects.filter(groupID=group_id,executor=username).values())
        return JsonResponse({"success": True, 'data': tasks})
    except Exception as e:
        return JsonResponse({"success": False, 'message': str(e)})


def get_memos(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)
            memos = list(models.Memo.objects.filter(username=data['username']).values())
            return JsonResponse({'success': True, 'data': memos})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def add_memo(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            memo = models.Memo.objects.create(
                username=data.get('username'),
                title=data.get('title', ''),
                content=data.get('content', ''),
                is_pinned=data.get('is_pinned', False)
            )
            return JsonResponse({
                "success": True,
                "data": {
                    "id": memo.id,
                    "title": memo.title,
                    "content": memo.content,
                    "is_pinned": memo.is_pinned,
                    "updateTime": memo.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                }
            })
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})
    return JsonResponse({"success": False, "message": "Invalid method"}, status=405)


def delete_memo(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)
            memo = models.Memo.objects.get(id=data['id'])
            memo.delete()
            return JsonResponse({'success': True})
        except models.Memo.DoesNotExist:
            return JsonResponse({"success": False, "message": "备忘录不存在"})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def update_memo(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)

            memo = models.Memo.objects.get(id=data['id'])
            memo.title = data.get('title', '')
            memo.content = data.get('content', '')
            memo.is_pinned = data.get('is_pinned', False)
            memo.updated_at = timezone.now()
            memo.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def search_memos(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            query = data.get('query', '').strip()

            if not query:
                return JsonResponse({
                    "success": False,
                    "message": "搜索内容不能为空"
                }, status=400)

            memos = models.Memo.objects.filter(
                Q(username=data['username']) &
                (Q(title__icontains=query) | Q(content__icontains=query))
            ).order_by('-is_pinned', '-updated_at')

            results = [{
                "id": memo.id,
                "title": memo.title,
                "content": memo.content,
                "is_pinned": memo.is_pinned,
                "updated_at": memo.updated_at
            } for memo in memos]

            return JsonResponse({"success": True, "data": results})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def get_team_memos(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)
            memos = list(models.TeamMemo.objects.filter(groupID=data['groupID']).values())
            return JsonResponse({'success': True, 'data': memos})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def add_team_memo(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            memo = models.TeamMemo.objects.create(
                username=data.get('username'),
                title=data.get('title', ''),
                content=data.get('content', ''),
                is_pinned=data.get('is_pinned', False),
                groupID=data.get('groupID')
            )
            return JsonResponse({
                "success": True,
                "data": {
                    "id": memo.id,
                    "title": memo.title,
                    "content": memo.content,
                    "is_pinned": memo.is_pinned,
                    "updateTime": memo.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                }
            })
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})
    return JsonResponse({"success": False, "message": "Invalid method"}, status=405)


def delete_team_memo(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)
            memo = models.TeamMemo.objects.get(id=data['id'])
            memo.delete()
            return JsonResponse({'success': True})
        except models.TeamMemo.DoesNotExist:
            return JsonResponse({"success": False, "message": "纪要不存在"})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def update_team_memo(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)

            memo = models.TeamMemo.objects.get(id=data['id'])
            memo.title = data.get('title', '')
            memo.content = data.get('content', '')
            memo.is_pinned = data.get('is_pinned', False)
            memo.updated_at = timezone.now()
            memo.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def search_team_memos(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            query = data.get('query', '').strip()

            if not query:
                return JsonResponse({
                    "success": False,
                    "message": "搜索内容不能为空"
                }, status=400)

            memos = models.TeamMemo.objects.filter(
                Q(groupID=data['groupID']) &
                (Q(title__icontains=query) | Q(content__icontains=query))
            ).order_by('-is_pinned', '-updated_at')

            results = [{
                "id": memo.id,
                "title": memo.title,
                "content": memo.content,
                "is_pinned": memo.is_pinned,
                "updated_at": memo.updated_at
            } for memo in memos]

            return JsonResponse({"success": True, "data": results})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def get_team_announcement(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)
            announcements = list(models.Announcement.objects.filter(groupID=data['groupID']).values())
            return JsonResponse({'success': True, 'data': announcements})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def add_team_announcement(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            announcement = models.Announcement.objects.create(
                username=data.get('username'),
                title=data.get('title', ''),
                content=data.get('content', ''),
                is_important=data.get('is_important', False),
                groupID=data.get('groupID')
            )
            return JsonResponse({
                "success": True,
                "data": {
                    "id": announcement.id,
                    "title": announcement.title,
                    "content": announcement.content,
                    "is_important": announcement.is_important,
                    "updateTime": announcement.publish_time.strftime("%Y-%m-%d %H:%M:%S")
                }
            })
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})
    return JsonResponse({"success": False, "message": "Invalid method"}, status=405)


def delete_team_announcement(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)
            announcement = models.Announcement.objects.get(id=data['id'])
            announcement.delete()
            return JsonResponse({'success': True})
        except models.Announcement.DoesNotExist:
            return JsonResponse({"success": False, "message": "公告不存在"})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def update_team_announcement(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)

            announcement = models.Announcement.objects.get(id=data['id'])
            announcement.title = data.get('title', '')
            announcement.content = data.get('content', '')
            announcement.is_important = data.get('is_important', False)
            announcement.last_modified = timezone.now()
            announcement.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def search_team_announcement(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            query = data.get('query', '').strip()

            if not query:
                return JsonResponse({
                    "success": False,
                    "message": "搜索内容不能为空"
                }, status=400)

            announcements = models.Announcement.objects.filter(
                Q(groupID=data['groupID']) &
                (Q(title__icontains=query) | Q(content__icontains=query))
            ).order_by('-is_important', '-updated_at')

            results = [{
                "id": announcement.id,
                "title": announcement.title,
                "content": announcement.content,
                "is_important": announcement.is_important,
                "updated_at": announcement.last_modified
            } for announcement in announcements]

            return JsonResponse({"success": True, "data": results})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def create_group(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)
        while True:
            groupID = str(random.randint(10000000, 99999999))
            if not models.TeamGroup.objects.filter(groupID=groupID).exists():
                break

        models.TeamGroup.objects.create(
            groupID=groupID,
            groupOwner=data["groupOwner"],
            groupName=data["groupName"],
            groupDescription=data["groupDescription"]
        )
        models.TeamMember.objects.create(
            groupID=groupID,
            username=data["groupOwner"],
            memberName=data["groupOwner"],
            permission=2
        )
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def search_group(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)
        if models.TeamGroup.objects.filter(groupID=data["groupID"]).exists():
            group = models.TeamGroup.objects.get(groupID=data["groupID"])
            return JsonResponse({
                "success": True,
                "group": {
                    "groupID": group.groupID,
                    "groupName": group.groupName,
                    "groupDescription": group.groupDescription,
                    "groupOwner": group.groupOwner
                }
            })
        else:
            return JsonResponse({"success": False, "message": "该团队不存在"})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def join_group(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)
        if models.TeamMember.objects.filter(username=data["username"], groupID=data["groupID"]).exists():
            return JsonResponse({"success": False, "message": "你已加入该团队"})
        models.TeamMember.objects.create(
            groupID=data["groupID"],
            username=data["username"],
            memberName=data["username"],
            permission=0
        )
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def get_member_info(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)
        try:
            member = models.TeamMember.objects.get(groupID=data['groupID'], username=data['username'])
            return JsonResponse({
                "success": True,
                "permission": member.permission
            })
        except models.TeamGroup.DoesNotExist:
            return JsonResponse({"success": False, "message": "群组信息不存在"})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def get_group(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)
            group_id = data.get('groupID')

            if not group_id:
                return JsonResponse({"success": False, "message": "groupID 不能为空"}, status=400)

            team = list(models.TeamGroup.objects.filter(groupID=group_id).values())
            return JsonResponse({'success': True, 'data': team})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def get_team_member(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)
            group_id = data.get('groupID')

            if not group_id:
                return JsonResponse({"success": False, "message": "groupID 不能为空"}, status=400)

            members = list(models.TeamMember.objects.filter(groupID=group_id).values())

            return JsonResponse({
                "success": True,
                "data": members
            })
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "请求体不是有效的 JSON"})
    else:
        return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def update_team_description(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)

            team = models.TeamGroup.objects.get(groupID=data['groupID'])
            team.groupDescription = data.get('groupDescription')
            team.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def update_team_nickname(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)

            user = models.TeamMember.objects.get(groupID=data['groupID'], username=data['username'])
            user.memberName = data.get('memberName')
            user.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def update_team_permission(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)

            user = models.TeamMember.objects.get(groupID=data['groupID'], username=data['username'])
            user.permission = data.get('permission')
            user.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def delete_team_member(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)
            user = models.TeamMember.objects.get(username=data['username'], groupID=data['groupID'])
            user.delete()
            return JsonResponse({'success': True})
        except models.Announcement.DoesNotExist:
            return JsonResponse({"success": False, "message": "该成员不存在"})
        except Exception as e:
            return JsonResponse({"success": False, 'message': str(e)})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def get_member(req: HttpRequest):
    if req.method == "POST":
        try:
            data = json.loads(req.body)
            group_id = data.get('groupID')

            if not group_id:
                return JsonResponse({"success": False, "message": "groupID 不能为空"}, status=400)

            members = models.TeamMember.objects.filter(groupID=group_id)

            if not members.exists():
                return JsonResponse({"success": False, "message": "该群组还没有成员"})

            member_list = [member.memberName for member in members]

            return JsonResponse({
                "success": True,
                "groupMembers": member_list
            })
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "请求体不是有效的 JSON"})
    else:
        return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def get_schedule_info(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)
        try:
            schedules = models.GroupSchedule.objects.filter(groupID=data['groupID'])

            schedule_list = []
            for schedule in schedules:
                member = models.TeamMember.objects.get(username=schedule.executor, groupID=schedule.groupID)
                schedule_list.append({
                    "id": schedule.id,
                    "content": schedule.scheduleContent,
                    "startTime": schedule.startTime,
                    "endTime": schedule.endTime,
                    "resource": schedule.resource,
                    "priority": schedule.priority,
                    "state": schedule.state,
                    "executor": member.memberName
                })

            return JsonResponse({
                "success": True,
                "groupInfo": schedule_list
            })
        except models.TeamGroup.DoesNotExist:
            return JsonResponse({"success": False, "message": "事件信息不存在"})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"服务器错误: {str(e)}"})
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def smart_input(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)
        try:
            text = data.get('text')
            executor = data.get('username')
            if not text:
                return JsonResponse({'error': 'Text不能为空'}, status=400)
            parser = ScheduleParser()
            result = parser.parse(text, executor)

            return JsonResponse({'success': True, 'data': {
                'content': result['scheduleContent'],
                'startTime': result['startTime'],
                'endTime': result['endTime'],
                'priority': result['priority'],
                'resources': result['resource']
            }})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def recognize_audio(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        audio_path = data.get('audio_path')
        if not audio_path:
            return JsonResponse({'error': 'audio_path is required'}, status=400)
        try:
            result = speech_recognize(audio_path)
            return JsonResponse({'success': True, 'data': result["result"]})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


def add_schedule(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)
        schedule_class = data.get("class")
        try:
            content = data.get("content")
            startTime = datetime.fromtimestamp(data.get("startTime"), ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
            endTime = datetime.fromtimestamp(data.get("endTime"), ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
            resource = data.get("resource")
            executor = data.get("executor")
            priority = int(data.get("priority"))

            if schedule_class == "team":
                groupID = data.get("groupID")
                new_schedule = GroupSchedule(
                    groupID=groupID,
                    scheduleContent=content,
                    startTime=startTime,
                    endTime=endTime,
                    resource=resource,
                    executor=executor,
                    priority=priority,
                    state=0,
                )
                existing_schedules = list(GroupSchedule.objects.all())
            elif schedule_class == "personal":
                new_schedule = Schedule(
                    scheduleContent=content,
                    startTime=startTime,
                    endTime=endTime,
                    resource=resource,
                    executor=executor,
                    priority=priority,
                    state=0,
                )
                existing_schedules = list(Schedule.objects.all())

            conflicts = check_conflicts(existing_schedules, new_schedule)
            if conflicts:
                return JsonResponse({
                    "success": False,
                    "conflict": True,
                    "message": "检测到事件冲突",
                    "conflicts": conflicts,
                })

            new_schedule.save()
            return JsonResponse({"success": True, "message": "日程添加成功"})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"服务器错误: {str(e)}"}, status=500)
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)


def adjust_schedule(req: HttpRequest):
    if req.method == "POST":
        data = json.loads(req.body)
        schedule_class = data.get("class")
        try:
            content = data.get("content")
            startTime = datetime.fromtimestamp(data.get("startTime"), ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
            endTime = datetime.fromtimestamp(data.get("endTime"), ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
            resource = data.get("resource")
            executor = data.get("executor")
            priority = int(data.get("priority"))

            if schedule_class == "team":
                groupID = data.get("groupID")
                new_schedule = GroupSchedule(
                    groupID=groupID,
                    scheduleContent=content,
                    startTime=startTime,
                    endTime=endTime,
                    resource=resource,
                    executor=executor,
                    priority=priority,
                    state=0,
                )
                existing_schedules = list(GroupSchedule.objects.all())
            elif schedule_class == "personal":
                new_schedule = Schedule(
                    scheduleContent=content,
                    startTime=startTime,
                    endTime=endTime,
                    resource=resource,
                    executor=executor,
                    priority=priority,
                    state=0,
                )
                existing_schedules = list(Schedule.objects.all())

            optimized_schedules = genetic_algorithm(existing_schedules, new_schedule)

            original_ids = set(s.id for s in existing_schedules if hasattr(s, "id"))

            for schedule in optimized_schedules:
                if not hasattr(schedule, "id") or schedule.id not in original_ids:
                    schedule.save()
                else:
                    db_schedule = GroupSchedule.objects.get(id=schedule.id)
                    if db_schedule.startTime != schedule.startTime or db_schedule.endTime != schedule.endTime:
                        db_schedule.startTime = schedule.startTime
                        db_schedule.endTime = schedule.endTime
                        db_schedule.save()

            return JsonResponse({"success": True, "message": "日程调整成功"})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"服务器错误: {str(e)}"}, status=500)
    return JsonResponse({"success": False, "message": "仅支持 POST 请求"}, status=405)
