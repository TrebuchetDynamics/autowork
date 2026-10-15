# Hosting authentication readiness

Use for Git-host authentication, credential-helper failures and browser-assisted CLI login. This is a diagnostic and handoff recipe, not evidence that a login has completed.

## 1. Identify the exact failing layer

1. Read the effective host-scoped helper and its origin with `git config --show-origin --get-all credential.https://HOST.helper`; inspect the general `credential.helper` separately. Keep secret-bearing helper arguments out of output. An invalid helper path is not proof that the account or token is invalid.
2. Resolve the installed CLI and test `--version` with a short bound before making authenticated requests. Consult that installed version's `auth login --help`; do not assume another hosting CLI's subcommands or a newer version's flags exist.
3. Test public network access separately from authenticated account/API access. A public clone, branch read or successful TLS connection cannot certify push permission, CI access or a release identity.
4. Diagnose the existing login process before replacing it: inspect its own output, executable/child names and callback listener without dumping full argv, environment or stored credentials. Cancel an owned stalled attempt before starting another, so duplicate browser/device sessions do not accumulate.

## 2. Distinguish configuration, keyring and network waits

- Probe isolation with a private configuration only when the CLI documents that mechanism. Verify which configuration file it actually reads; setting an environment variable without observing its effect does not establish isolation. Preserve the original configuration and other hosts.
- If a Linux CLI waits on Secret Service, read service metadata instead of extracting passwords or guessing that credentials are missing. These read-only queries were exercised successfully:

```sh
gdbus call --session --dest org.freedesktop.secrets \
  --object-path /org/freedesktop/secrets \
  --method org.freedesktop.DBus.Properties.Get \
  org.freedesktop.Secret.Service Collections

# Set COLLECTION to an object path returned above, not an assumed collection name.
gdbus call --session --dest org.freedesktop.secrets \
  --object-path "$COLLECTION" \
  --method org.freedesktop.DBus.Properties.Get \
  org.freedesktop.Secret.Collection Locked
```

- A locked collection proves a secure-store prerequisite, not an invalid hosting account. Request that the user unlock it through the operating system's secure UI; never request or type that password in chat or shell input.
- If requesting a native Secret Service prompt programmatically, keep one D-Bus connection alive through `Unlock`, `Prompt` and the `Completed` signal. Separate short-lived `gdbus` invocations can lose the prompt when the first client disconnects. A successful `Prompt` call proves only that a dialog was requested: reread `Locked` afterward before claiming an unlock.
- Do not silently switch to plaintext token storage to avoid a locked keyring. If a different storage policy is genuinely necessary, explain the tradeoff and obtain the user's choice rather than treating it as a routine retry.

## 3. Start browser authorization and stop at the real user action

- Use a tracked interactive process for the installed CLI's supported web/device flow; retain its handle and completion notification. Let the user authenticate in their own browser and approve the requested account/scope.
- Share the actual provider authorization destination only after it is emitted. Distinguish waiting for keyring unlock, waiting for browser approval and completed authentication; a silent live process is not a generated browser link.
- After one evidence-changing retry, stop repeating the same silent login. Report one concrete prerequisite the user can satisfy and leave only the intended process waiting. A cancelled prompt is not approval to choose weaker credential storage.
- Verify completion with the CLI's authentication status and a harmless authenticated account/API read. Do not infer login success from browser navigation, an OAuth callback alone or a zero-output process.

## 4. Repair helpers and resume only authorized work

- Repair only the affected host's helper, using the resolved executable path rather than a temporary installation path. Preserve unrelated host settings and restore inherited-helper isolation when required by the configuration. Do not rewrite global credential configuration merely to make a diagnostic succeed.
- For an SSH alternative, verify the host key against authoritative provider metadata and use a command-scoped known-hosts file where appropriate; never disable host-key checks or blindly trust a scanned key. Host verification and public-key account authorization are separate results.
- Reverify the exact host/ref and permissions before resuming delivery. Successful login is neither a successful mirror push nor a released application, and a login-only request does not widen publication scope.

The observed Secret Service metadata queries and persistent prompt mechanism do not establish an end-to-end hosting login. Never present an unresolved authentication attempt as a validated OAuth recovery procedure.
