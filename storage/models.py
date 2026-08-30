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
    seed: Optional[int] = None
    ai_enabled: Optional[bool] = None
    ai_model: Optional[str] = None
    duration_ms: Optional[int] = None
    selected_categories: Optional[str] = None


class TestResult(SQLModel, table = True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="testrun.id")
    method: str
    path: str
    template_path: Optional[str] = None
    test_type: str
    category: Optional[str] = None
    field: Optional[str] = None
    expected_status: Optional[int] = None
    passed:bool = True
    description: str
    status_code: Optional[int] = None
    data_sent: Optional[str] = None


class Issue(SQLModel, table = True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="testrun.id")
    method: str
    path: str
    template_path: Optional[str] = None
    category: Optional[str] = None
    field: Optional[str] = None
    expected_status: Optional[int] = None
    description: str
    status_code: Optional[int] = None
    severity: str        