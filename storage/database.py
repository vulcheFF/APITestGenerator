from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = "sqlite:///test_results.db"
engine = create_engine(DATABASE_URL, echo=False) #не принтваме всяка сял заявка, при тру принтим

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)

