from django.db.models import (
    Model,
    Manager,
    CharField,
    DateTimeField,
    ForeignKey,
    CASCADE,
)

import datetime


class EventManager(Manager):
    pass


class Event(Model):
    objects = EventManager()

    instance = ForeignKey(
        "Instance",
        related_name="events",
        on_delete=CASCADE,
        verbose_name="Instance",
        help_text=(
            "The instance associated with an event."
        ),
    )
    timestamp = DateTimeField(
        default=datetime.datetime.now,
        verbose_name="Timestamp",
        help_text=(
            "The timestamp associated with this event."
        ),
    )
    event = CharField(
        max_length=255,
        verbose_name="Event",
        help_text=(
            "The event description."
        ),
    )
