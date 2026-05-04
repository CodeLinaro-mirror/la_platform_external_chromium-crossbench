# Agent Extensions & MCP Servers

This directory contains extensions and Model Context Protocol (MCP) server
configurations useful for development within the Crossbench source tree. Each
subdirectory within this directory corresponds to one extension.

Configurations are provided in
[gemini-cli extensions](https://github.com/google-gemini/gemini-cli/blob/main/docs/extensions/index.md)
format.

## Manual Installation

If you prefer not to use a helper script, you can manage extensions directly
using the `gemini` CLI.

### Adding an Extension

To install an extension by creating a symbolic link (preferred, so it stays up
to date):

```bash
gemini extensions link agents/extensions/<extension-name>
```

To install by copying the files:

```bash
gemini extensions install agents/extensions/<extension-name>
```

### Enabling/Disabling Extensions

By default, installed extensions might not be enabled. You can enable them per
workspace or globally.

To enable for the current workspace:

```bash
gemini extensions enable <extension-name> --scope Workspace
```

To enable for all workspaces (user level):

```bash
gemini extensions enable <extension-name> --scope User
```

To disable:

```bash
gemini extensions disable <extension-name> --scope Workspace
```

### Listing Extensions

To see what is installed and enabled:

```bash
gemini extensions list
```

## Types of MCP Servers

There are three types of MCP server configurations supported:

1. **Local MCP Server (tree)**: The configuration for these servers points to a
   local MCP server that is located elsewhere within the source tree.
2. **Local MCP Server (prebuilt)**: These servers are prebuilt as CIPD packages
   and located within the same subdirectory as their configuration files.
3. **Remote MCP Server**: The configuration for these servers contains a
   reference to a remote URL where the MCP server is hosted.

## Creating an MCP server

See the `example-server` for a minimal example for creating an MCP tool with
Python and FastMCP.
