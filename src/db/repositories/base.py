"""Base repository.

Repositories receive an open cursor and never own the connection lifecycle, so a
single service method can compose several repositories inside one transaction.

User-scoped repositories (everything holding tenant data) extend
``UserScopedRepository`` which makes ``user_id`` a required constructor argument —
multitenancy is enforced *here* so no service can accidentally cross tenants.
(The ``user_id`` plumbing lands fully in Phase 1; ``BaseRepository`` is used by
the global reference tables — categories / payment methods.)
"""

from __future__ import annotations

from psycopg2.extras import RealDictCursor


class BaseRepository:
    def __init__(self, cur: RealDictCursor):
        self.cur = cur


class UserScopedRepository(BaseRepository):
    def __init__(self, cur: RealDictCursor, user_id: int):
        super().__init__(cur)
        if user_id is None:
            raise ValueError("user_id is required for tenant-scoped repositories")
        self.user_id = user_id
