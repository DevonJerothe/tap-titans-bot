from django.db.models import (
    Model,
    Manager,
    CharField,
)


def get_default_instance_name():
    """Attempt to generate a default instance name based on the existing instances currently
    in the system.
    """
    # The count is used to determine if we need to add
    # an additional "index" or if we can just use "1".
    count = Instance.objects.count()
    # "Bot Instance " prepended to our default name through count.
    return "Bot Instance %(count)s" % {
        "count": str(count + 1) if count else "1"
    }


class InstanceManager(Manager):
    def generate_defaults(self):
        """Generate default instances if they don't currently exist.
        """
        if self.count() == 0:
            for i in range(3):
                # We default to allowing "three" instances, this is purely
                # to keep users from overloading their instances, performance also
                # becomes an issue if many instances are running simultaneously.
                self.create()


class Instance(Model):
    objects = InstanceManager()

    name = CharField(
        max_length=255,
        default=get_default_instance_name,
        verbose_name="Name",
        help_text=(
            "Specify a name for this instance, the instance name is only used for informational purposes and has "
            "no bearing on any bot functionality."
        ),
    )
