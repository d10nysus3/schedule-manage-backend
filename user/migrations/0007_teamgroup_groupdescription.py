# Generated by Django 5.1.6 on 2025-03-13 11:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0006_teamgroup_groupname'),
    ]

    operations = [
        migrations.AddField(
            model_name='teamgroup',
            name='groupDescription',
            field=models.CharField(default='group', max_length=256, verbose_name='团队描述'),
            preserve_default=False,
        ),
    ]
