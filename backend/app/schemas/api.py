from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints
from typing import Annotated

from app.models import AlertStatus, AlertType, AssignmentStatus, CollectionStatus, OrganizationStatus, OrganizationType, RecyclerLinkType, RecyclerProfileStatus, TransactionType, UserRole

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
    email: str
    full_name: str
    role: UserRole
    university_id: UUID | None
    is_active: bool
    created_at: datetime


class UserAdminCreate(RequestModel):
    email: EmailStr
    full_name: ShortName
    password: Annotated[str, Field(min_length=12, max_length=128)]
    role: UserRole
    university_id: UUID | None = None


class UserUpdate(RequestModel):
    email: EmailStr | None = None
    full_name: ShortName | None = None
    role: UserRole | None = None
    university_id: UUID | None = None
    is_active: bool | None = None


class UniversityRead(ORMModel):
    id: UUID
    name: str
    slug: str
    city: str
    campus_name: str
    address: str | None
    active: bool
    public_registration_enabled: bool
    created_at: datetime
    updated_at: datetime


class UniversityUpdate(RequestModel):
    name: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)] = None
    slug: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] = None
    city: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)] = None
    campus_name: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)] = None
    address: Annotated[str | None, Field(max_length=240)] = None
    active: bool | None = None
    public_registration_enabled: bool | None = None


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
    university_id: UUID | None = None
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
    university_id: UUID
    code: str
    name: str
    address: str
    active: bool
    created_at: datetime


class CompartmentCreate(RequestModel):
    material_id: UUID | None = None
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
    material_id: UUID | None
    label: str
    capacity_kg: Decimal
    current_kg: Decimal
    fill_threshold_pct: int
    active: bool
    fill_percentage: Decimal


class DepositCreate(RequestModel):
    ecopoint_id: UUID
    compartment_id: UUID
    material_id: UUID | None = None
    weight_g: Annotated[int, Field(gt=0, le=100_000)]


class DepositRead(ORMModel):
    id: UUID
    citizen_id: UUID
    ecopoint_id: UUID
    compartment_id: UUID
    material_id: UUID | None
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
    material_id: UUID | None = None
    weight_kg: Decimal
    status: CollectionStatus
    created_at: datetime
    notes: str | None


class OrganizationCreate(RequestModel):
    name: ShortName
    type: OrganizationType
    tax_id: str | None = Field(default=None, max_length=40)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=240)
    city: ShortName = "Bogotá"
    description: str | None = None
    status: OrganizationStatus = OrganizationStatus.PENDING


class OrganizationPatch(RequestModel):
    name: ShortName | None = None
    type: OrganizationType | None = None
    tax_id: str | None = Field(default=None, max_length=40)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=240)
    city: ShortName | None = None
    description: str | None = None
    status: OrganizationStatus | None = None


class OrganizationRead(ORMModel):
    id: UUID
    name: str
    type: OrganizationType
    tax_id: str | None
    phone: str | None
    email: str | None
    address: str | None
    city: str
    description: str | None
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime
    sector_ids: list[UUID] = []
    ecopoint_ids: list[UUID] = []


class OrganizationCoverageUpdate(RequestModel):
    sector_ids: list[UUID]
    ecopoint_ids: list[UUID] = []


class SectorCreate(RequestModel):
    locality: ShortName
    name: ShortName
    city: ShortName = "Bogotá"
    description: str | None = None
    active: bool = True


class SectorRead(ORMModel):
    id: UUID
    locality: str
    name: str
    city: str
    description: str | None
    active: bool
    ecopoint_ids: list[UUID] = []


class SectorPatch(RequestModel):
    name: ShortName | None = None
    locality: ShortName | None = None
    city: ShortName | None = None
    active: bool | None = None


class SectorPointsUpdate(RequestModel):
    ecopoint_ids: list[UUID]


class AssignmentCreate(RequestModel):
    recycler_id: UUID
    sector_id: UUID | None = None
    university_id: UUID | None = None
    ecopoint_id: UUID | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: AssignmentStatus = AssignmentStatus.ACTIVE
    notes: str | None = None


class AssignmentPatch(RequestModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: AssignmentStatus | None = None
    notes: str | None = None


class AssignmentRead(ORMModel):
    id: UUID
    recycler_id: UUID
    sector_id: UUID | None
    university_id: UUID | None
    ecopoint_id: UUID | None
    starts_at: datetime
    ends_at: datetime | None
    status: AssignmentStatus
    notes: str | None
    organization_id: UUID | None = None
    origin: str = "DIRECT"
    sector_name: str | None = None
    university_name: str | None = None
    ecopoint_name: str | None = None


class RecyclerCreate(RequestModel):
    email: EmailStr
    full_name: ShortName
    password: Annotated[str, Field(min_length=12, max_length=128)]
    organization_id: UUID | None = None
    link_type: RecyclerLinkType | None = None
    phone: str | None = Field(default=None, max_length=40)
    document_type: str | None = Field(default=None, max_length=20)
    document_number: str | None = Field(default=None, max_length=40)
    is_active: bool = True


class RecyclerPatch(RequestModel):
    full_name: ShortName | None = None
    email: EmailStr | None = None
    organization_id: UUID | None = None
    link_type: RecyclerLinkType | None = None
    phone: str | None = Field(default=None, max_length=40)
    document_type: str | None = Field(default=None, max_length=20)
    document_number: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None


class RecyclerRead(UserRead):
    organization_id: UUID | None = None
    organization_name: str | None = None
    link_type: RecyclerLinkType = RecyclerLinkType.INDEPENDENT
    profile_status: RecyclerProfileStatus = RecyclerProfileStatus.ACTIVE
    phone: str | None = None
    document_type: str | None = None
    document_number: str | None = None


class RecyclerDashboardRead(BaseModel):
    profile: RecyclerRead
    assignments: list[AssignmentRead]
    collections: list[CollectionRead]
    recovered_weight_kg: Decimal
    collection_count: int
    material_weights: list[dict[str, str | Decimal]]
    as_of: datetime
