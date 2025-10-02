from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def timestamp_column() -> Column:
    return Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
