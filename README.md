# Copilot Repository Resolver

Copilot Repository Resolver is a public, generic GitHub Copilot plugin for
resolving short repository aliases to verified local Git checkouts.

It supports:

- Alias references configured on the current machine, such as `flux`.
- Direct `owner/repository` references.
- Bare owner references that list matching locally configured aliases.
- Local checkout verification against the Git `origin` remote.
- An explicit confirmation step before cloning an absent repository.
- Built-in Bash/View operations only, so it works when organizations block
  third-party MCP servers.

## Install

Register the public plugin marketplace:

```shell
copilot plugin marketplace add crh225/copilot-repo-resolver
```

Install the plugin from that marketplace:

```shell
copilot plugin install copilot-repo-resolver@copilot-repo-resolver-marketplace
```

Verify that Copilot loaded it:

```shell
copilot plugin list
```

Start a new Copilot session, then select the `repository-resolver` agent or use
the `repository-resolution` skill when you want a reference resolved.

## Configure aliases

Copy [`examples/config.json`](examples/config.json) to:

```text
~/.config/copilot-repo-resolver/config.json
```

Then replace the example values with your own local aliases:

```json
{
  "repositoriesRoot": "~/development",
  "aliases": {
    "web": "example-org/storefront",
    "api": "example-org/api-service"
  }
}
```

The resolver prefers `<repositoriesRoot>/<owner>/<repository>`, then scans
one directory level below the configured root for a checkout whose Git `origin`
matches the requested repository. This supports alternate local worktree names
without sacrificing remote verification.

Alias configuration is deliberately local. Do not commit your organization's
aliases, repository names, or local filesystem details to this repository.

## Use

After `/restart`, select the resolver agent for the current session:

```text
/agent repository-resolver
```

Then ask it to resolve an alias or repository:

```text
Resolve web
Resolve example-org/storefront
Resolve repositories for example-org
```

For an existing checkout with the expected origin, the resolver returns its
local path. If the checkout is missing, it identifies the intended clone target
and asks for explicit approval before cloning. If a directory exists with a
different origin, it reports the mismatch and does not change the directory.

Copilot CLI reserves `@` for file mentions, so aliases must be entered without
an `@` prefix after selecting the resolver agent.

The plugin uses Copilot's built-in Bash and View tools only. It does not need a
third-party MCP server, so it works in organizations that block third-party MCP
servers.

## Development

For a local plugin check:

```shell
copilot plugin install .
copilot plugin list
```

In a new Copilot session, verify the custom agent with `/agent` and the skill
with `/skills list`.
