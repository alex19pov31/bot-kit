import logging
from typing import List, TypeVar, Generic
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, Query
from sqlalchemy.orm.exc import FlushError, NoResultFound
from sqlite3 import IntegrityError as SIError

Base = declarative_base()
T = TypeVar('T')


class ModelManager(Generic[T]):
    def __init__(self, session: Session, model_class):
        self.session: Session = session
        self.model_class = model_class

    def one(self, **kwargs) -> T:
        try:
            return self.query().filter_by(**kwargs).one()
        except NoResultFound:
            return None

    def all(self, **kwargs) -> List[T]:
        return self.query().filter_by(**kwargs).all()

    def save(self, model: T):
        try:
            self.session.add(model)
            self.session.commit()
        except (SIError, IntegrityError, FlushError, InvalidRequestError) as err:
            self.session.rollback()
            logging.error(err)
            raise err

    def delete_items(self, **kwargs):
        pass

    def delete(self, model: T):
        self.session.delete(model)
        self.session.commit()

    def delete_by_id(self, id_record: int):
        model: Base = self.one(id=id_record)
        if not model:
            return

        self.delete(model)

    def query(self, *args) -> Query:
        return self.session.query(self.model_class, *args)


class DBManager:
    def __init__(self, connection_string: str, base_model_class=None):
        self.engine = create_engine(connection_string)
        self.s = sessionmaker(autoflush=False, autocommit=False)
        self.s.configure(bind=self.engine)
        self.session: Session = self.s()
        self.base_model_class = base_model_class

    def manage(self, model_class) -> ModelManager:
        return ModelManager[model_class](self.session, model_class)

    def init_models(self):
        if self.base_model_class is not None:
            self.base_model_class.metadata.create_all(self.engine)
