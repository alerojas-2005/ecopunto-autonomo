from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Column,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.core.database import Base


class UTCDateTime(TypeDecorator[datetime]):
    """Persist UTC datetimes and restore UTC tzinfo with SQLite."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, _dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, _dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class UserRole(str, Enum):
    CITIZEN = "CITIZEN"
    ADMIN = "ADMIN"
    RECYCLER = "RECYCLER"


class TransactionType(str, Enum):
    EARN = "EARN"
    REDEEM = "REDEEM"


class AlertType(str, Enum):
    FILL_THRESHOLD = "FILL_THRESHOLD"


class AlertStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"


class CollectionStatus(str, Enum):
    COMPLETED = "COMPLETED"


class OrganizationType(str, Enum):
    ASSOCIATION = "ASSOCIATION"
    COOPERATIVE = "COOPERATIVE"
    COMPANY = "COMPANY"
    INDEPENDENT = "INDEPENDENT"
    OTHER = "OTHER"


class OrganizationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"


class AssignmentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"
    SUSPENDED = "SUSPENDED"


class RecyclerLinkType(str, Enum):
    ORGANIZATION = "ORGANIZATION"
    INDEPENDENT = "INDEPENDENT"


class RecyclerProfileStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING = "PENDING"


organization_sectors = Table(
    "organization_sectors", Base.metadata,
    Column("organization_id", Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
    Column("sector_id", Uuid(as_uuid=True), ForeignKey("coverage_sectors.id", ondelete="RESTRICT"), primary_key=True),
)
sector_ecopoints = Table(
    "sector_ecopoints", Base.metadata,
    Column("sector_id", Uuid(as_uuid=True), ForeignKey("coverage_sectors.id", ondelete="CASCADE"), primary_key=True),
    Column("ecopoint_id", Uuid(as_uuid=True), ForeignKey("ecopoints.id", ondelete="RESTRICT"), primary_key=True),
)


class University(Base):
    __tablename__ = "universities"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    city: Mapped[str] = mapped_column(String(120))
    campus_name: Mapped[str] = mapped_column(String(160))
    address: Mapped[str | None] = mapped_column(String(240), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    public_registration_enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    users: Mapped[list["User"]] = relationship(back_populates="university")
    ecopoints: Mapped[list["EcoPoint"]] = relationship(back_populates="university")


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), index=True)
    type: Mapped[OrganizationType] = mapped_column(SAEnum(OrganizationType, native_enum=False, length=16), index=True)
    tax_id: Mapped[str | None] = mapped_column(String(40), nullable=True, unique=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    address: Mapped[str | None] = mapped_column(String(240), nullable=True)
    city: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[OrganizationStatus] = mapped_column(SAEnum(OrganizationStatus, native_enum=False, length=12), default=OrganizationStatus.PENDING, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    sectors: Mapped[list["CoverageSector"]] = relationship(secondary=organization_sectors, back_populates="organizations")


class RecyclerProfile(Base):
    __tablename__ = "recycler_profiles"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    link_type: Mapped[RecyclerLinkType] = mapped_column(SAEnum(RecyclerLinkType, native_enum=False, length=12), default=RecyclerLinkType.INDEPENDENT)
    document_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[RecyclerProfileStatus] = mapped_column(SAEnum(RecyclerProfileStatus, native_enum=False, length=12), default=RecyclerProfileStatus.ACTIVE, index=True)
    linked_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC))
    user: Mapped["User"] = relationship(back_populates="recycler_profile", foreign_keys=[user_id])


class CoverageSector(Base):
    __tablename__ = "coverage_sectors"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    locality: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    city: Mapped[str] = mapped_column(String(120), default="Bogotá")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    organizations: Mapped[list[Organization]] = relationship(secondary=organization_sectors, back_populates="sectors")
    ecopoints: Mapped[list["EcoPoint"]] = relationship(secondary=sector_ecopoints, back_populates="coverage_sectors")


class RecyclerAssignment(Base):
    __tablename__ = "recycler_assignments"
    __table_args__ = (UniqueConstraint("recycler_id", "sector_id", "university_id", "ecopoint_id", "status", name="uq_recycler_assignment_scope_status"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    recycler_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True, index=True)
    origin: Mapped[str] = mapped_column(String(12), default="DIRECT", index=True)
    sector_id: Mapped[UUID | None] = mapped_column(ForeignKey("coverage_sectors.id", ondelete="RESTRICT"), nullable=True, index=True)
    university_id: Mapped[UUID | None] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=True, index=True)
    ecopoint_id: Mapped[UUID | None] = mapped_column(ForeignKey("ecopoints.id", ondelete="RESTRICT"), nullable=True, index=True)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC))
    ends_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    status: Mapped[AssignmentStatus] = mapped_column(SAEnum(AssignmentStatus, native_enum=False, length=12), default=AssignmentStatus.PENDING, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "(role = 'ADMIN' AND university_id IS NULL) OR "
            "(role = 'CITIZEN' AND university_id IS NOT NULL) OR "
            "(role = 'RECYCLER')",
            name="ck_user_role_university",
        ),
        UniqueConstraint("id", "university_id", name="uq_user_id_university"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, native_enum=False, length=16), default=UserRole.CITIZEN, index=True)
    university_id: Mapped[UUID | None] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC))

    university: Mapped["University | None"] = relationship(back_populates="users")
    deposits: Mapped[list["Deposit"]] = relationship(back_populates="citizen")
    transactions: Mapped[list["PointTransaction"]] = relationship(back_populates="user")
    collections: Mapped[list["Collection"]] = relationship(back_populates="recycler", foreign_keys="Collection.recycler_id")
    recycler_profile: Mapped["RecyclerProfile | None"] = relationship(
        back_populates="user", uselist=False, foreign_keys="RecyclerProfile.user_id"
    )


class EcoPoint(Base):
    __tablename__ = "ecopoints"
    __table_args__ = (
        UniqueConstraint("university_id", "code", name="uq_ecopoint_university_code"),
        UniqueConstraint("id", "university_id", name="uq_ecopoint_id_university"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(40))
    university_id: Mapped[UUID] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str] = mapped_column(String(240))
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC))

    university: Mapped[University] = relationship(back_populates="ecopoints")
    compartments: Mapped[list["Compartment"]] = relationship(back_populates="ecopoint")
    deposits: Mapped[list["Deposit"]] = relationship(back_populates="ecopoint")
    collections: Mapped[list["Collection"]] = relationship(back_populates="ecopoint")
    coverage_sectors: Mapped[list[CoverageSector]] = relationship(secondary=sector_ecopoints, back_populates="ecopoints")


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (CheckConstraint("points_per_gram > 0", name="ck_material_points_positive"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    points_per_gram: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    compartments: Mapped[list["Compartment"]] = relationship(back_populates="material")
    deposits: Mapped[list["Deposit"]] = relationship(back_populates="material")


class Compartment(Base):
    __tablename__ = "compartments"
    __table_args__ = (
        CheckConstraint("capacity_kg > 0", name="ck_compartment_capacity_positive"),
        CheckConstraint("current_kg >= 0", name="ck_compartment_weight_nonnegative"),
        CheckConstraint("fill_threshold_pct > 0 AND fill_threshold_pct <= 100", name="ck_compartment_threshold_range"),
        CheckConstraint("material_id IS NOT NULL OR label = 'No identificados'", name="ck_unidentified_compartment_label"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    ecopoint_id: Mapped[UUID] = mapped_column(ForeignKey("ecopoints.id", ondelete="RESTRICT"), index=True)
    material_id: Mapped[UUID | None] = mapped_column(ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True, index=True)
    label: Mapped[str] = mapped_column(String(80))
    capacity_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    current_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=Decimal("0"))
    fill_threshold_pct: Mapped[int] = mapped_column(default=80)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    ecopoint: Mapped[EcoPoint] = relationship(back_populates="compartments")
    material: Mapped[Material | None] = relationship(back_populates="compartments")
    deposits: Mapped[list["Deposit"]] = relationship(back_populates="compartment")
    collections: Mapped[list["Collection"]] = relationship(back_populates="compartment")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="compartment")

    @property
    def fill_percentage(self) -> Decimal:
        if not self.capacity_kg:
            return Decimal("0")
        return (self.current_kg / self.capacity_kg * Decimal("100")).quantize(Decimal("0.01"))


class Deposit(Base):
    __tablename__ = "deposits"
    __table_args__ = (
        CheckConstraint("weight_g > 0", name="ck_deposit_weight_positive"),
        CheckConstraint(
            "(material_id IS NULL AND factor_applied = 0 AND points_awarded = 0) OR "
            "(material_id IS NOT NULL AND factor_applied > 0 AND points_awarded > 0)",
            name="ck_deposit_reward_matches_material",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    citizen_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    ecopoint_id: Mapped[UUID] = mapped_column(ForeignKey("ecopoints.id", ondelete="RESTRICT"), index=True)
    compartment_id: Mapped[UUID] = mapped_column(ForeignKey("compartments.id", ondelete="RESTRICT"), index=True)
    material_id: Mapped[UUID | None] = mapped_column(ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True, index=True)
    weight_g: Mapped[int]
    factor_applied: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    points_awarded: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC), index=True)

    citizen: Mapped[User] = relationship(back_populates="deposits")
    ecopoint: Mapped[EcoPoint] = relationship(back_populates="deposits")
    compartment: Mapped[Compartment] = relationship(back_populates="deposits")
    material: Mapped[Material | None] = relationship(back_populates="deposits")
    point_transaction: Mapped["PointTransaction | None"] = relationship(back_populates="deposit", uselist=False)


class PointTransaction(Base):
    __tablename__ = "point_transactions"
    __table_args__ = (
        CheckConstraint("amount != 0", name="ck_point_transaction_nonzero"),
        CheckConstraint("(type = 'EARN' AND amount > 0) OR (type = 'REDEEM' AND amount < 0)", name="ck_point_transaction_direction"),
        CheckConstraint("(type = 'EARN' AND deposit_id IS NOT NULL) OR (type = 'REDEEM' AND deposit_id IS NULL)", name="ck_point_transaction_deposit_link"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    deposit_id: Mapped[UUID | None] = mapped_column(ForeignKey("deposits.id", ondelete="RESTRICT"), unique=True, nullable=True)
    type: Mapped[TransactionType] = mapped_column(SAEnum(TransactionType, native_enum=False, length=12))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    description: Mapped[str] = mapped_column(String(240))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC), index=True)

    user: Mapped[User] = relationship(back_populates="transactions")
    deposit: Mapped[Deposit | None] = relationship(back_populates="point_transaction")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("uq_active_compartment_alert", "compartment_id", "type", unique=True, sqlite_where=text("status = 'ACTIVE'")),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    compartment_id: Mapped[UUID] = mapped_column(ForeignKey("compartments.id", ondelete="RESTRICT"), index=True)
    type: Mapped[AlertType] = mapped_column(SAEnum(AlertType, native_enum=False, length=24))
    status: Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus, native_enum=False, length=12), default=AlertStatus.ACTIVE, index=True)
    message: Mapped[str] = mapped_column(String(240))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    compartment: Mapped[Compartment] = relationship(back_populates="alerts")


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = (CheckConstraint("weight_kg > 0", name="ck_collection_weight_positive"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    ecopoint_id: Mapped[UUID] = mapped_column(ForeignKey("ecopoints.id", ondelete="RESTRICT"), index=True)
    compartment_id: Mapped[UUID] = mapped_column(ForeignKey("compartments.id", ondelete="RESTRICT"), index=True)
    recycler_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    material_id: Mapped[UUID | None] = mapped_column(ForeignKey("materials.id", ondelete="RESTRICT"), nullable=True, index=True)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    status: Mapped[CollectionStatus] = mapped_column(SAEnum(CollectionStatus, native_enum=False, length=16), default=CollectionStatus.COMPLETED)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC), index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    ecopoint: Mapped[EcoPoint] = relationship(back_populates="collections")
    compartment: Mapped[Compartment] = relationship(back_populates="collections")
    recycler: Mapped[User] = relationship(back_populates="collections", foreign_keys=[recycler_id])
