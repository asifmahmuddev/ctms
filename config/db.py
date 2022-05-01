"""Database backend adjustment required by the MongoDB connector.

Django may place a conditional expression directly inside a WHERE clause and advertises that
capability through `conditional_expression_supported_in_where_clause()`, which defaults to True.
The MongoDB backend transpiles SQL rather than executing it and cannot parse that form, so ordinary
filters fail inside the transpiler. Declaring the capability unsupported makes Django emit the plain
comparison form instead.
"""

from djongo.base import DatabaseWrapper
from djongo.operations import DatabaseOperations


class PatchedDatabaseOperations(DatabaseOperations):
    def conditional_expression_supported_in_where_clause(self, _expression):
        return False


def configure_database_backend():
    """Install the patched operations class. Must run before any connection is opened."""

    DatabaseWrapper.ops_class = PatchedDatabaseOperations
