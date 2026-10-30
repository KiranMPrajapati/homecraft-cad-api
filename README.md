# AutoCAD AI Generator — Django backend

A standalone stateless Django/DRF API. Pipeline:

`request → LangChain structured output (strict Pydantic) → spatial validation → deterministic geometry → ezdxf R2010`

The model never produces DXF, Python, or executable code. The provider call goes through LangChain's `ChatOpenAI.with_structured_output(Layout, method="json_schema", strict=True)`, so the model is constrained to the `Layout` JSON schema and the result is already a validated Pydantic object. Both preview geometry and DXF are compiled from the same validated semantic layout. There is no database requirement and no generated-code execution.

## Setup

Python 3.11+ and `uv`:

```sh
cd backend-django
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.lock
cp .env.example .env
# Edit .env: set a random DJANGO_SECRET_KEY and your own OPENAI_API_KEY.
.venv/bin/python manage.py check
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

No existing `.env` or real provider key was used during implementation. Tests explicitly disable dotenv and clear the provider key; all provider calls are mocked. Run sequentially:

```sh
.venv/bin/python -m pytest tests -q
```

`requirements.txt` pins direct dependencies; `requirements.lock` also pins transitive dependencies. Re-resolve deliberately when applying security updates. ezdxf currently emits upstream pyparsing deprecation warnings; these are not geometry/audit failures.

## API

All routes are POST, JSON-only, with trailing slash.

### Generate: `/api/generate-floorplan/`

```json
{"prompt":"Two rooms with bedroom, entry and window","width":10,"depth":8,"unit":"m"}
```

### Modify: `/api/modify-floorplan/`

```json
{"current_layout":{"project_name":"...","unit":"m","lot":{"width":10,"depth":8},"rooms":[],"openings":[],"furniture":[]},"instruction":"Move the bed"}
```

The abbreviated layout above illustrates the envelope only; use the complete valid `tests/fixtures/valid_layout.json` for integration. Input layouts are validated before any paid call. Modification must preserve original lot dimensions and unit, including when user instructions request changes. Generate must preserve the explicitly requested dimensions and unit. Incorrect provider dimensions are rejected and repaired, never silently overwritten.

### Successful response

```text
{
  layout: {project_name, unit, lot:{width,depth},
    rooms:[{id,name,type,x,y,width,depth}],
    openings:[{id,type,x,y,width,orientation,swing}],
    furniture:[{id,type,label,x,y,width,depth,rotation}]},
  dxf_content: "0\nSECTION\n...",  // raw ASCII DXF string, NOT base64
  render_geometry: {
    walls:[{x1,y1,x2,y2,layer}],
    doors:[{id,hinge:[x,y],leaf:[x,y],radius,start_angle,end_angle}],
    windows:[{id,x1,y1,x2,y2}]
  }
}
```

DXF is AC1024/R2010 with `$INSUNITS=6` for metres or `2` for feet. Coordinates stay in the requested unit. Unicode labels are escaped into ASCII DXF Unicode escapes. Save `dxf_content` directly as `.dxf`, not the enclosing JSON. Every opening is subtracted from deduplicated room-boundary wall lines. Shared walls are unioned once. Doors include open leaves and true quarter-circle ARC entities. Windows are drawn as two parallel glazing rails plus a centerline (three `A-GLAZ` LINE entities each); the rails are offset perpendicular to the opening by a unit-aware half-separation (`0.075` in metres, `0.25` in feet), computed once in the backend so the SVG preview and the DXF match exactly. The `render_geometry.windows[]` objects therefore carry `{id, x1, y1, x2, y2, rails: [[ax,ay,bx,by],[cx,cy,dx,dy]]}`. Furniture uses scaled, rotated reusable INSERTs. Overall lot dimensions are real rendered aligned DIMENSION entities; each room additionally carries a name label and a `"{width} x {depth} {unit}"` dimension label on `A-ANNO-TEXT`, matching the on-screen preview.

Layers (color / lineweight in hundredths of mm):

| Layer | Color | Weight |
|---|---:|---:|
| A-WALL-EXTR | 7 | 50 |
| A-WALL-INTR | 8 | 35 |
| A-DOOR | 1 | 25 |
| A-GLAZ | 4 | 25 |
| A-FURN | 3 | 18 |
| A-ANNO-TEXT | 2 | 18 |
| A-ANNO-DIMS | 6 | 18 |

Supported furniture types (canonical identifiers shared with the frontend): `bed_king`, `bed_single`, `sofa`, `toilet`, `sink`, `kitchen_counter`, `dining_table`, `wardrobe`. Each is a recognizable unit-square block (`FURN_<TYPE>`): beds with mattress outline, blanket line, and pillow(s); sofa with back/arms/seat division; toilet with tank and bowl; sink with basin and tap; kitchen_counter with sink basin and four burners; dining_table with chairs; wardrobe with doors and diagonal. Entities inside blocks use layer 0 and inherit INSERT styling.

## Exact geometry contract

- Cartesian **y-up**, axis-aligned rectangular rooms filling the entire rectangular lot. Wall geometry is conceptual centerline geometry; frontend can draw thick strokes. No wall-thickness area is removed from rooms.
- Global unique IDs across rooms, openings and furniture. Unknown fields are forbidden.
- Finite numeric coordinates in `[0,1000]`; dimensions in `[0.1,1000]`; rotation `[0,360)`. Booleans and numeric strings are not valid geometric numbers. At most 64 rooms, 256 openings and 256 furniture items. Labels/IDs 1–100 characters, without control characters or DXF formatting escape characters. Prompts/instructions 1–4000 characters. Request body limit 256 KiB.
- Rooms cannot overlap, leave gaps, or extend outside the lot. Tiny numerical tolerances are used for area comparisons (`1e-8` square input units) and rotated-corner containment.
- Opening `(x,y)` is the **lower-coordinate endpoint**. Horizontal extends along +X; vertical extends along +Y. Entire span must belong to one room wall exteriorly or two room walls internally, not cross a partition junction. Openings cannot touch or overlap. Windows must be exterior and `swing:null`.
- For doors `(x,y)` is also the hinge. `inward_left` rotates the closed leaf **+90°**: +Y for horizontal, -X for vertical. `inward_right` rotates **-90°**: -Y for horizontal, +X for vertical. These are mathematical conventions, not architectural handedness inferred from room names.
- `leaf` is the fully **open** endpoint. `start_angle` and `end_angle` describe the CCW quarter-circle arc in degrees, modulo 360. A horizontal right swing is `270 → 0`, not a 270° arc. SVG clients must account for y-axis inversion when drawing arcs.
- Every room needs a graph path through doors to an exterior door. Door swept quarters must fit within a host room and cannot intersect furniture or other door sweeps. Door-vs-furniture uses exact quadrant clipping plus hinge distance. Door-vs-door uses a conservative circumscribed 256-sided disk, so nearly tangent doors can be rejected rather than accepted unsafely.
- Furniture `(x,y)` is the lower-left corner **before rotation**, and rotation is CCW about that insertion point, exactly matching DXF INSERT. Rotate all four corners for browser preview. Furniture must fit a single room after rotation and cannot have positive-area overlap with another item. Supported types: `bed_king, bed_single, sofa, toilet, sink, kitchen_counter, dining_table, wardrobe`. `rotation` defaults to 0 and opening `swing` defaults to null when omitted; doors still require a non-null swing.

## Errors and provider controls

- 400: malformed/unsupported request or invalid current layout.
- 413: body too large; 415: unsupported content type; 429: throttled.
- 422: no valid geometry within repair budget.
- 502: missing key, provider failure/refusal, malformed provider output.
- 504: provider timeout.

LangChain `ChatOpenAI.with_structured_output(Layout, method="json_schema", strict=True)` enforces structured output, binding the model to the `Layout` JSON schema and returning a validated Pydantic object. Model defaults to `gpt-4.1-mini`, configurable via `OPENAI_MODEL`; use an OpenAI-compatible model that supports strict JSON-schema structured outputs. LangChain/SDK automatic retries are disabled (`max_retries=0`). `OPENAI_TIMEOUT_SECONDS` defaults to 25, clamped to 1–60 seconds. `GEOMETRY_REPAIR_RETRIES` defaults to 1, clamped to 0–2 (at most three calls total). Repairs receive validation feedback and the original request; provider transport errors are not retried. Use an external worker/proxy deadline for a hard total request wall-clock bound, because HTTP read timeouts are inactivity limits rather than absolute deadlines. Provider errors/refusals are sanitized via a broad catch: keys, prompts, and provider bodies are not logged or surfaced by application code. Do not enable LangChain/SDK HTTP debug logging in deployment. The API key is read from `OPENAI_API_KEY`; LangChain uses the same variable.

## Deployment

Defaults are for local development, not an authenticated public paid API. `DJANGO_DEBUG=false`; startup requires `DJANGO_SECRET_KEY`. Configure `DJANGO_ALLOWED_HOSTS` and explicit `CORS_ALLOWED_ORIGINS`; CORS is not authentication. No sessions/cookies are used, so CSRF middleware is intentionally not involved in these stateless endpoints.

Before exposing publicly, put authenticated access, budget controls and edge rate limiting in front of the API. Built-in DRF anonymous IP throttling defaults to `10/min` and uses a process-local cache: it is best-effort, not a distributed security/billing boundary. Run one worker for low-memory local use; add a shared cache and edge limits when scaling. Set proxy body limits to 256 KiB too. Configure trusted proxy count (`DJANGO_NUM_PROXIES`) and strip spoofed forwarding headers. Only set `DJANGO_TRUST_PROXY_SSL=true` behind a trusted proxy that controls `X-Forwarded-Proto`.

Enable HTTPS redirect and HSTS using the corresponding `.env.example` switches after TLS is correctly configured. Use a securely generated secret and explicit host list (remove `testserver` if using defaults). Example process command:

```sh
.venv/bin/gunicorn core.wsgi:application --bind 127.0.0.1:8000 --workers 1 --timeout 190
```

A worker timeout is a last-resort process guard, not a graceful API deadline. Never use Django's development server publicly. Run `manage.py check --deploy` after setting production security flags.

## Scope / limitations

Conceptual rectangular partition plans only: no nonrectangular lots, curved walls, multi-storey plans, stair logic, setbacks, structural analysis, wall assemblies, plumbing, accessibility/egress widths or local building-code certification. Graph connectivity does not certify navigable clearance around all furniture. Furniture symbols are schematic, not manufacturer assets. Text placement is simple and can need drafting refinement. Licensed professionals must review any plan before construction. No real provider call was made during verification; correctness tests prove the mocked-provider pipeline and deterministic compiler, not live model quality.

## Files

- `core/`: settings, URLs, ASGI/WSGI (`DJANGO_SETTINGS_MODULE=core.settings`, `core.wsgi:application`).
- `cad_generator/urls.py`: app routes, included under `/api/` by `core/urls.py`.
- `cad_generator/schema.py`, `serializers.py`: strict bounded contracts.
- `cad_generator/services/llm_client.py`: LangChain structured-output provider integration.
- `cad_generator/services/__init__.py`: the `generate()` orchestrator with bounded repairs.
- `cad_generator/services/validator.py`, `geometry.py`: spatial checks and shared preview primitives.
- `cad_generator/services/dxf_compiler.py`, `cad_generator/cad_blocks/`: CAD export and reusable symbols.
- `cad_generator/views.py`, `middleware.py`: endpoint/error handling and body budget.
- `tests/`: mocked API/provider, invalid geometry, door conventions, audited metre/feet DXF roundtrips; fixture ready for frontend integration.
