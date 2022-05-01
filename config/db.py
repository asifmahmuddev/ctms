"""Database backend adjustment required by the MongoDB connector.

The connector transpiles SQL rather than executing it and cannot parse a conditional expression
inside a WHERE clause, so declaring that capability unsupported keeps ordinary filters working.
"""

from djongo.base import DatabaseWrapper
from djongo.operations import DatabaseOperations


class PatchedDatabaseOperations(DatabaseOperations):
    """Refuses every expression, so Django writes `field = True` rather than a bare `field`."""

    def conditional_expression_supported_in_where_clause(self, _expression):
        return False


def configure_database_backend():
    """Install the patched operations class. Must run before any connection is opened."""

    DatabaseWrapper.ops_class = PatchedDatabaseOperations
