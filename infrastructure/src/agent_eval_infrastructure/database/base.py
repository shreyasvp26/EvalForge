"""Declarative Base and shared MetaData for all persistence models."""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from agent_eval_infrastructure.database.naming import NAMING_CONVENTION

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Root for all Infrastructure ORM models.

    Never import or subclass this from Domain or Application. Persistence
    models are an Infrastructure concern (Data Mapper).
    """

    metadata = metadata
