from peewee import (
    CharField,
)

from database.database import (
    BaseModel,
)


def get_default_instance_name():
    """Attempt to generate a default instance name based on the existing instances currently
    in the system.
    """
    # The count is used to determine if we need to add
    # an additional "index" or if we can just use "1".
    count = Instance.select().count()
    # "Bot Instance " prepended to our default name through count.
    return "Bot Instance %(count)s" % {
        "count": str(count + 1) if count else "1"
    }


class Instance(BaseModel):
    name = CharField(
        default=get_default_instance_name,
        verbose_name="Name",
        help_text=(
            "Specify a name for this instance, the instance name is only used for informational purposes and has "
            "no bearing on any bot functionality."
        ),
    )

    def generate_defaults(self):
        """Generate the default instances if they do not currently exist.
        """
        if self.select().count() == 0:
            for i in range(3):
                # We default to allowing "three" instances, this is purely
                # to keep users from overloading their instances, performance also
                # becomes an issue if many instances are running simultaneously.
                self.create()
