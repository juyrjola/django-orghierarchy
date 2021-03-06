import swapper
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey


class AbstractDataSource(models.Model):
    """Abstract data source model.

    Abstract data source model that provides required fields
    for custom data source model.
    """
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=255)
    user_editable = models.BooleanField(default=False, verbose_name=_('Objects may be edited by users'))

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class DataSource(AbstractDataSource):
    """Default data source model.

    The default data source model will be used if the project
    does not provide a custom data source model.
    """

    class Meta:
        swappable = swapper.swappable_setting('django_orghierarchy', 'DataSource')


class DataModel(models.Model):
    id = models.CharField(max_length=255, primary_key=True, editable=False)
    data_source = models.ForeignKey(
        swapper.get_model_name('django_orghierarchy', 'DataSource'),
        blank=True, null=True, on_delete=models.SET_NULL
    )
    origin_id = models.CharField(max_length=255, blank=True)
    created_time = models.DateTimeField(default=timezone.now, help_text=_('The time at which the resource was created'))
    last_modified_time = models.DateTimeField(auto_now=True, help_text=_('The time at which the resource was updated'))

    class Meta:
        abstract = True
        unique_together = ('data_source', 'origin_id')

    def save(self, *args, **kwargs):
        if not self.id:
            # the id is only set when creating object, it cannot be changed later
            self.id = '{0}:{1}'.format(self.data_source_id, self.origin_id)
        super().save(*args, **kwargs)


class OrganizationClass(DataModel):
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ('data_source', 'origin_id')
        verbose_name = _('Organization class')
        verbose_name_plural = _('Organization classes')

    def __str__(self):
        return self.name


class Organization(MPTTModel, DataModel):
    NORMAL = 'normal'
    AFFILIATED = 'affiliated'

    INTERNAL_TYPES = (
        (NORMAL, _('Normal organization')),
        (AFFILIATED, _('Affiliated organization')),
    )

    internal_type = models.CharField(max_length=20, choices=INTERNAL_TYPES, default=NORMAL)

    classification = models.ForeignKey(OrganizationClass, on_delete=models.PROTECT, blank=True, null=True,
                                       help_text=_('An organization category, e.g. committee'))
    name = models.CharField(max_length=255, help_text=_('A primary name, e.g. a legally recognized name'))
    abbreviation = models.CharField(max_length=50, help_text=_('A commonly used abbreviation'), blank=True, null=True)
    distinct_name = models.CharField(max_length=400, help_text=_('A distinct name for this organization (generated automatically)'), editable=False, null=True)
    founding_date = models.DateField(blank=True, null=True, help_text=_('A date of founding'))
    dissolution_date = models.DateField(blank=True, null=True, help_text=_('A date of dissolution'))
    parent = TreeForeignKey(
        'self', null=True, blank=True, related_name='children',
        help_text=_('The organizations that contain this organization'),
        on_delete=models.SET_NULL
    )
    admin_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='admin_organizations')
    regular_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
                                           related_name='organization_memberships')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_organizations',
                                   null=True, blank=True, editable=False, on_delete=models.SET_NULL)
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='modified_organizations',
                                         null=True, blank=True, editable=False, on_delete=models.SET_NULL)
    replaced_by = models.OneToOneField(
        'self', null=True, blank=True, related_name='replaced_organization',
        help_text=_('The organization that replaces this organization'),
        on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')
        unique_together = ('data_source', 'origin_id')
        permissions = (
            ('add_affiliated_organization', 'Can add affiliated organization'),
            ('change_affiliated_organization', 'Can change affiliated organization'),
            ('delete_affiliated_organization', 'Can delete affiliated organization'),
            ('replace_organization', 'Can replace an organization with a new one'),
        )

    def __str__(self):
        if self.distinct_name:
            name = self.distinct_name
        else:
            name = self.name
        if self.dissolution_date:
            return self.name + ' (dissolved)'
        return name

    @transaction.atomic
    def save(self, *args, **kwargs):
        new_object = not self.pk
        super().save(*args, **kwargs)
        if not new_object:
            return

        # before moving again, the instance must be refreshed from db as it has been moved!
        # https://github.com/django-mptt/django-mptt/issues/257 and
        # https://github.com/django-mptt/django-mptt/issues/279
        new_self = self.__class__.objects.get(pk=self.pk)
        if new_self.parent:
            # move affiliated organization as the first child of parent
            # organization as they need appear before normal child
            # organization when shown in list. We also need to account
            # for the case that an affiliated organization can be changed
            # to a normal organization, thus move normal organization to
            # the last child of parent organization.
            move_positions = {
                self.AFFILIATED: 'first-child',
                self.NORMAL: 'last-child',
            }
            # we must not call move with original self, its fields were outdated by save
            new_self.move_to(new_self.parent, move_positions[self.internal_type])

    def generate_distinct_name(self, levels=1):
        if self.data_source_id == 'helsinki':
            ROOTS = ['Kaupunki', 'Valtuusto', 'Hallitus', 'Toimiala', 'Lautakunta', 'Toimikunta', 'Jaosto']
            stopper_classes = OrganizationClass.objects\
                .filter(data_source='helsinki', name__in=ROOTS).values_list('id', flat=True)
            stopper_parents = Organization.objects\
                .filter(data_source='helsinki', name='Kaupunginkanslia', dissolution_date=None)\
                .values_list('id', flat=True)
        else:
            stopper_classes = []
            stopper_parents = []

        if (stopper_classes and self.classification_id in stopper_classes) or \
                (stopper_parents and self.id in stopper_parents):
            return self.name

        name = self.name
        parent = self.parent
        for level in range(levels):
            if parent is None:
                break
            if parent.abbreviation:
                parent_name = parent.abbreviation
            else:
                parent_name = parent.name
            name = "%s / %s" % (parent_name, name)
            if stopper_classes and parent.classification_id in stopper_classes:
                break
            if stopper_parents and parent.id in stopper_parents:
                break
            parent = parent.parent

        return name

    def autocomplete_label(self):
        return self.distinct_name
    autocomplete_search_field = 'distinct_name'

    @property
    def sub_organizations(self):
        return self.children.filter(internal_type=self.NORMAL)

    @property
    def affiliated_organizations(self):
        return self.children.filter(internal_type=self.AFFILIATED)
