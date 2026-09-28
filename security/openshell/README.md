# EVE Evidence Hunter OpenShell boundary

This directory contains a minimal, non-production proof policy for EVE's
Evidence Hunter. It deliberately uses a harmless fixture instead of copying
the real project `.env` or any user SSH material into an image.

`host.openshell.internal:8000` is tested as the official OpenShell host-service
route. The host AI-Q service remains bound to `127.0.0.1`; this proof must not
change that binding or enable host networking. A failed request means that a
safe bridge for this loopback-only service has not been established, not that
the sandbox may bypass the policy.
