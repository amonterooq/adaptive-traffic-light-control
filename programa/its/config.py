from pathlib import Path
import json
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[2]
ARMS = ('N', 'E', 'S', 'W')


class Timing(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    min_green: int = Field(default=10, ge=5, le=40)
    max_green: int = Field(default=50, ge=10, le=90)
    fixed_green: int = Field(default=30, ge=10, le=60)
    yellow: int = Field(default=3, ge=3, le=6)
    all_red: int = Field(default=2, ge=2, le=5)
    hysteresis: int = Field(default=2, ge=0, le=10)
    stale_after: int = Field(default=5, ge=1, le=10)

    @model_validator(mode='after')
    def bounds(self):
        if self.min_green > self.max_green:
            raise ValueError('El verde mínimo no puede superar el máximo.')
        return self


def scenarios():
    return json.loads((ROOT/'simulacion/escenarios/escenarios.json').read_text(encoding='utf-8'))
