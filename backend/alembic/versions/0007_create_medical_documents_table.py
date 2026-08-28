"""create medical documents and chunks tables

Revision ID: 0007_create_medical_documents_table
Revises: 0006_create_appointments_table
Create Date: 2026-08-28 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007_create_medical_documents_table"
down_revision: Union[str, None] = "0006_create_appointments_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create medical_documents table
    op.create_table(
        "medical_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("uploader_user_id", sa.Integer(), nullable=True),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=50), server_default="other", nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_extension", sa.String(length=20), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("processing_status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("total_chunks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["uploader_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_medical_documents_id"), "medical_documents", ["id"], unique=False)
    op.create_index(op.f("ix_medical_documents_document_id"), "medical_documents", ["document_id"], unique=True)
    op.create_index(op.f("ix_medical_documents_patient_id"), "medical_documents", ["patient_id"], unique=False)
    op.create_index(op.f("ix_medical_documents_uploader_user_id"), "medical_documents", ["uploader_user_id"], unique=False)
    op.create_index(op.f("ix_medical_documents_encounter_id"), "medical_documents", ["encounter_id"], unique=False)
    op.create_index(op.f("ix_medical_documents_title"), "medical_documents", ["title"], unique=False)
    op.create_index(op.f("ix_medical_documents_document_type"), "medical_documents", ["document_type"], unique=False)
    op.create_index(op.f("ix_medical_documents_processing_status"), "medical_documents", ["processing_status"], unique=False)

    # 2. Create document_chunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chunk_id", sa.String(length=32), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("vector_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["medical_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_chunks_id"), "document_chunks", ["id"], unique=False)
    op.create_index(op.f("ix_document_chunks_chunk_id"), "document_chunks", ["chunk_id"], unique=True)
    op.create_index(op.f("ix_document_chunks_document_id"), "document_chunks", ["document_id"], unique=False)
    op.create_index(op.f("ix_document_chunks_patient_id"), "document_chunks", ["patient_id"], unique=False)
    op.create_index(op.f("ix_document_chunks_vector_id"), "document_chunks", ["vector_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_chunks_vector_id"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_patient_id"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_document_id"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_chunk_id"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_id"), table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index(op.f("ix_medical_documents_processing_status"), table_name="medical_documents")
    op.drop_index(op.f("ix_medical_documents_document_type"), table_name="medical_documents")
    op.drop_index(op.f("ix_medical_documents_title"), table_name="medical_documents")
    op.drop_index(op.f("ix_medical_documents_encounter_id"), table_name="medical_documents")
    op.drop_index(op.f("ix_medical_documents_uploader_user_id"), table_name="medical_documents")
    op.drop_index(op.f("ix_medical_documents_patient_id"), table_name="medical_documents")
    op.drop_index(op.f("ix_medical_documents_document_id"), table_name="medical_documents")
    op.drop_index(op.f("ix_medical_documents_id"), table_name="medical_documents")
    op.drop_table("medical_documents")
