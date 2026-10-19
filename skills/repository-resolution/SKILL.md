---
name: repository-resolution
description: Resolve a local repository alias or GitHub owner/repository reference before working with its files.
---

# Repository resolution

Use this skill when a user refers to a repository as `@alias`,
`@owner/repository`, or `@owner/`.

1. Call the `repository-resolver` MCP server's `resolve_repository` tool.
2. If the result is `found`, state the verified local path and use that
   checkout for subsequent file operations.
3. If the result is `ambiguous`, show the returned locally configured aliases
   and ask the user which one they intend.
4. If the result is `missing`, ask the user for explicit confirmation before
   calling `clone_repository`. Never clone merely because a reference was
   supplied.
5. If the result is `mismatch`, explain that the local checkout's `origin`
   does not match the requested repository. Do not use or overwrite it without
   further user direction.

The resolver reads only the installing user's local configuration file. Do not
suggest adding their aliases to this plugin repository.
