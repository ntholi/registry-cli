from sqlalchemy.orm import Session

from registry_cli.commands.register.crawler import Crawler


def register_students(db: Session) -> None:
    crawler = Crawler(db)
