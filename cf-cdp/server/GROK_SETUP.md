# Connect Grok bots to the Comfort Fresh CDP

The CDP runs as an MCP server. Any Grok agent built on the xAI API connects to it as a remote MCP tool.

| Setting | Value |
|---|---|
| Server URL | `https://urgdkrwoxndfdxnllbvx.supabase.co/functions/v1/cdp-mcp` |
| Server label | `comfort_fresh_cdp` |
| Authorization | the bot's CDP key (`cfk_…`), sent as `Authorization: Bearer <key>` |

## Keys and what each can do

| Key | Role | Can |
|---|---|---|
| Sy (Grok) | `sy` | everything, including `approve_campaign` and `send_campaign` (counts as Sy's OK) |
| Team bot (Grok) | `member` | read, tasks, comments, Meta logging, email drafts, Omnisend templates, `prepare_campaign` (test email only) |
| Viewer bot (Grok) | `viewer` | read plan, numbers and customers; comment |

Keys are shown once and stored only as SHA-256 hashes (`api_keys`). To revoke: `update api_keys set active=false where name='…'`.
Every tool call is written to the `audit` table (who, what, arguments, result).

Rules the server enforces no matter which key: ≤3 marketing emails per 30 days per audience, no Omnisend + Gmail
marketing in the same week, subscribed contacts only (segments filter on subscribed), Omnisend brand check before
any write, no Shopify writes at all (the server's Shopify token is read-only).

## xAI API example (Python, Responses API)

```python
from openai import OpenAI
client = OpenAI(base_url="https://api.x.ai/v1", api_key=XAI_API_KEY)
r = client.responses.create(
    model="grok-4",
    instructions=open("bot_instructions.md").read(),
    input="What should we do this week to grow revenue? Prepare the Wave A email.",
    tools=[{
        "type": "mcp",
        "server_url": "https://urgdkrwoxndfdxnllbvx.supabase.co/functions/v1/cdp-mcp",
        "server_label": "comfort_fresh_cdp",
        "authorization": CDP_KEY,
    }],
)
print(r.output_text)
```

## Suggested bot instructions

> You work for Comfort Fresh (DTC socks: large-feet sock size 13–15 and non-binding diabetic socks). North star $100k/month,
> CAC target $70. Always start with `get_overview` and `list_moves`. Only use offers from `list_audiences` (never invent a
> discount). Never invent Meta spend or ROAS. Prepare emails with `prepare_campaign`; a send needs Sy's key, `approve_campaign`,
> then `send_campaign` with confirm "SEND". Leave a note with `add_comment` explaining what you did and why.

## Server secrets (Supabase dashboard → Edge Functions → Secrets)

- `SHOPIFY_ADMIN_TOKEN`: Admin API token with `read_orders` and `read_customers` only.
- `OMNISEND_API_KEY`: Omnisend → Store settings → API keys.

Until both are set, the sync and the Omnisend tools return a clear "not set yet" message.
