from bot.core.exceptions import (
    StoppedException,
    PausedException,
)

from schedule import Scheduler


class TitanScheduler(Scheduler):
    """
    Custom implementation for the default `Scheduler` class, primarily updating the scheduled jobs
    executor to check an additional function before running a job.
    """
    def __init__(
        self,
        instance,
        stop_func=None,
        pause_func=None,
        force_stop_func=None,
        force_prestige_func=None,
    ):
        """
        Initialize a new scheduler instance.

        The `stop_func` and `pause_func` parameter can be passed in and will be used when running pending events, if either
        of these functions return a non truthy value, we'll raise out early from the job runner.
        """
        super().__init__()

        self.instance = instance
        # check_func() -> True/False.
        # expected to return a boolean.
        self.stop_func = stop_func
        self.pause_func = pause_func
        self.force_stop_func = force_stop_func
        self.force_prestige_func = force_prestige_func

    def run_pending(self):
        """
        Run all jobs that are scheduled to run.

        Please note that it is *intended behavior that run_pending()
        does not run missed jobs*. For example, if you've registered a job
        that should run every minute and you only call run_pending()
        in one hour increments then your job won't be run 60 times in
        between but only once.
        """
        runnable_jobs = (job for job in self.jobs if job.should_run)
        for job in sorted(runnable_jobs):
            if self.stop_func:
                if self.stop_func(instance=self.instance):
                    raise StoppedException()
            if self.pause_func:
                if self.pause_func(instance=self.instance):
                    raise PausedException()
            if self.force_stop_func:
                if self.force_stop_func(instance=self.instance):
                    raise StoppedException()
            if self.force_prestige_func:
                if self.force_prestige_func(instance=self.instance):
                    # If a forced prestige is pending, we'll break out of our pending jobs
                    # early, this ensures the function is executed and the schedule
                    # is updated proper.
                    break
            self._run_job(job)

    def pad_jobs(self, timedelta):
        """
        Pad all existing jobs with the specified timedelta. This will modify the next run date for each job
        and add the timedelta to them.
        """
        for job in self.jobs:
            job.next_run += timedelta
