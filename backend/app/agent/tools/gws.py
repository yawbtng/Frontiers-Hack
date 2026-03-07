"""Google Workspace CLI tools for LangGraph agent."""

import json
from langchain_core.tools import tool

from core.gws_runner import run_gws, GWSResult


@tool
async def gws(
    command: str,
    dry_run: bool = False,
    force_execute: bool = False,
) -> str:
    """Execute any Google Workspace CLI command.

    The gws CLI provides dynamic access to ALL Google Workspace APIs.
    Format: '<service> <resource> <method> [flags]' or '<service> +helper [flags]'

    ═══ HELPER COMMANDS (preferred — simpler and more reliable) ═══

    Gmail:
    - 'gmail +triage'                                          — unread inbox summary
    - 'gmail +triage --max 5 --query "from:boss"'              — filtered triage
    - 'gmail +send --to EMAIL --subject SUBJ --body TEXT'      — send email

    Calendar:
    - 'calendar +agenda'                                       — upcoming events
    - 'calendar +agenda --today'                               — today's events only
    - 'calendar +agenda --week'                                — this week's events
    - 'calendar +agenda --days 3'                              — next 3 days
    - 'calendar +insert --summary TEXT --start TIME --end TIME' — create event
    - 'calendar +insert ... --location LOC --attendee EMAIL'   — with location/attendees

    Drive:
    - 'drive +upload ./file.pdf'                               — upload file
    - 'drive +upload ./file.pdf --parent FOLDER_ID'            — upload to folder

    Docs:
    - 'docs +write --document DOC_ID --text TEXT'              — append text to doc

    Sheets:
    - 'sheets +read --spreadsheet ID --range "Sheet1!A1:D10"'  — read values
    - 'sheets +append --spreadsheet ID --values "a,b,c"'       — append row

    Chat:
    - 'chat +send --space spaces/SPACE_ID --text TEXT'         — send chat message

    Workflows (cross-service):
    - 'workflow +standup-report'                                — today's meetings + open tasks
    - 'workflow +meeting-prep'                                  — prep for next meeting (agenda, attendees, docs)
    - 'workflow +weekly-digest'                                 — weekly summary: meetings + unread count
    - 'workflow +email-to-task --message-id MSG_ID'            — convert email to task
    - 'workflow +file-announce --file-id ID --space spaces/ID' — announce file in chat

    ═══ RAW API CALLS (when helpers don't cover your need) ═══

    - 'gmail users messages list --params {"userId": "me", "q": "is:unread"}'
    - 'gmail users messages get --params {"userId": "me", "id": "MSG_ID"}'
    - 'calendar events list --params {"calendarId": "primary"}'
    - 'drive files list --params {"q": "name contains 'hackathon'"}'
    - 'tasks tasklists list'
    - 'tasks tasks list --params {"tasklist": "@default"}'
    - 'keep notes list'
    - 'people people connections list --params {"resourceName": "people/me", "personFields": "names,emailAddresses"}'

    ═══ RAW API: --params vs --json ═══

    - --params = URL/query/path parameters (e.g., calendarId, userId, q)
    - --json   = request BODY (e.g., summary, start, end, location, attendees)
    - Example: calendar events insert --params {"calendarId": "primary"} --json {"summary": "Meeting", "start": {"dateTime": "..."}, "end": {"dateTime": "..."}}
    - NEVER put calendarId or userId in --json. They are URL parameters → use --params.

    ═══ IMPORTANT RULES ═══

    - ALL JSON must use DOUBLE QUOTES. Single quotes are invalid JSON.
    - IF A COMMAND FAILS: Call gws_schema to discover correct parameters, then retry.
    - Use --params for query/path parameters (JSON object).
    - Use --json for request body (POST/PATCH/PUT).
    - Use --page-all to auto-paginate results.
    - Create/update/delete operations automatically show a dry-run preview.
    - After user confirms, re-call gws with the SAME command and force_execute=True.
    - Do NOT add --force to the command string. Use the force_execute parameter instead.
    - Times must be ISO 8601 / RFC 3339 (e.g., 2026-03-07T08:00:00-05:00).
    """
    result: GWSResult = await run_gws(command, dry_run=dry_run, force_execute=force_execute)

    if not result.success:
        return json.dumps({"error": result.error, "command": result.command})

    output = {"success": True, "data": result.data, "command": result.command}
    if result.requires_approval and result.dry_run:
        output["requires_approval"] = True
        output["note"] = "This action requires user approval. Showing dry-run preview."
    return json.dumps(output, default=str)


@tool
async def gws_help(command: str) -> str:
    """Get CLI help for any gws service, resource, or helper command.

    Use this to discover available subcommands, flags, and usage examples.

    Examples:
    - 'drive'                — list Drive subcommands and helpers
    - 'drive files list'     — see flags for listing files
    - 'calendar +insert'     — see flags for creating events
    - 'gmail +triage'        — see flags for email triage
    - 'workflow'             — list all workflow helpers
    - 'tasks'                — list Tasks subcommands

    Returns the CLI help output for the given command.
    """
    result = await run_gws(f"{command} --help")
    if not result.success:
        # --help often exits with code 0 but sometimes doesn't; return raw output
        return result.error or "No help available"
    return result.data if isinstance(result.data, str) else json.dumps(result.data, default=str)


def _sanitize_schema(obj):
    """Remove $ref and schemaRef keys that confuse Gemini's function calling.

    Gemini interprets $ref values as references to tool/function names.
    Also truncates overly large response/request body schemas to keep
    the tool response lean — the agent only needs parameter info.
    """
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            # Skip keys that cause Gemini to look for non-existent functions
            if k in ("$ref", "schemaRef"):
                continue
            # Truncate nested response/request schemas — agent doesn't need full body specs
            if k == "response" and isinstance(v, dict):
                cleaned[k] = "(response schema omitted — use gws_help for output details)"
                continue
            if k == "request" and isinstance(v, dict):
                cleaned[k] = "(request body schema omitted — use gws_help for input details)"
                continue
            cleaned[k] = _sanitize_schema(v)
        return cleaned
    elif isinstance(obj, list):
        return [_sanitize_schema(item) for item in obj]
    return obj


@tool
async def gws_schema(method: str) -> str:
    """Inspect any Google Workspace API method's parameters and body schema.

    Use this to discover correct parameters BEFORE calling unfamiliar API methods,
    or AFTER a command fails to understand the correct syntax.

    Format: 'service.resource.method'

    Examples:
    - 'gmail.users.messages.list'   — see query params for listing emails
    - 'calendar.events.insert'      — see required fields for creating events
    - 'calendar.events.list'        — see how to filter events
    - 'drive.files.list'            — see how to search files (q parameter format)
    - 'drive.files.create'          — see how to create/upload files
    - 'tasks.tasks.list'            — see how to list tasks
    - 'docs.documents.get'          — see how to read a doc
    - 'sheets.spreadsheets.values.get' — see how to read sheet values
    - 'people.people.connections.list' — see how to list contacts
    """
    result = await run_gws(f"schema {method}")
    if not result.success:
        return json.dumps({"error": result.error})
    data = result.data
    if isinstance(data, dict):
        data = _sanitize_schema(data)
    return json.dumps({"schema": data}, default=str)
