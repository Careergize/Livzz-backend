from rest_framework import serializers
from .models import Property, RoomConfiguration, Location
from rooms.models import Room

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'city', 'state', 'latitude', 'longitude']


class RoomConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomConfiguration
        fields = [
            'id', 'room_type', 'rent', 'deposit', 
            'total_beds', 'available_beds', 'room_image'
        ]


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = [
            'id', 'room_number', 'sharing_type', 'rent', 'deposit',
            'total_beds', 'occupied_beds', 'is_active'
        ]


class PropertyListSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True, default='')
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True, default='')
    price = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)
    image = serializers.SerializerMethodField()
    amenities = serializers.JSONField()

    class Meta:
        model = Property
        fields = [
            'id',
            'name',
            'property_type',
            'location',
            'location_name',
            'address',
            'city',
            'state',
            'latitude',
            'longitude',
            'description',
            'amenities',
            'price',
            'rating',
            'image',
            'total_rooms',
            'gender_filter',
            'owner_name',
            'is_active',
            'created_at',
        ]

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class PropertyDetailSerializer(serializers.ModelSerializer):
    """Serializer for property detail view (complete info)"""
    owner = serializers.SerializerMethodField()
    room_configs = RoomConfigurationSerializer(many=True, read_only=True)
    rooms = RoomSerializer(many=True, read_only=True)
    amenities = serializers.SerializerMethodField()
    
    class Meta:
        model = Property
        fields = [
            'id', 'name', 'property_type', 'location', 'address', 
            'city', 'state', 'latitude', 'longitude', 'description',
            'amenities', 'price', 'rating', 'image', 'total_rooms',
            'gender_filter', 'is_active', 'owner', 'room_configs', 'rooms',
            'created_at', 'updated_at'
        ]
    
    def get_amenities(self, obj):
        return obj.amenities if obj.amenities else []
    
    def get_owner(self, obj):
        return {
            'name': obj.owner.first_name,
            'contact_number': obj.owner.phone_number,
            'whatsapp_number': obj.owner.whatsapp_number
        }


class PropertyCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating properties"""
    room_configs = RoomConfigurationSerializer(many=True, required=False)
    
    class Meta:
        model = Property
        fields = [
            'name', 'property_type', 'location', 'address', 'city', 'state',
            'latitude', 'longitude', 'description', 'amenities', 'price',
            'rating', 'image', 'total_rooms', 'gender_filter', 'is_active',
            'room_configs'
        ]
    
    def create(self, validated_data):
        room_configs_data = validated_data.pop('room_configs', [])
        property_obj = Property.objects.create(**validated_data)
        
        for room_config_data in room_configs_data:
            RoomConfiguration.objects.create(property=property_obj, **room_config_data)
        
        return property_obj
    
    def update(self, instance, validated_data):
        room_configs_data = validated_data.pop('room_configs', [])
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if room_configs_data:
            instance.room_configs.all().delete()
            for room_config_data in room_configs_data:
                RoomConfiguration.objects.create(property=instance, **room_config_data)
        
        return instance
