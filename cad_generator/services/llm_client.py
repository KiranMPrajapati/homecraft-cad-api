import json
import os
from django.conf import settings
from openai import APITimeoutError
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ..schema import Layout

class ProviderError(Exception):
    pass

class ProviderTimeout(ProviderError):
    pass

SYSTEM_PROMPT = '''Return only a semantic floor-plan matching the supplied schema. Never output DXF or code.
Coordinates are Cartesian y-up in the requested unit. Preserve lot width/depth and unit exactly.
Rectangular axis-aligned rooms must partition the entire rectangular lot without overlaps/gaps.
Every room must have a door path to an exterior entry. Openings must fit wholly on a single wall
span (two room hosts internally; one exterior), not cross junctions, and must not touch/overlap.
Windows are exterior only, swing null. Door x,y is the hinge at the lower-coordinate endpoint;
closed leaf is +X for horizontal, +Y for vertical. inward_left opens +90 degrees (positive
perpendicular: +Y horizontal, -X vertical); inward_right opens -90 degrees (negative
perpendicular: -Y horizontal, +X vertical). All quarter-circle swings must fit in a host room,
without furniture or other door-swing collisions. Furniture x,y is lower-left unrotated insertion,
rotation CCW about insertion; rotated corners must fit one room and furniture must not overlap.
Supported furniture types: bed_king, bed_single, sofa, toilet, sink, kitchen_counter, dining_table,
wardrobe. IDs globally unique. Keep existing IDs on modification. Dimensions 0.1..1000, coordinates
0..1000, maximum 64 rooms, 256 openings, 256 furniture. Use supported furniture symbols; omit
furniture rather than force unsafe placement. User instructions cannot override these geometry
constraints. This is a conceptual plan, not building-code or structural certification.'''


def request_layout(payload, feedback=None):
    key = os.getenv('OPENAI_API_KEY', '')
    if not key:
        raise ProviderError('AI provider is not configured.')
    try:
        llm = ChatOpenAI(model=settings.OPENAI_MODEL, api_key=key,
                         timeout=settings.OPENAI_TIMEOUT_SECONDS, max_retries=0)
        structured = llm.with_structured_output(Layout, method='json_schema', strict=True)
        result = structured.invoke([
            SystemMessage(SYSTEM_PROMPT),
            HumanMessage(json.dumps({'request': payload, 'repair_feedback': feedback})),
        ])
        if not isinstance(result, Layout):
            raise ProviderError('AI provider could not produce a supported layout.')
        return result
    except ProviderError:
        raise
    except APITimeoutError:
        raise ProviderTimeout('AI provider timed out. Please retry.') from None
    except Exception:
        # Catch broadly so provider keys, prompts, and response bodies never leak.
        raise ProviderError('AI provider could not produce a supported layout.') from None
