"""SQLAlchemy models for KratorAI."""

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()


class Designer(Base):
    """Registered designer/creator."""
    __tablename__ = "designers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    designs = relationship("Design", back_populates="owner")


class Design(Base):
    """A design template or generated asset."""
    __tablename__ = "designs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("designers.id"), nullable=False)
    
    # Asset storage
    asset_uri = Column(String(512), nullable=False)
    thumbnail_uri = Column(String(512))
    
    # Metadata
    title = Column(String(255))
    description = Column(String(1024))
    tags = Column(JSON, default=list)  # ["adinkra", "kente", "logo"]
    cultural_region = Column(String(100))  # "West Africa", "East Africa", etc.
    
    # Generation info
    is_original = Column(Boolean, default=True)
    generation_prompt = Column(String(2048))
    generation_model = Column(String(100))  # "gemini", "sdxl_cultural_v1"
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("Designer", back_populates="designs")
    parent_relations = relationship(
        "DesignLineage",
        foreign_keys="DesignLineage.child_id",
        back_populates="child",
    )


class DesignLineage(Base):
    """Parent-child relationships for bred designs."""
    __tablename__ = "design_lineage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    child_id = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    
    # Contribution weight (0-1)
    weight = Column(Float, nullable=False)
    
    # Relationships
    child = relationship("Design", foreign_keys=[child_id], back_populates="parent_relations")


class RoyaltyTransaction(Base):
    """Royalty payments from design usage."""
    __tablename__ = "royalty_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    design_id = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("designers.id"), nullable=False)
    
    # Payment details
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    share_percentage = Column(Float, nullable=False)
    
    # Transaction info
    transaction_type = Column(String(50))  # "sale", "subscription", "license"
    created_at = Column(DateTime, default=datetime.utcnow)
