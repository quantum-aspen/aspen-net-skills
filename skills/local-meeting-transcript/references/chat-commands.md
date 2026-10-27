---
name: chat-commands
description: The `ai:` chat convention — how people in a Zoom meeting leave instructions (screenshots, notes, off-record spans) for whoever processes the recording.
---

# `ai:` chat commands

Nobody's agent is live in the meeting. Attendees type chat messages that start with `ai:`,
and the agent reads them from the recording afterwards, so each one works as a bookmark at
the moment it was sent. `chat.py` finds them; this file says what they mean.

## Reading a command

A message is a command only if it starts with `ai:` (any case, leading spaces ignored).
Everything after the prefix is read for **intent, not exact syntax**. People won't remember
a vocabulary, so `ai: screenshot`, `ai: screengrab`, `ai: snap`, `ai: grab this slide`,
`ai: capture`, and `ai: pic of the diagram pls` all mean the same thing. Interpret them the
way a person would. If a command really is unclear, say so in the summary's Chat section
rather than guessing.

| Intent | Examples | What to do |
|---|---|---|
| Screenshot now | `ai: screenshot`, `ai: snap`, `ai: capture this` | Use its candidate frame from `frames.py commands` |
| Screenshot earlier | `ai: screenshot 2 min ago`, `ai: grab the slide from before` | `frames.py at <video> <t − offset> <out.png>`. For "the slide before", pick the last frame in `scenes.json` before the message instead |
| Note for the summary | `ai: note we're going with SOPS`, `ai: action item Marcos gets SSH access` | Put it in the summary as written: a decision, an action item, or a note. Name only the people the text names |
| Off the record | `ai: off record` … `ai: on record` | Leave everything between the two out of the transcript and the summary. An unclosed span runs to the end of the recording |

Any text after the intent is the caption: `ai: screenshot the topology figure`.
Drop the candidate frame for any command that isn't a screenshot request.

## Timing

`t` in `chat.json` is seconds into the recording, `(time − fileStartTime) / 1000`, from the
play-info response. Zoom's `timeFromMeetingStart` counts from when the meeting opened,
which can be minutes before recording began, so it's never used.

`frames.py` takes the frame from just before the message. People type after they've seen
something, so if the screen changed in the last 2 s it takes the frame from before the change.

## In the summary

Upload each kept frame as an Outline attachment, place it at the matching point in the
discussion, and caption it with the request and the sender's name:
*"Topology figure — screenshot requested by Marcos Frenkel (42:10)"*. Zoom records sender
names with each message, so naming the requester is reliable, unlike guessing speakers from
audio.

## Limits

- Only works while the host account saves chat with cloud recordings.
- Only messages sent to everyone are recorded. Private messages aren't seen.
- There's no reply during the meeting. Tell the team about the convention once, e.g. in the
  meeting invite.
