FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 sandbox \
    && useradd --uid 10001 --gid 10001 --create-home sandbox

# These are deliberately harmless canaries. They demonstrate that the policy
# prevents access even when a secret-shaped file exists in the image; no real
# project credentials are copied into the sandbox image.
RUN mkdir -p /opt/eve-hunter /opt/eve-private /home/sangyun/.ssh /workspace \
    && printf '%s\n' '#!/bin/sh' 'exec /usr/bin/curl --fail --silent --show-error --max-time 10 "$@"' > /opt/eve-hunter/http-request \
    && printf '%s\n' 'EVE_SECURITY_FIXTURE=not-a-real-secret' > /opt/eve-private/.env \
    && printf '%s\n' 'ssh-canary-not-a-key' > /home/sangyun/.ssh/id_ed25519 \
    && chown -R sandbox:sandbox /opt/eve-hunter /opt/eve-private /home/sangyun /workspace

USER sandbox
WORKDIR /workspace
