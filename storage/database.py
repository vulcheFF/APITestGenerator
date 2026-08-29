from sqlmodel import SQLModel, create_engine, Session, inspect

DATABASE_URL = "sqlite:///test_results.db"
RUN_METADATA_COLUMNS = {
    "seed": "INTEGER",
    "ai_enabled": "BOOLEAN",
    "ai_model": "VARCHAR",
    "duration_ms": "INTEGER",
}

RESULT_METADATA_COLUMNS = {"template_path": "VARCHAR"}

ISSUE_METADATA_COLUMNS = {"template_path": "VARCHAR"}

engine = create_engine(DATABASE_URL, echo=False) #не принтваме всяка сял заявка, при тру принтим



def _ensure_table_columns(table_name: str, columns: dict[str,str]):
    inspector = inspect(engine)

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}

    with engine.begin() as connection:
        for column_name, column_type in columns.items():
            if column_name not in existing_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN {column_name} {column_type}"
                )

def _ensure_run_metadata_columns():

    inspector = inspect(engine)
    existing_columns = {
        column["name"] for column in inspector.get_columns("testrun")
    }
    with engine.begin() as connection:
        #existing_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(test_run)").fetchall()}

        for column_name, column_type in RUN_METADATA_COLUMNS.items():
            if column_name not in existing_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE testrun "
                    f"ADD COLUMN {column_name} {column_type}"
                )


def init_db():
    SQLModel.metadata.create_all(engine)
    _ensure_run_metadata_columns()

    _ensure_table_columns("testresult", RESULT_METADATA_COLUMNS)
    _ensure_table_columns("issue", ISSUE_METADATA_COLUMNS)
def get_session():
    return Session(engine)

