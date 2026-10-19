---
name: repository-resolution
description: Resolve a local repository alias or GitHub owner/repository reference before working with its files.
---

# Repository resolution

Use this skill when a user refers to a repository as `@alias`,
`@owner/repository`, or `@owner/`.

1. Inspect `~/.config/copilot-repo-resolver/config.json` for the clone root and
   aliases. Resolve a short alias before looking at the filesystem.
2. Check the canonical `<repositoriesRoot>/<owner>/<repository>` directory.
   If it is absent, search one level below the configured root for a Git
   checkout whose `origin` matches the resolved repository.
3. If a verified checkout is found, state its path and use it for subsequent
   file operations.
4. For a bare owner reference, show matching locally configured aliases and ask
   the user which one they intend.
5. If no verified checkout exists, ask for explicit confirmation before
   cloning. Never clone merely because a reference was supplied.
6. If a checkout's `origin` differs from the requested repository, explain the
   mismatch. Do not use or overwrite it without further user direction.

The resolver reads only the installing user's local configuration file. Do not
suggest adding their aliases to this plugin repository.
