import math
from rest_framework import serializers
from pydantic import ValidationError
from .schema import Layout
from .services.validator import validate_layout, GeometryError

class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError('Expected an object with only documented fields.')
        return super().to_internal_value(data)

class FiniteSize(serializers.FloatField):
    def to_internal_value(self, data):
        if isinstance(data, bool) or not isinstance(data, (int, float)):
            raise serializers.ValidationError('Expected a finite numeric dimension.')
        value = super().to_internal_value(data)
        if not math.isfinite(value) or not .1 <= value <= 1000:
            raise serializers.ValidationError('Dimension must be finite and between 0.1 and 1000.')
        return value

class GenerateSerializer(StrictSerializer):
    prompt = serializers.CharField(max_length=4000, allow_blank=False)
    width = FiniteSize()
    depth = FiniteSize()
    unit = serializers.ChoiceField(choices=['ft','m'])

class ModifySerializer(StrictSerializer):
    current_layout = serializers.JSONField()
    instruction = serializers.CharField(max_length=4000, allow_blank=False)

    def validate_current_layout(self, value):
        try:
            return validate_layout(Layout.model_validate(value)).model_dump()
        except (ValidationError, GeometryError):
            raise serializers.ValidationError('Current layout is not schema-valid and spatially valid.') from None
