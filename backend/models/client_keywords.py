"""Client keyword model — stores editable keyword lists per client."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class ClientKeyword(Base):
    """Editable keyword record associated with a client.

    keyword_type: primary | secondary | negative | quick_win
    source:       research_tool (seeded from a research run) | manual (operator edit)
    """

    __tablename__ = "client_keywords"
    __table_args__ = (
        UniqueConstraint("client_id", "keyword", "keyword_type", name="uq_client_keyword_type"),
        Index("idx_client_keywords_lookup", "client_id", "keyword_type", "is_active"),
        Index("idx_client_keywords_result", "research_result_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(
        String,
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    research_result_id = Column(
        String,
        ForeignKey("research_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    keyword = Column(String(200), nullable=False)
    keyword_type = Column(String(20), nullable=False)  # primary|secondary|negative|quick_win
    search_intent = Column(
        String(20), nullable=True
    )  # informational|commercial|transactional|navigational
    difficulty = Column(String(10), nullable=True)  # low|medium|high
    monthly_volume = Column(String(30), nullable=True)  # e.g. "1K-10K"
    relevance_score = Column(Float, nullable=True)  # 1.0-10.0
    quality_score = Column(Float, nullable=True)  # 0-100
    source = Column(String(20), nullable=False, default="manual")  # research_tool|manual
    is_active = Column(Boolean, nullable=False, default=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    client = relationship(
        "backend.models.client.Client",
        foreign_keys=[client_id],
        back_populates="keywords_list",
    )

    def __repr__(self) -> str:
        return f"<ClientKeyword {self.keyword_type}:{self.keyword!r} client={self.client_id}>"
