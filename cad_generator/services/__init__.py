from django.conf import settings
from pydantic import ValidationError
from . import llm_client
from ..schema import Layout
from .validator import GeometryError, validate_layout
from .dxf_compiler import compile_layout


def generate(payload):
    current = payload.get('current_layout')
    lot = current['lot'] if current else {'width':payload['width'], 'depth':payload['depth']}
    unit = current['unit'] if current else payload['unit']
    feedback = None
    for attempt in range(settings.GEOMETRY_REPAIR_RETRIES + 1):
        candidate = llm_client.request_layout(payload, feedback)
        try:
            layout = candidate if isinstance(candidate, Layout) else Layout.model_validate(candidate)
            if layout.unit != unit or layout.lot.model_dump() != lot:
                raise GeometryError('Preserve the original lot width, depth and unit exactly.')
            validate_layout(layout)
            return compile_layout(layout)
        except (ValidationError, GeometryError) as exc:
            feedback = str(exc) if isinstance(exc, GeometryError) else 'Output did not match the required strict schema.'
            if attempt == settings.GEOMETRY_REPAIR_RETRIES:
                raise GeometryError('Unable to produce a valid layout within the repair limit. Try simpler requirements.') from None
