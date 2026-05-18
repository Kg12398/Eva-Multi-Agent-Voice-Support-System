"""
SQLAlchemy ORM models for PostgreSQL database.
Stores call records, transcripts, and tickets persistently.
"""

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import uuid


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class CallRecord(Base):
    """Persistent record of every call handled by the system."""
    __tablename__ = "call_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    call_id = Column(String, unique=True, nullable=False, index=True)
    customer_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    contact_number = Column(String, nullable=True)
    product_category = Column(String, nullable=True)
    product_model = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    city = Column(String, nullable=True)
    error_code = Column(String, nullable=True)
    issue_description = Column(Text, nullable=True)
    warranty_status = Column(String, nullable=True)
    diagnosis_result = Column(Text, nullable=True)
    resolution_status = Column(String, nullable=True)  # resolved | escalated | abandoned
    sentiment = Column(String, default="neutral")
    turn_count = Column(Integer, default=0)
    call_duration_seconds = Column(Float, nullable=True)
    transcript = Column(JSON, nullable=True)  # Full conversation history
    call_summary = Column(Text, nullable=True)
    ticket_id = Column(String, nullable=True)
    audio_s3_key = Column(String, nullable=True)  # S3 path to audio recording
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)


class Ticket(Base):
    """Support ticket created when AI escalates an issue."""
    __tablename__ = "tickets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_number = Column(String, unique=True, nullable=False, index=True)
    call_id = Column(String, nullable=False, index=True)
    customer_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    contact_number = Column(String, nullable=True)
    product_category = Column(String, nullable=True)
    product_model = Column(String, nullable=True)
    serial_number = Column(String, nullable=True)
    city = Column(String, nullable=True)
    error_code = Column(String, nullable=True)
    issue_description = Column(Text, nullable=True)
    diagnosis_attempted = Column(Text, nullable=True)
    troubleshooting_steps = Column(JSON, nullable=True)
    priority = Column(String, default="normal")  # low | normal | high | critical
    status = Column(String, default="open")  # open | in_progress | resolved | closed
    sentiment = Column(String, default="neutral")
    call_summary = Column(Text, nullable=True)
    assigned_to = Column(String, nullable=True)
    email_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeDocument(Base):
    """Metadata for documents loaded into the RAG knowledge base."""
    __tablename__ = "knowledge_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    document_type = Column(String, nullable=True)  # manual | faq | troubleshooting
    product_category = Column(String, nullable=True)
    chunk_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
