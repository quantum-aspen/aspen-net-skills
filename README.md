# aspen-net-skills

Shared agent skills for the ASPEN-NET project.

Every skill lives once, as a plain `skills/<name>/SKILL.md` directory at the repo root — the
layout any Agent Skills client expects. `plugins/` holds the Claude Code plugins that group those
skills; their `skills/` entries are symlinks into the canonical set, so there is exactly
one copy of every skill.

- **meetings** — transcribe Zoom recordings on-device and publish summaries to the
  [ASPEN-NET wiki](https://wiki.quantum-aspen.net).

The [aspen-net-transcriber](https://github.com/quantum-aspen/aspen-net-transcriber) service
bakes these skills into its image at build time, so a change on `main` reaches the service on
its next image build.

## Skills Quickstart

For Claude Code, add the marketplace once:

```bash
/plugin marketplace add quantum-aspen/aspen-net-skills
```

For Hermes, see [Installing with Hermes](#installing-with-hermes).

### meetings

```bash
/plugin install meetings@aspen-net-skills
```

`local-meeting-transcript` downloads a Zoom cloud recording from its share link, transcribes it
locally with faster-whisper, and writes the ASPEN-NET summary to the wiki's Meetings
collection. Needs `ffmpeg`, `yt-dlp` and `uv` on PATH. Publishing the summary needs the
Outline MCP connected to the wiki.

---

## Installing with Hermes

Add this repo as a source once, then install by name:

```bash
hermes skills tap add quantum-aspen/aspen-net-skills
hermes skills install local-meeting-transcript --category aspen-net
```

`hermes skills update` re-fetches installed skills later.

---

## Repository layout

```
skills/<name>/SKILL.md                every skill, one copy, the canonical location
skills.sh.json                        groups the skills for browse/search listings
plugins/<plugin>/skills/<name>        symlink into skills/ — Claude Code grouping
plugins/<plugin>/.claude-plugin/      Claude Code plugin manifest
.claude-plugin/marketplace.json       the Claude Code marketplace
```

Skills live at the repo root because that is where skill registries look for them, which is
what makes `hermes skills tap add` work. `plugins/` exists to give Claude Code its
per-group install, and the marketplace points at it via `metadata.pluginRoot`. Because the
plugin entries are symlinks, `skills/` is the only place you ever edit a skill.

Cloning on Windows needs `git config --global core.symlinks true`, or the plugin
directories come down as plain text files instead of links.
