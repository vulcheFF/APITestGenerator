from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class TestRun(SQLModel, table = True):
    id: Optional[int] = Field(default=None, primary_key=True)
    base_url: str
    total_tests: int
    passed_count: int
    issues_found: int
    run_timestamp: datetime= Field(default_factory = datetime.now)


class TestResult(SQLModel, table = True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="testrun.id")
    method: str
    path: str
    test_type: str
    category: Optional[str] = None
    field: Optional[str] = None
    expected_status: Optional[int] = None
    passed:bool = True
    description: str
    status_code: int
    data_sent: Optional[str] = None


class Issue(SQLModel, table = True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="testrun.id")
    method: str
    path: str
    category: Optional[str] = None
    field: Optional[str] = None
    expected_status: Optional[int] = None
    description: str
    status_code: int
    severity: str        