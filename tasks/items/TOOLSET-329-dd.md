+++
schema = 1
id = "TOOLSET-329-dd"
title = "Decide how the runner supports Nous Portal models"
short = "Owner: Nous Portal provider path"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Needs decision"
rank = 4000
depends_on = []
touches = []
resources = []
kind = "plan"
ownership = "owner"
scope = "GitHub issue 1 asks for guided Nous Portal support for Pi runners in the CLI, TUI and service (Pi stays the executor). The model-list parsing bug it reported is fixed (autowork models now says Pi listed no models). A verified workaround uses the local Hermes proxy (hermes proxy start --provider nous) with a custom Pi provider in ~/.pi/agent/models.json. Decide: support only the local-proxy path (autowork writes or checks the Pi provider entry and the proxy), also a direct API-key path, or neither. Writing ~/.pi/agent/models.json changes user configuration, so the decision names whether autowork may write it."
acceptance = ["The owner records the decision as an Owner decision note; an implementation task follows only from it"]
exclusions = []
+++

- Sources: https://github.com/TrebuchetDynamics/autowork/issues/1
