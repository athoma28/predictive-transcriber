from pydantic import BaseModel, Field, PositiveInt, validator

DEFAULT_HOTKEY = "Tab"

class Settings(BaseModel):
    context_window: PositiveInt = Field(20,  ge=1,  le=200)
    top_k:          PositiveInt = Field(5,   ge=1,  le=20)
    ngram_order:    PositiveInt = Field(5,   ge=2,  le=7)
    hotkey:         str         = Field(DEFAULT_HOTKEY)

    @validator("hotkey")
    def printable(cls, v):
        if not v.strip():
            raise ValueError("Hotkey cannot be blank")
        return v
