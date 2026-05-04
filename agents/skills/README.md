# Agent Skills

This directory contains specialized Agent Skills for development. Unlike general
context files, skills are shared, “on-demand” expertise that multiple AI agents
(such as Gemini CLI, Claude, GitHub Copilot, etc.) can activate when relevant to
your request.

## How to Use

To use a skill, you must first install it into your workspace. Creating a
symlink is preferred so that the skill stays up-to-date when you sync your local
checkout:

```bash
gemini skills link agents/skills/<skill-name> --scope workspace
```

Once installed, your agent will automatically detect when a skill is relevant to
your request and ask for permission to activate it.

## Contributing

New skills should be self-contained within their own directory under
`agents/skills/`. Each skill requires a `SKILL.md` file at its root with a name
and description in the YAML frontmatter.

Example structure:

```
agents/skills/my-skill/SKILL.md
```

And the `SKILL.md` should look like:

```markdown
---
name: My Skill
description: Explains what this skill does and when to use it.
---

# My Skill

Detailed instructions for the skill go here.
```
