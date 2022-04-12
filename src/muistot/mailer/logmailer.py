from . import Mailer, Result


class LogMailer(Mailer):

    async def send_email(self, email: str, email_type: str, **data) -> Result:
        from ..logging import log
        import pprint
        log.info(f"Email:\n "
                 f"- email: {email}\n "
                 f"- type: {email_type}\n "
                 f"- data:\n{pprint.pformat(data, indent=2, width=200)}")
        return Result(success=True)


def get(**_):
    return LogMailer()
