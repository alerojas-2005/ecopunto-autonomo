from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints
from typing import Annotated

from app.models import AlertStatus, AlertType, CollectionStatus, TransactionType, UserRole

ShortName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
PositiveFactor = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=4)]
PositiveWeightKg = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=3)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(RequestModel):
    email: EmailStr
    full_name: ShortName
    password: Annotated[str, Field(min_length=12, max_length=128)]
    university_id: UUID


class LoginRequest(RequestModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]


class UserRead(ORMModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserAdminCreate(RequestModel):
    email: EmailStr
    full_name: ShortName
    password: Annotated[str, Field(min_length=12, max_length=128)]
    role: UserRole
    university_id: UUID | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BootstrapAdminRequest(RequestModel):
    email: EmailStr
    full_name: ShortName
    password: Annotated[str, Field(min_length=12, max_length=128)]


class UniversityRegistrationOption(ORMModel):
    id: UUID
    name: str


class MaterialCreate(RequestModel):
    name: ShortName
    description: Annotated[str | None, Field(max_length=300)] = None
    points_per_gram: PositiveFactor
    active: bool = True


class MaterialPatch(RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=300)
    points_per_gram: PositiveFactor | None = None
    active: bool | None = None


class MaterialRead(ORMModel):
    id: UUID
    name: str
    description: str | None
    points_per_gram: Decimal
    active: bool


class EcoPointCreate(RequestModel):
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]
    name: ShortName
    address: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
    active: bool = True


class EcoPointPatch(RequestModel):
    code: str | None = Field(default=None, min_length=2, max_length=40)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, min_length=1, max_length=240)
    active: bool | None = None


class EcoPointRead(ORMModel):
    id: UUID
    code: str
    name: str
    address: str
    active: bool
    created_at: datetime


class CompartmentCreate(RequestModel):
    material_id: UUID
    label: ShortName
    capacity_kg: PositiveWeightKg
    current_kg: Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=3)] = Decimal("0")
    fill_threshold_pct: Annotated[int, Field(gt=0, le=100)] = 80
    active: bool = True


class CompartmentPatch(RequestModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    capacity_kg: PositiveWeightKg | None = None
    fill_threshold_pct: Annotated[int | None, Field(gt=0, le=100)] = None
    active: bool | None = None


class CompartmentRead(ORMModel):
    id: UUID
    ecopoint_id: UUID
    material_id: UUID
    label: str
    capacity_kg: Decimal
    current_kg: Decimal
    fill_threshold_pct: int
    active: bool
    fill_percentage: Decimal


class DepositCreate(RequestModel):
    ecopoint_id: UUID
    compartment_id: UUID
    material_id: UUID
    weight_g: Annotated[int, Field(gt=0, le=100_000)]


class DepositRead(ORMModel):
    id: UUID
    citizen_id: UUID
    ecopoint_id: UUID
    compartment_id: UUID
    material_id: UUID
    weight_g: int
    factor_applied: Decimal
    points_awarded: Decimal
    created_at: datetime


class PointTransactionRead(ORMModel):
    id: UUID
    user_id: UUID
    deposit_id: UUID | None
    type: TransactionType
    amount: Decimal
    description: str
    created_at: datetime


class BalanceRead(BaseModel):
    balance: Decimal


class AlertRead(ORMModel):
    id: UUID
    compartment_id: UUID
    type: AlertType
    status: AlertStatus
    message: str
    created_at: datetime
    resolved_at: datetime | None


class CollectionCreate(RequestModel):
    ecopoint_id: UUID
    compartment_id: UUID
    weight_kg: PositiveWeightKg
    notes: str | None = Field(default=None, max_length=1000)


class CollectionRead(ORMModel):
    id: UUID
    ecopoint_id: UUID
    compartment_id: UUID
    recycler_id: UUID
    weight_kg: Decimal
    status: CollectionStatus
    created_at: datetime
    notes: str | None
