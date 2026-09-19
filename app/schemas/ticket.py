import uuid

from pydantic import BaseModel, Field, field_validator


class TicketCreateRequest(BaseModel):
    event_id: uuid.UUID
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    seat: str = Field(min_length=1, max_length=64)

    @field_validator("first_name", "last_name", "seat")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("must not be blank")

        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip()

        if (
            "@" not in value
            or value.startswith("@")
            or value.endswith("@")
            or "." not in value.rsplit("@", 1)[-1]
        ):
            raise ValueError("invalid email address")

        return value


class TicketCreateResponse(BaseModel):
    ticket_id: uuid.UUID


class TicketDeleteResponse(BaseModel):
    success: bool
