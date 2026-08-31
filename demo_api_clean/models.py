from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ProductCategory(str, Enum):
    ELECTRONICS = "electronics"
    BOOKS = "books"
    HOME = "home"


class ManufacturerInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    country: str


class Product(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Path/stateful tests need a discoverable integer ID.
    id: int

    # String boundary tests.
    name: str = Field(
        min_length=3,
        max_length=40,
    )

    # Pattern test.
    sku: str = Field(
        pattern=r"^[A-Z]{3}-\d{4}$",
    )

    # Enum test.
    category: ProductCategory

    # Boolean test.
    active: bool

    # Numeric boundary tests.
    price: float = Field(
        gt=0,
        le=10_000,
        description="Regular product price.",
    )

    quantity: int = Field(
        ge=0,
        le=10_000,
    )

    # Intentionally NO formal minimum.
    # The application still rejects negative values.
    # This lets us exercise the negative_value heuristic.
    warehouse_priority: int

    # Array item type + minItems/maxItems tests.
    tags: list[str] = Field(
        min_length=1,
        max_length=4,
    )

    # uniqueItems is deliberately visible in OpenAPI.
    # Validation below actually rejects duplicates.
    feature_codes: list[str] = Field(
        min_length=1,
        json_schema_extra={"uniqueItems": True},
    )

    # Intentionally NO minItems in the formal schema.
    # Application-level validation rejects an empty list.
    # This exercises empty_array.
    supported_regions: list[str]

    # Nested object tests.
    manufacturer: ManufacturerInfo

    # AI implicit-constraint candidate.
    # No formal pattern is declared intentionally.
    serial_code: str = Field(
        description=(
            "Product serial code. It must contain letters only."
        )
    )

    primary_code: str = Field(
        min_length=2,
        max_length=12,
        description="Primary internal product code.",
    )

    secondary_code: str = Field(
        min_length=2,
        max_length=12,
        description=(
            "Secondary internal product code. "
            "It must be different from primary_code."
        ),
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: int) -> int:
        if value < 0:
            raise ValueError("id cannot be negative")
        return value


    @field_validator("warehouse_priority")
    @classmethod
    def validate_warehouse_priority(cls, value: int) -> int:
        if value < 0:
            raise ValueError("warehouse_priority cannot be negative")
        return value

    @field_validator("feature_codes")
    @classmethod
    def validate_unique_feature_codes(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("feature_codes must contain unique values")
        return value

    @field_validator("supported_regions")
    @classmethod
    def validate_supported_regions(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("supported_regions cannot be empty")
        return value

    @field_validator("serial_code")
    @classmethod
    def validate_serial_code(cls, value: str) -> str:
        if not value.isalpha():
            raise ValueError(
                "serial_code must contain letters only"
            )
        return value

    @model_validator(mode="after")
    def validate_product_codes(self):
        if self.secondary_code == self.primary_code:
            raise ValueError(
                "secondary_code must be different from primary_code"
            )
        return self