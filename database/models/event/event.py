from peewee import (
    CharField,
    DateTimeField,
    ForeignKeyField,
)

from database.database import (
    BaseModel,
)
from database.models.instance.instance import (
    Instance,
)

import datetime


class Event(BaseModel):
    instance = ForeignKeyField(
        Instance,
        backref="events",
        verbose_name="Instance",
        help_text=(
            "The instance associated with an event."
        ),
    )
    timestamp = DateTimeField(
        default=datetime.datetime.utcnow,
        verbose_name="Timestamp",
        help_text=(
            "The timestamp associated with this event."
        ),
    )
    event = CharField(
        verbose_name="Event",
        help_text=(
            "The event description."
        ),
    )
