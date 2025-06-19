import random
from math import floor

from django.db import models


# Create your models here.
class User(models.Model):
    username = models.CharField(verbose_name="用户名", max_length=11, primary_key=True)
    password = models.CharField(verbose_name="密码", max_length=15)
    nickname = models.CharField(verbose_name="昵称", max_length=64, default="用户")


class Schedule(models.Model):
    executor = models.CharField(verbose_name="用户名", max_length=11)
    scheduleContent = models.CharField(verbose_name="事件内容", max_length=256)
    startTime = models.DateTimeField(verbose_name="开始时间")
    endTime = models.DateTimeField(verbose_name="结束时间")
    resource = models.CharField(verbose_name="所需资源", max_length=256, null=True, default=None)
    priority = models.IntegerField(default=1)  # 任务优先级（1: 低, 2: 中, 3: 高）
    state = models.IntegerField(verbose_name="事件状态", default=0)  # 0是未完成，1是完成

    def __str__(self):
        return self.scheduleContent


class GroupSchedule(models.Model):
    groupID = models.CharField(verbose_name="群ID", max_length=8)
    executor = models.CharField(verbose_name="用户名", max_length=11)
    scheduleContent = models.CharField(verbose_name="事件内容", max_length=256)
    startTime = models.DateTimeField(verbose_name="开始时间")
    endTime = models.DateTimeField(verbose_name="结束时间")
    resource = models.CharField(verbose_name="所需资源", max_length=256, null=True, default=None)
    priority = models.IntegerField(default=1)  # 任务优先级（1: 低, 2: 中, 3: 高）
    state = models.IntegerField(verbose_name="事件状态", default=0)  # 0是未完成，1是完成


class TeamGroup(models.Model):
    groupID = models.CharField(verbose_name="群ID", primary_key=True, max_length=8, editable=False, unique=True)
    groupOwner = models.CharField(verbose_name="团队负责人", max_length=11)
    groupName = models.CharField(verbose_name="团队名", max_length=64)
    groupDescription = models.CharField(verbose_name="团队描述", max_length=256)


class TeamMember(models.Model):
    groupID = models.CharField(verbose_name="群ID", max_length=8)
    username = models.CharField(verbose_name="成员用户名", max_length=11)
    memberName = models.CharField(verbose_name="成员名", max_length=64)
    permission = models.IntegerField(verbose_name="权限", default=0)


class Memo(models.Model):
    username = models.CharField( max_length=11,verbose_name='所属用户')
    title = models.CharField(max_length=100, blank=True, null=True, verbose_name='标题')
    content = models.TextField( blank=True, verbose_name='内容')
    is_pinned = models.BooleanField(default=False, verbose_name='是否置顶')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')


class TeamMemo(models.Model):
    username = models.CharField( max_length=11,verbose_name='创建用户')
    title = models.CharField(max_length=100, blank=True, null=True, verbose_name='标题')
    content = models.TextField( blank=True, verbose_name='内容')
    is_pinned = models.BooleanField(default=False, verbose_name='是否置顶')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    groupID = models.CharField(verbose_name="所属群组", max_length=8)


class Announcement(models.Model):
    title = models.CharField('标题', max_length=100)
    content = models.TextField('内容')
    username = models.CharField( max_length=11,verbose_name='发布人')
    is_important = models.BooleanField('重要公告', default=False)
    publish_time = models.DateTimeField('发布时间', auto_now_add=True)
    last_modified = models.DateTimeField('最后修改时间', auto_now=True)
    groupID = models.CharField(verbose_name="所属群组", max_length=8)


class TimerRecord(models.Model):
    TIMER_TYPES = (
        ('countdown', '倒计时'),
        ('stopwatch', '正计时'),
        ('pomodoro', '番茄钟'),
    )

    STATUS_CHOICES = (
        ('completed', '已完成'),
        ('aborted', '已中断'),
    )

    username = models.CharField( max_length=11,verbose_name='所属用户')
    timer_type = models.CharField(max_length=20, choices=TIMER_TYPES)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration = models.PositiveIntegerField(help_text="持续时间(秒)")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    # 番茄钟专用字段
    focus_duration = models.PositiveIntegerField(null=True, blank=True, help_text="专注时长(分钟)")
    break_duration = models.PositiveIntegerField(null=True, blank=True, help_text="休息时长(分钟)")
    rounds_completed = models.PositiveIntegerField(null=True, blank=True, help_text="完成轮次")

    created_at = models.DateTimeField(auto_now_add=True)