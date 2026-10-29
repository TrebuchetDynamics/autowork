---
name: apk-get
description: Use when requesting Flutter or React Native ARM64 APKs.
disable-model-invocation: true
---

# APK Get

Apply the [shared Ponytail method](../../../skills/shared/PONYTAIL.md) and
[communication rules](../../../skills/shared/COMMUNICATION.md) within build-and-upload scope.

Read the [host contract](../COMMON.md), then follow the
[host-neutral APK Get workflow](../../../skills/apk-get/SKILL.md).
Resolve its verification script from that workflow's directory.
Use this host's native tools. No Hermes installation is required.
No app-path argument is required: discover the app in the current repository.
Upload the verified release APK through the host's installed `s3upload`, then
return its download URL. Preserve read-only/network limits and delivery exclusions.
