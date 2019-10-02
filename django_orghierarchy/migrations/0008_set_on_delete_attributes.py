# Generated by Django 2.1.3 on 2018-11-22 14:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        ('django_orghierarchy', '0007_add_abbreviation_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='created_by',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_organizations', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='organization',
            name='data_source',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.DJANGO_ORGHIERARCHY_DATASOURCE_MODEL),
        ),
        migrations.AlterField(
            model_name='organization',
            name='last_modified_by',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='modified_organizations', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='organization',
            name='parent',
            field=mptt.fields.TreeForeignKey(blank=True, help_text='The organizations that contain this organization', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='django_orghierarchy.Organization'),
        ),
        migrations.AlterField(
            model_name='organization',
            name='replaced_by',
            field=models.OneToOneField(blank=True, help_text='The organization that replaces this organization', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replaced_organization', to='django_orghierarchy.Organization'),
        ),
        migrations.AlterField(
            model_name='organizationclass',
            name='data_source',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.DJANGO_ORGHIERARCHY_DATASOURCE_MODEL),
        ),
    ]