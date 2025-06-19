"""
URL configuration for schedule_manage project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from user import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/login/', views.login),
    path('api/register/', views.register),
    path('api/updatePersonalData/', views.update_user_data),

    path('api/getGroupList/', views.get_group_info),
    path('api/createGroup/', views.create_group),
    path('api/searchGroup/', views.search_group),
    path('api/joinGroup/', views.join_group),
    path('api/getGroupMembers/', views.get_member),
    path('api/getGroupEvents/', views.get_schedule_info),
    path('api/getMemberInfo/', views.get_member_info),

    path('api/getTeamData/', views.get_group),
    path('api/getTeamMember/', views.get_team_member),
    path('api/updateDescription/', views.update_team_description),
    path('api/updateMemberName/', views.update_team_nickname),
    path('api/updatePermission/', views.update_team_permission),
    path('api/deleteMember/', views.delete_team_member),

    path('api/smart_input/', views.smart_input),
    path('api/audio_path_upload/', views.recognize_audio),
    path('api/addSchedule/', views.add_schedule),
    path('api/adjustSchedule/', views.adjust_schedule),

    path('api/getSchedule/', views.get_schedule),
    path('api/updateSchedule/', views.update_schedule),
    path('api/updateTeamSchedule/', views.update_team_schedule),
    path('api/deleteSchedule/', views.delete_schedule),
    path('api/updateScheduleState/', views.update_schedule_state),

    path('api/all_tasks/', views.get_all_tasks),
    path('api/personal_tasks/', views.get_personal_tasks),
    path('api/group_tasks/', views.get_group_tasks),
    path('api/user_groups/', views.get_user_groups),

    path('api/get_memos/', views.get_memos),
    path('api/update_memo/', views.update_memo),
    path('api/add_memo/', views.add_memo),
    path('api/delete_memos/', views.delete_memo),
    path('api/search_memos/', views.search_memos),

    path('api/get_team_memos/', views.get_team_memos),
    path('api/update_team_memo/', views.update_team_memo),
    path('api/add_team_memo/', views.add_team_memo),
    path('api/delete_team_memos/', views.delete_team_memo),
    path('api/search_team_memos/', views.search_team_memos),

    path('api/get_team_announcement/', views.get_team_announcement),
    path('api/update_team_announcement/', views.update_team_announcement),
    path('api/add_team_announcement/', views.add_team_announcement),
    path('api/delete_team_announcement/', views.delete_team_announcement),
    path('api/search_team_announcement/', views.search_team_announcement),

]
