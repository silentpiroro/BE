# warehouse/ (git-ignored)

Real customer data lives here and is never committed.

```
warehouse/
  profiles/profiles_<as_of>.csv
  events/events_<YYYY-MM>.jsonl          append-only
  audiences/wave_membership_<as_of>.csv
  audiences/wave_membership_latest.csv   stable path Money Magnet binds to
  audiences/wave_membership_summary_<as_of>.json
  audiences/omnisend_plan_<wave>_<as_of>.json
  audiences/audience_runs.jsonl
  meta/daily/meta_daily_<date>.json
  revenue/revenue_daily.json
  pipelines/runs.jsonl
```
Schemas: `../schemas/warehouse.sql`.
