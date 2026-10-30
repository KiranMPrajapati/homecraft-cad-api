"""Bounded semantic contract; no model-generated executable content."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

Number = Annotated[float, Field(ge=0, le=1000, allow_inf_nan=False)]
Size = Annotated[float, Field(ge=0.1, le=1000, allow_inf_nan=False)]
Text = Annotated[str, Field(min_length=1, max_length=100, pattern=r'^[^\x00-\x1f\\{}]+$')]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class Lot(StrictModel):
    width: Size
    depth: Size

class Room(StrictModel):
    id: Text
    name: Text
    type: Text
    x: Number
    y: Number
    width: Size
    depth: Size

class Opening(StrictModel):
    id: Text
    type: Literal['door', 'window']
    x: Number
    y: Number
    width: Size
    orientation: Literal['horizontal', 'vertical']
    swing: Literal['inward_left', 'inward_right'] | None = None

class Furniture(StrictModel):
    id: Text
    type: Literal['bed_king', 'bed_single', 'sofa', 'toilet', 'sink', 'kitchen_counter', 'dining_table', 'wardrobe']
    label: Text
    x: Number
    y: Number
    width: Size
    depth: Size
    rotation: Annotated[float, Field(ge=0, lt=360, allow_inf_nan=False)] = 0

class Layout(StrictModel):
    project_name: Text
    unit: Literal['ft', 'm']
    lot: Lot
    rooms: Annotated[list[Room], Field(min_length=1, max_length=64)]
    openings: Annotated[list[Opening], Field(max_length=256)]
    furniture: Annotated[list[Furniture], Field(max_length=256)]
