from peewee import (
    SqliteDatabase,
    Model,
)
from peewee_migrate import (
    Router,
)

from settings import (
    LOCAL_DATABASE,
    LOCAL_DATABASE_SETTINGS,
)


db = SqliteDatabase(
    database=LOCAL_DATABASE,
    pragmas=LOCAL_DATABASE_SETTINGS,
)
router = Router(
    database=db,
    migrate_table="migration",
)


class BaseModel(Model):
    class Meta:
        database = db


class Singleton(BaseModel):
    @classmethod
    def get(cls):
        # Super call get_or_none to avoid recursion issues...
        # Also, just care about determining if ONE exists.
        if cls.select().first() is None:
            return cls.create()

        # Always return super get() call with no args,
        # we just want the ONE that exists.
        return cls.select().first()
