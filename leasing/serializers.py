from collections import OrderedDict

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from enumfields.drf import EnumSupportSerializerMixin
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from leasing.models import (
    Area, Contact, Decision, Invoice, LeaseAdditionalField, LeaseBuildingFootprint, LeaseCondition,
    LeaseRealPropertyUnit, LeaseRealPropertyUnitAddress, LeaseRealPropertyUnitDetailedPlan,
    LeaseRealPropertyUnitPlotDivision, Note, Rent, Tenant)
from users.serializers import UserSerializer

from .models import Application, ApplicationBuildingFootprint, Lease


def instance_replace_related(instance=None, instance_name=None, related_name=None, serializer_class=None,
                             validated_data=None):
    manager = getattr(instance, related_name)
    manager.all().delete()

    for item in validated_data:
        serializer = serializer_class(data=item)

        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            raise ValidationError({
                related_name: e.detail
            })

        item_instance = serializer.save(**{
            instance_name: instance
        })

        if item_instance and hasattr(manager, 'add'):
            manager.add(item_instance)


def instance_create_or_update_related(instance=None, instance_name=None, related_name=None, serializer_class=None,
                                      validated_data=None):
    manager = getattr(instance, related_name)
    new_items = set()

    for item in validated_data:
        pk = item.pop('id', None)

        serializer_params = {
            'data': item,
        }

        if pk:
            try:
                item_instance = serializer_class.Meta.model._default_manager.get(id=pk)
                serializer_params['instance'] = item_instance
            except ObjectDoesNotExist:
                pass

        serializer = serializer_class(**serializer_params)

        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            raise ValidationError({
                related_name: e.detail
            })

        item_instance = serializer.save(**{
            instance_name: instance
        })

        new_items.add(item_instance)

    if new_items and hasattr(manager, 'add'):
        existing_items = set(manager.all())

        for item in existing_items.difference(new_items):
            manager.remove(item)

        for item in new_items.difference(existing_items):
            manager.add(item)


class InstanceDictPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """
    Like PrimaryKeyRelatedField but the id can be alternatively supplied inside a model instance or a dict.
    """

    def __init__(self, *args, **kwargs):
        self.instance_class = kwargs.pop('instance_class', None)
        self.related_serializer = kwargs.pop('related_serializer', None)

        super().__init__(**kwargs)

    def to_representation(self, obj):
        if self.related_serializer and hasattr(obj, 'pk') and obj.pk:
            obj = self.get_queryset().get(pk=obj.pk)
            return self.related_serializer(obj, context=self.context).to_representation(obj)

        return super().to_representation(obj)

    def to_internal_value(self, value):
        pk = value

        if isinstance(value, dict) and 'id' in value:
            pk = value['id']

        if self.instance_class and isinstance(value, self.instance_class):
            pk = value.id

        return super().to_internal_value(pk)

    def get_choices(self, cutoff=None):
        queryset = self.get_queryset()

        if queryset is None:
            return {}

        if cutoff is not None:
            queryset = queryset[:cutoff]

        return OrderedDict((item.pk, self.display_value(item)) for item in queryset)


class NoteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    author = InstanceDictPrimaryKeyRelatedField(instance_class=User, queryset=User.objects.all(), allow_null=True,
                                                required=False, related_serializer=UserSerializer)

    class Meta:
        model = Note
        fields = '__all__'


class AreaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    notes = NoteSerializer(many=True, required=False)

    class Meta:
        model = Area
        fields = '__all__'

    def create(self, validated_data):
        notes = validated_data.pop('notes', [])

        instance = super().create(validated_data)

        instance_create_or_update_related(instance=instance, instance_name='area', related_name='notes',
                                          serializer_class=NoteSerializer, validated_data=notes)

        return instance

    def update(self, instance, validated_data):
        notes = validated_data.pop('notes', None)

        if notes is not None:
            instance_create_or_update_related(instance=instance, instance_name='area', related_name='notes',
                                              serializer_class=NoteSerializer, validated_data=notes)

        instance = super().update(instance, validated_data)

        return instance


class ApplicationBuildingFootprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationBuildingFootprint
        fields = ('use', 'area')


class ApplicationSerializer(EnumSupportSerializerMixin, serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    building_footprints = ApplicationBuildingFootprintSerializer(many=True, required=False)
    areas = AreaSerializer(many=True, required=False)
    notes = NoteSerializer(many=True, required=False)

    class Meta:
        model = Application
        fields = '__all__'

    def create(self, validated_data):
        building_footprints = validated_data.pop('building_footprints', [])
        areas = validated_data.pop('areas', [])
        notes = validated_data.pop('notes', [])

        instance = super().create(validated_data)

        instance_replace_related(instance=instance, instance_name='application', related_name='building_footprints',
                                 serializer_class=ApplicationBuildingFootprintSerializer,
                                 validated_data=building_footprints)

        instance_create_or_update_related(instance=instance, instance_name='application', related_name='areas',
                                          serializer_class=AreaSerializer, validated_data=areas)

        instance_create_or_update_related(instance=instance, instance_name='application', related_name='notes',
                                          serializer_class=NoteSerializer, validated_data=notes)

        return instance

    def update(self, instance, validated_data):
        building_footprints = validated_data.pop('building_footprints', None)
        areas = validated_data.pop('areas', None)
        notes = validated_data.pop('notes', None)

        instance.building_footprints.all().delete()

        if building_footprints is not None:
            instance_replace_related(instance=instance, instance_name='application', related_name='building_footprints',
                                     serializer_class=ApplicationBuildingFootprintSerializer,
                                     validated_data=building_footprints)

        if areas is not None:
            instance_create_or_update_related(instance=instance, instance_name='application', related_name='areas',
                                              serializer_class=AreaSerializer, validated_data=areas)

        if notes is not None:
            instance_create_or_update_related(instance=instance, instance_name='application', related_name='notes',
                                              serializer_class=NoteSerializer, validated_data=notes)

        instance = super().update(instance, validated_data)

        return instance


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'


class LeaseBuildingFootprintSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseBuildingFootprint
        fields = ('use', 'area')


class DecisionSerializer(EnumSupportSerializerMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Decision
        fields = '__all__'


class RentSerializer(EnumSupportSerializerMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Rent
        fields = '__all__'


class TenantSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    contact = ContactSerializer()
    contact_contact = ContactSerializer(required=False, allow_null=True)
    billing_contact = ContactSerializer(required=False, allow_null=True)

    class Meta:
        model = Tenant
        fields = '__all__'


class InvoiceSerializer(EnumSupportSerializerMixin, serializers.ModelSerializer):
    reference_number = serializers.ReadOnlyField()
    billing_contact = ContactSerializer(required=False, allow_null=True)
    tenants = TenantSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'


class TenantCreateUpdateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    contact = InstanceDictPrimaryKeyRelatedField(instance_class=Contact, queryset=Contact.objects.all(),
                                                 related_serializer=ContactSerializer)
    contact_contact = InstanceDictPrimaryKeyRelatedField(instance_class=Contact, queryset=Contact.objects.all(),
                                                         required=False, allow_null=True,
                                                         related_serializer=ContactSerializer)
    billing_contact = InstanceDictPrimaryKeyRelatedField(instance_class=Contact, queryset=Contact.objects.all(),
                                                         required=False, allow_null=True,
                                                         related_serializer=ContactSerializer)

    class Meta:
        model = Tenant
        fields = ('id', 'contact', 'contact_contact', 'billing_contact', 'share')


class LeaseAdditionalFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseAdditionalField
        fields = ('name', 'value', 'date', 'requires_review', 'reviewed_by', 'reviewed_at')


class LeaseConditionSerializer(EnumSupportSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = LeaseCondition
        fields = ('type', 'description', 'date')


class LeaseRealPropertyUnitAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaseRealPropertyUnitAddress
        fields = ('address',)


class LeaseRealPropertyUnitDetailedPlanSerializer(EnumSupportSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = LeaseRealPropertyUnitDetailedPlan
        fields = ('identification_number', 'description', 'date', 'state')


class LeaseRealPropertyUnitPlotDivisionSerializer(EnumSupportSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = LeaseRealPropertyUnitPlotDivision
        fields = ('identification_number', 'description', 'date', 'state')


class LeaseRealPropertyUnitSerializer(serializers.ModelSerializer):
    addresses = LeaseRealPropertyUnitAddressSerializer(many=True, required=False, allow_null=True)
    detailed_plans = LeaseRealPropertyUnitDetailedPlanSerializer(many=True, required=False, allow_null=True)
    plot_divisions = LeaseRealPropertyUnitPlotDivisionSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = LeaseRealPropertyUnit
        fields = ('identification_number', 'name', 'area', 'registry_date', 'addresses', 'detailed_plans',
                  'plot_divisions')

    def create(self, validated_data):
        addresses = validated_data.pop('addresses', [])
        detailed_plans = validated_data.pop('detailed_plans', [])
        plot_divisions = validated_data.pop('plot_divisions', [])

        instance = super().create(validated_data)

        instance_replace_related(instance=instance, instance_name='lease_property_unit', related_name='addresses',
                                 serializer_class=LeaseRealPropertyUnitAddressSerializer, validated_data=addresses)
        instance_replace_related(instance=instance, instance_name='lease_property_unit', related_name='detailed_plans',
                                 serializer_class=LeaseRealPropertyUnitDetailedPlanSerializer,
                                 validated_data=detailed_plans)
        instance_replace_related(instance=instance, instance_name='lease_property_unit', related_name='plot_divisions',
                                 serializer_class=LeaseRealPropertyUnitPlotDivisionSerializer,
                                 validated_data=plot_divisions)

        return instance

    def update(self, instance, validated_data):
        addresses = validated_data.pop('addresses', [])
        detailed_plans = validated_data.pop('detailed_plans', [])
        plot_divisions = validated_data.pop('plot_divisions', [])

        instance = super().update(instance, validated_data)

        instance_replace_related(instance=instance, instance_name='lease_property_unit', related_name='addresses',
                                 serializer_class=LeaseRealPropertyUnitAddressSerializer, validated_data=addresses)

        instance_replace_related(instance=instance, instance_name='lease_property_unit',
                                 related_name='detailed_plans',
                                 serializer_class=LeaseRealPropertyUnitDetailedPlanSerializer,
                                 validated_data=detailed_plans)

        instance_replace_related(instance=instance, instance_name='lease_property_unit',
                                 related_name='plot_divisions',
                                 serializer_class=LeaseRealPropertyUnitPlotDivisionSerializer,
                                 validated_data=plot_divisions)

        return instance


class LeaseRentSerializer(EnumSupportSerializerMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Rent
        fields = ('id', 'type', 'use', 'start_date', 'end_date', 'amount')


class LeaseSerializer(EnumSupportSerializerMixin, serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    application = ApplicationSerializer(required=False, allow_null=True)
    preparer = UserSerializer(required=False, allow_null=True)
    building_footprints = LeaseBuildingFootprintSerializer(many=True, required=False, allow_null=True)
    decisions = DecisionSerializer(many=True, required=False, allow_null=True)
    real_property_units = LeaseRealPropertyUnitSerializer(many=True, required=False, allow_null=True)
    rents = LeaseRentSerializer(many=True, required=False, allow_null=True)
    tenants = TenantSerializer(many=True, required=False, allow_null=True)
    identifier = serializers.ReadOnlyField(source='identifier_string')
    areas = AreaSerializer(many=True, required=False)
    notes = NoteSerializer(many=True, required=False)
    additional_fields = LeaseAdditionalFieldSerializer(many=True, required=False, allow_null=True)
    conditions = LeaseConditionSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = Lease
        fields = '__all__'


class LeaseCreateUpdateSerializer(EnumSupportSerializerMixin, serializers.ModelSerializer):
    application = InstanceDictPrimaryKeyRelatedField(instance_class=Application, queryset=Application.objects.all(),
                                                     required=False, allow_null=True,
                                                     related_serializer=ApplicationSerializer)
    preparer = InstanceDictPrimaryKeyRelatedField(instance_class=User, queryset=User.objects.all(), allow_null=True,
                                                  related_serializer=UserSerializer)
    building_footprints = LeaseBuildingFootprintSerializer(many=True, required=False, allow_null=True)
    decisions = DecisionSerializer(many=True, required=False, allow_null=True)
    real_property_units = LeaseRealPropertyUnitSerializer(many=True, required=False, allow_null=True)
    rents = LeaseRentSerializer(many=True, required=False, allow_null=True)
    tenants = TenantCreateUpdateSerializer(many=True, required=False, allow_null=True)
    identifier = serializers.ReadOnlyField(source='identifier_string')
    areas = AreaSerializer(many=True, required=False, allow_null=True)
    notes = NoteSerializer(many=True, required=False, allow_null=True)
    additional_fields = LeaseAdditionalFieldSerializer(many=True, required=False, allow_null=True)
    conditions = LeaseConditionSerializer(many=True, required=False, allow_null=True)

    class Meta:
        model = Lease
        fields = '__all__'

    def create(self, validated_data):
        building_footprints = validated_data.pop('building_footprints', [])
        decisions = validated_data.pop('decisions', [])
        real_property_units = validated_data.pop('real_property_units', [])
        rents = validated_data.pop('rents', [])
        tenants = validated_data.pop('tenants', [])
        areas = validated_data.pop('areas', [])
        notes = validated_data.pop('notes', [])
        additional_fields = validated_data.pop('additional_fields', [])
        conditions = validated_data.pop('conditions', [])

        instance = super().create(validated_data)

        instance_replace_related(instance=instance, instance_name='lease', related_name='building_footprints',
                                 serializer_class=LeaseBuildingFootprintSerializer, validated_data=building_footprints)

        instance_create_or_update_related(instance=instance, instance_name='lease', related_name='decisions',
                                          serializer_class=DecisionSerializer, validated_data=decisions)

        instance_replace_related(instance=instance, instance_name='lease', related_name='real_property_units',
                                 serializer_class=LeaseRealPropertyUnitSerializer, validated_data=real_property_units)

        instance_create_or_update_related(instance=instance, instance_name='lease', related_name='rents',
                                          serializer_class=LeaseRentSerializer, validated_data=rents)

        instance_replace_related(instance=instance, instance_name='lease', related_name='tenants',
                                 serializer_class=TenantCreateUpdateSerializer, validated_data=tenants)

        instance_create_or_update_related(instance=instance, instance_name='lease', related_name='areas',
                                          serializer_class=AreaSerializer, validated_data=areas)

        instance_create_or_update_related(instance=instance, instance_name='lease', related_name='notes',
                                          serializer_class=NoteSerializer, validated_data=notes)

        instance_replace_related(instance=instance, instance_name='lease', related_name='additional_fields',
                                 serializer_class=LeaseAdditionalFieldSerializer, validated_data=additional_fields)

        instance_replace_related(instance=instance, instance_name='lease', related_name='conditions',
                                 serializer_class=LeaseConditionSerializer, validated_data=conditions)

        instance.create_identifier()

        return instance

    def update(self, instance, validated_data):
        building_footprints = validated_data.pop('building_footprints', None)
        decisions = validated_data.pop('decisions', None)
        real_property_units = validated_data.pop('real_property_units', None)
        rents = validated_data.pop('rents', None)
        tenants = validated_data.pop('tenants', None)
        areas = validated_data.pop('areas', None)
        notes = validated_data.pop('notes', None)
        additional_fields = validated_data.pop('additional_fields', None)
        conditions = validated_data.pop('conditions', None)

        instance = super().update(instance, validated_data)

        if building_footprints is not None:
            instance_replace_related(instance=instance, related_name='building_footprints',
                                     serializer_class=LeaseBuildingFootprintSerializer,
                                     validated_data=building_footprints)

        if decisions is not None:
            instance_create_or_update_related(instance=instance, instance_name='lease', related_name='decisions',
                                              serializer_class=DecisionSerializer, validated_data=decisions)

        if real_property_units is not None:
            instance_replace_related(instance=instance, instance_name='lease', related_name='real_property_units',
                                     serializer_class=LeaseRealPropertyUnitSerializer,
                                     validated_data=real_property_units)

        if rents is not None:
            instance_create_or_update_related(instance=instance, instance_name='lease', related_name='rents',
                                              serializer_class=LeaseRentSerializer,
                                              validated_data=rents)

        if tenants is not None:
            instance_create_or_update_related(instance=instance, instance_name='lease', related_name='tenants',
                                              serializer_class=TenantCreateUpdateSerializer,
                                              validated_data=tenants)

        if areas is not None:
            instance_create_or_update_related(instance=instance, instance_name='lease', related_name='areas',
                                              serializer_class=AreaSerializer,
                                              validated_data=areas)

        if notes is not None:
            instance_create_or_update_related(instance=instance, instance_name='lease', related_name='notes',
                                              serializer_class=NoteSerializer,
                                              validated_data=notes)

        if additional_fields is not None:
            instance_replace_related(instance=instance, instance_name='lease', related_name='additional_fields',
                                     serializer_class=LeaseAdditionalFieldSerializer, validated_data=additional_fields)

        if conditions is not None:
            instance_replace_related(instance=instance, instance_name='lease', related_name='conditions',
                                     serializer_class=LeaseConditionSerializer, validated_data=conditions)

        instance.create_identifier()

        return instance
