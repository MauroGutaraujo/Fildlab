import pytest

from app.core import db


@pytest.mark.parametrize("other", [
    "postgresql+asyncpg://different:password@127.0.0.1:5432/fildlab_test?sslmode=require",
    "postgresql://u:p@database-alias/fildlab_test?application_name=pytest",
])
def test_equivalent_database_cannot_be_authorized_by_query_credentials_or_alias(other):
    with pytest.raises(RuntimeError):
        db.assert_distinct_test_database("postgresql://u:p@localhost/fildlab_test", other)


def test_test_target_requires_local_explicitly_named_database():
    validate = getattr(db, "assert_safe_test_target", None)
    assert callable(validate), "pytest needs positive destination validation"
    for url in ["postgresql://u:p@remote.example/fildlab_test", "postgresql://u:p@localhost/production",
                "postgresql://u:p@localhost/fildlab_test?options=-csearch_path=public"]:
        with pytest.raises(RuntimeError):
            validate(url)
    validate("postgresql://u:p@127.0.0.1:55432/fildlab_test")
