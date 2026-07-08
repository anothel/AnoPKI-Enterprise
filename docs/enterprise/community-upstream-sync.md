# Community Upstream Sync

Keep Enterprise close to Community.

Recommended process:

1. Treat Community as upstream.
2. Pull Community security fixes before Enterprise feature work.
3. Avoid editing shared files when an Enterprise-only overlay can satisfy the need.
4. When shared behavior changes, update Community contracts first or prepare a
   clear upstream patch.
5. Keep Enterprise-only files under `enterprise/`, `docs/enterprise/`,
   `service/internal/enterprise/`, `include/anopki/enterprise/`, or a clearly named
   adapter boundary.
