// Comfort Fresh CDP — MCP server (Streamable HTTP, JSON responses).
// Grok (xAI remote MCP), Claude and any MCP client connect with: Authorization: Bearer <cdp key>.
// Roles: viewer (read), member (read + tasks, comments, drafts, prepare campaigns, log data),
//        sy (everything, including approve + send; a bot using Sy's key counts as Sy's OK).
import { db, omni, omniBrandCheck, sha256 } from "../_shared/clients.ts";
import { syncConsent, syncShopify } from "../_shared/sync.ts";
import * as E from "../_shared/engine.ts";

type Actor = { name: string; role: "viewer" | "member" | "sy" };
const RANK = { viewer: 0, member: 1, sy: 2 } as const;
const need = (a: Actor, r: keyof typeof RANK) => { if (RANK[a.role] < RANK[r]) throw new Error(`This needs the "${r}" role; your key is "${a.role}".`); };

async function all<T>(table: string, cols = "*"): Promise<T[]> {
  const out: T[] = [];
  for (let from = 0; ; from += 1000) {
    const { data, error } = await db.from(table).select(cols).range(from, from + 999);
    if (error) throw new Error(error.message);
    out.push(...(data as T[])); if (!data || data.length < 1000) break;
  }
  return out;
}
async function profiles() {
  const [cs, os] = await Promise.all([all<E.Customer>("customers"), all<E.Order>("orders")]);
  const by = new Map<string, E.Order[]>(); for (const o of os) { o.day = String(o.day); (by.get(o.email) || by.set(o.email, []).get(o.email)!).push(o); }
  const latest = os.reduce((m, o) => (o.day > m ? o.day : m), ""), asOf = latest || E.today();
  const ps = cs.filter((c) => by.has(c.email)).map((c) => E.derive(c, by.get(c.email)!, asOf));
  return { ps, os, asOf };
}
const sentDates = async (aud: string) => ((await db.from("sends").select("day").eq("audience", aud)).data || []).map((r: any) => String(r.day));
function chicagoToUtc(date: string, time: string) {
  const guess = new Date(`${date}T${time}:00Z`);
  const local = new Date(guess.toLocaleString("en-US", { timeZone: "America/Chicago" }));
  return new Date(guess.getTime() + (guess.getTime() - local.getTime()));
}
const log = async (campId: string, line: string) => {
  const { data } = await db.from("campaigns").select("log").eq("id", campId).single();
  await db.from("campaigns").update({ log: ((data?.log || "") + `\n${new Date().toISOString()} · ${line}`).slice(-6000), updated_at: new Date().toISOString() }).eq("id", campId);
};

// ---------------------------------------------------------------- tools
const T: Record<string, { description: string; role: keyof typeof RANK; schema: any; run: (a: any, actor: Actor) => Promise<unknown> }> = {
  whoami: { description: "Who this key belongs to and what it may do.", role: "viewer", schema: {}, run: async (_a, actor) => ({ ...actor, can_send: actor.role === "sy" }) },

  get_overview: {
    description: "North-star dashboard: last 30 days and month-to-date sales, new vs repeat orders, first-order AOV, Meta spend and CAC (7 and 30 days), run-rate vs $100k/month.",
    role: "viewer", schema: {},
    run: async () => {
      const { os, asOf } = await profiles(); const t = asOf;
      const l30 = E.sumPeriod(os, E.addDays(t, -29), t), mtd = E.sumPeriod(os, t.slice(0, 8) + "01", t);
      const meta = (await db.from("meta_daily").select("*").gte("day", E.addDays(t, -29))).data || [];
      const win = (d: number) => { const xs = meta.filter((r: any) => String(r.day) >= E.addDays(t, -(d - 1))); const spend = xs.reduce((a: number, r: any) => a + +r.spend, 0), n = xs.reduce((a: number, r: any) => a + (+r.new_customers || 0), 0); return { spend: +spend.toFixed(2), new_customers: n, cac: n ? +(spend / n).toFixed(2) : null }; };
      const w7 = win(7), w30 = win(30), run = l30.gross / 30 * 30.44;
      return { orders_through: asOf, last_30_days: l30, month_to_date: mtd, run_rate_per_month: Math.round(run), gap_to_100k: Math.max(0, Math.round(E.NS - run)),
        meta: { last_7_days: w7, last_30_days: w30, cac_target: E.CAC, cut_above: E.CAC_CUT, verdict: w7.cac == null ? "no data" : w7.cac <= E.CAC ? "scale +30%" : w7.cac <= E.CAC_CUT ? "hold" : "cut one budget step" },
        rules: ["Sy approves every send", "≤3 marketing emails per person per 30 days", "never Omnisend + Gmail marketing the same week", "subscribed contacts only", "never change Shopify"] };
    },
  },

  list_audiences: {
    description: "All 13 audiences (lifecycle groups) with size, subscribed count, rule, the email offer, the auto-picked Omnisend template and the next planned send date.",
    role: "viewer", schema: {},
    run: async () => {
      const { ps } = await profiles(); const out = [];
      for (const k of E.SEG_ORDER) { const xs = ps.filter((p) => p.audience === k);
        out.push({ audience: k, label: E.SEG_LABEL[k], people: xs.length, subscribed: xs.filter((p) => p.consent === "subscribed").length, rule: E.SEG_RULE[k], offer: E.OFFER[k] || null,
          template: E.TEMPLATE[k] ? { id: E.TEMPLATE[k][0], name: E.TEMPLATE[k][1] } : E.GMAIL_ONLY.includes(k) ? "personal Gmail note" : null, next_send: E.nextSend(k, await sentDates(k)) }); }
      return out;
    },
  },

  search_customers: {
    description: "Find customers (profiles) by name/email/order number, audience, consent or sock size. Returns orders, LTV net, LTV profit after $70 CAC, last order and audience.",
    role: "viewer",
    schema: { query: { type: "string" }, audience: { type: "string", enum: E.SEG_ORDER }, consent: { type: "string", enum: ["subscribed", "unsubscribed", "unknown"] }, size: { type: "string", enum: ["9-11", "10-13", "13-15"] }, sort: { type: "string", enum: ["ltv", "recent", "since"] }, limit: { type: "integer", maximum: 200 } },
    run: async (a) => {
      const { ps } = await profiles(); const q = String(a.query || "").toLowerCase();
      let xs = ps.filter((p) => (!a.audience || p.audience === a.audience) && (!a.consent || p.consent === a.consent) && (!a.size || p.size === a.size) && (!q || p.email.includes(q) || p.name.toLowerCase().includes(q)));
      const key: Record<string, (p: E.Profile) => number> = { ltv: (p) => -p.ltv_net, recent: (p) => p.days_since ?? 9999, since: (p) => -(p.days_since ?? 0) };
      xs = xs.sort((x, y) => key[a.sort || "ltv"](x) - key[a.sort || "ltv"](y));
      return { total: xs.length, customers: xs.slice(0, a.limit || 50) };
    },
  },

  get_customer: {
    description: "One customer's full profile and order timeline (first order to latest), audience and next move.", role: "viewer",
    schema: { email: { type: "string" } }, required: ["email"],
    run: async (a) => {
      const email = String(a.email).toLowerCase(); const { ps } = await profiles(); const p = ps.find((x) => x.email === email); if (!p) throw new Error("No customer with that email.");
      const orders = (await db.from("orders").select("name,day,gross,discount,refund,pairs,skus,seq").eq("email", email).order("day")).data;
      return { ...p, next_move: { audience: E.SEG_LABEL[p.audience], offer: E.OFFER[p.audience] || null }, orders };
    },
  } as any,

  list_moves: {
    description: "The ranked 'do these next' list: Meta budget gate, audience sends with prepare/approve/send dates, and team tasks due this week.", role: "viewer", schema: {},
    run: async () => {
      const t = E.today(), wk = E.addDays(t, 7), { ps } = await profiles(), moves: any[] = [];
      const meta = (await db.from("meta_daily").select("*").gte("day", E.addDays(t, -7))).data || [];
      const spend = meta.reduce((a: number, r: any) => a + +r.spend, 0), n = meta.reduce((a: number, r: any) => a + (+r.new_customers || 0), 0), cac = n ? spend / n : null;
      if (meta.length && (cac == null || cac > E.CAC)) moves.push({ kind: "meta_budget", due: t, title: cac != null && cac <= E.CAC_CUT ? "Hold the Meta budget" : "Cut Meta one budget step", detail: `7-day CAC ${cac == null ? "n/a" : "$" + cac.toFixed(2)} vs $${E.CAC} target on $${spend.toFixed(0)} spend` });
      const camps = (await db.from("campaigns").select("audience,status,send_date").not("status", "in", "(sent,scheduled,canceled)")).data || [];
      for (const k of E.SEG_ORDER) { if (k === "recent" || k === "other") continue; const xs = ps.filter((p) => p.audience === k); if (!xs.length) continue;
        const ns = E.nextSend(k, await sentDates(k)); if (!ns || ns.date > E.addDays(t, 21)) continue;
        const prep = ns.date <= t ? t : E.addDays(ns.date, -2) < t ? t : E.addDays(ns.date, -2);
        moves.push({ kind: E.GMAIL_ONLY.includes(k) ? "gmail_notes" : "email", audience: k, title: E.SEG_LABEL[k], offer: E.OFFER[k], people: xs.length, subscribed: xs.filter((p) => p.consent === "subscribed").length,
          prepare_by: prep, sy_approves_by: ns.date <= t ? t : E.addDays(ns.date, -1), sends: ns.date, campaign_status: camps.find((c: any) => c.audience === k)?.status || "not started", due: prep }); }
      const tasks = (await db.from("tasks").select("*").neq("status", "done").lte("due", wk)).data || [];
      tasks.forEach((x: any) => moves.push({ kind: "task", id: x.id, title: x.title, owner: x.owner, due: x.due, needs_sy: x.needs_sy && !x.sy_ok }));
      return moves.sort((a, b) => String(a.due).localeCompare(String(b.due)));
    },
  },

  get_meta: { description: "Daily Meta spend with new Shopify customers and CAC.", role: "viewer", schema: { days: { type: "integer", maximum: 90 } },
    run: async (a) => (await db.from("meta_daily").select("*").gte("day", E.addDays(E.today(), -(a.days || 30))).order("day")).data },
  log_meta_day: { description: "Log one day of Meta spend (new customers are counted from Shopify first orders that day if omitted).", role: "member",
    schema: { day: { type: "string", format: "date" }, spend: { type: "number" }, purchases: { type: "integer" }, value: { type: "number" }, new_customers: { type: "integer" } }, required: ["day", "spend"],
    run: async (a, actor) => {
      let n = a.new_customers; if (n == null) { const { count } = await db.from("orders").select("id", { count: "exact", head: true }).eq("day", a.day).eq("seq", 1); n = count || 0; }
      await db.from("meta_daily").upsert({ day: a.day, spend: a.spend, purchases: a.purchases ?? null, value: a.value ?? null, new_customers: n, source: `logged by ${actor.name}`, updated_at: new Date().toISOString() });
      return { ok: true, new_customers: n, cac: n ? +(a.spend / n).toFixed(2) : null };
    } } as any,

  list_tasks: { description: "Team tasks (status todo/doing/blocked/done).", role: "viewer", schema: { status: { type: "string" } },
    run: async (a) => { let q = db.from("tasks").select("*").order("due"); if (a.status) q = q.eq("status", a.status); return (await q).data; } },
  create_task: { description: "Add a team task.", role: "member", schema: { title: { type: "string" }, owner: { type: "string" }, due: { type: "string", format: "date" }, needs_sy: { type: "boolean" }, note: { type: "string" } }, required: ["title"],
    run: async (a, actor) => (await db.from("tasks").insert({ title: a.title, owner: a.owner || actor.name, due: a.due || E.addDays(E.today(), 3), needs_sy: !!a.needs_sy, note: a.note || null, created_by: actor.name }).select().single()).data } as any,
  update_task: { description: "Change a task's status, note, due date or owner. Marking a needs-Sy task approved requires the sy role.", role: "member",
    schema: { id: { type: "string" }, status: { type: "string", enum: ["todo", "doing", "blocked", "done"] }, note: { type: "string" }, due: { type: "string" }, owner: { type: "string" }, sy_ok: { type: "boolean" } }, required: ["id"],
    run: async (a, actor) => {
      const patch: any = { updated_at: new Date().toISOString() }; for (const k of ["status", "note", "due", "owner"]) if (a[k] != null) patch[k] = a[k];
      if (a.sy_ok) { need(actor, "sy"); patch.sy_ok = true; patch.sy_ok_by = actor.name; }
      return (await db.from("tasks").update(patch).eq("id", a.id).select().single()).data;
    } } as any,

  add_comment: { description: "Leave a note on a move, audience, task or campaign (ref like 'audience:wave_a', 'task:<id>', 'campaign:<id>', 'general').", role: "viewer",
    schema: { ref: { type: "string" }, body: { type: "string" } }, required: ["ref", "body"], run: async (a, actor) => (await db.from("comments").insert({ ref: a.ref, body: a.body, author: actor.name }).select().single()).data } as any,
  list_comments: { description: "Notes on a ref (or all recent notes if ref is omitted).", role: "viewer", schema: { ref: { type: "string" }, limit: { type: "integer" } },
    run: async (a) => { let q = db.from("comments").select("*").order("created_at", { ascending: false }).limit(a.limit || 50); if (a.ref) q = q.eq("ref", a.ref); return (await q).data; } },

  draft_email: { description: "Save an email draft (HTML) for an audience. Must include a working unsubscribe link [[unsubscribe_link]], only offers that exist in Shopify, and no % codes except COMEBACK15 for dormant.", role: "member",
    schema: { audience: { type: "string", enum: E.SEG_ORDER }, subject: { type: "string" }, preheader: { type: "string" }, body_html: { type: "string" } }, required: ["audience", "subject", "body_html"],
    run: async (a, actor) => {
      if (!String(a.body_html).includes("[[unsubscribe_link]]")) throw new Error("Add an unsubscribe link: <a href=\"[[unsubscribe_link]]\">Unsubscribe</a>.");
      return (await db.from("email_drafts").insert({ audience: a.audience, subject: a.subject, preheader: a.preheader || null, body_html: a.body_html, author: actor.name }).select("id,audience,subject,status,created_at").single()).data;
    } } as any,
  list_email_drafts: { description: "Email drafts written by the team or bots.", role: "viewer", schema: { audience: { type: "string" } },
    run: async (a) => { let q = db.from("email_drafts").select("id,audience,subject,preheader,author,status,omnisend_template_id,created_at").order("created_at", { ascending: false }); if (a.audience) q = q.eq("audience", a.audience); return (await q).data; } },
  publish_draft_as_template: { description: "Turn an email draft into an Omnisend template named 'CF · <audience> · <date>'. The CDP then auto-picks it for that audience.", role: "member",
    schema: { draft_id: { type: "string" } }, required: ["draft_id"],
    run: async (a) => {
      const { data: d } = await db.from("email_drafts").select("*").eq("id", a.draft_id).single(); if (!d) throw new Error("Draft not found.");
      await omniBrandCheck();
      const code = (E.TEMPLATE[d.audience]?.[1] || "").split(" · ")[1] || d.audience;
      const t = await omni("POST", "/email-templates/import", { name: `CF · ${code} · ${E.today()}`, html: d.body_html });
      await db.from("email_drafts").update({ status: "template", omnisend_template_id: t.id, updated_at: new Date().toISOString() }).eq("id", d.id);
      return { template_id: t.id, name: t.name };
    } } as any,

  list_campaigns: { description: "CDP campaigns and their status (new → tagged → segment → draft → tested → approved → sent/scheduled).", role: "viewer", schema: {},
    run: async () => (await db.from("campaigns").select("id,audience,status,subject,send_date,send_time,listed,sy_ok,sy_ok_by,omnisend_campaign_id,created_by,created_at,sent_at").order("created_at", { ascending: false }).limit(50)).data },

  prepare_campaign: {
    description: "One step to get an audience ready for Sy: tags the audience's subscribed customers in Omnisend, builds a subscribed-only segment, creates the campaign draft from the audience's template (scheduled for the next planned send date 10:00 Chicago unless given), and sends a test email. Nothing reaches customers.",
    role: "member",
    schema: { audience: { type: "string", enum: E.SEG_ORDER }, template_id: { type: "string" }, subject: { type: "string" }, preheader: { type: "string" }, send_date: { type: "string", format: "date" }, send_time: { type: "string", description: "HH:MM, America/Chicago" }, test_to: { type: "string", description: "comma-separated emails; default brand@comfortfresh.shop" } },
    required: ["audience"],
    run: async (a, actor) => {
      const k = a.audience; if (E.GMAIL_ONLY.includes(k) || k === "recent" || k === "other") throw new Error(`${E.SEG_LABEL[k]} doesn't get Omnisend campaigns.`);
      const tpl = a.template_id || E.TEMPLATE[k]?.[0]; if (!tpl) throw new Error("No template for this audience. Draft one with draft_email + publish_draft_as_template.");
      await omniBrandCheck();
      const { ps } = await profiles(); const emails = ps.filter((p) => p.audience === k).map((p) => p.email);
      const ns = E.nextSend(k, await sentDates(k)), date = a.send_date || (ns && ns.date > E.today() ? ns.date : E.today()), time = a.send_time || "10:00";
      const cap = E.capCheck(k, date, "Omnisend", ((await db.from("sends").select("audience,day,channel,name")).data || []).map((s: any) => ({ ...s, day: String(s.day) })));
      if (!cap.ok) throw new Error(`Email cap would be broken on ${date}: ${cap.conflict || "email #" + cap.email_number_in_30_days + " in 30 days"}. Pick another date.`);
      const { data: c } = await db.from("campaigns").insert({ audience: k, status: "new", created_by: actor.name, template_id: tpl, send_date: date, send_time: time, listed: emails.length, log: `${new Date().toISOString()} · prepared by ${actor.name}` }).select().single();
      const tag = `cf-${k.replace(/_/g, "-")}-${E.today().replace(/-/g, "")}`;
      for (let i = 0; i < emails.length; i += 250) await omni("POST", "/contacts/tags", { emails: emails.slice(i, i + 250), tags: [tag] });
      await db.from("campaigns").update({ status: "tagged", tag }).eq("id", c.id); await log(c.id, `tagged ${emails.length} with ${tag}`);
      const seg = await omni("POST", "/segments", { name: `CF · ${E.SEG_LABEL[k]} · ${E.today()}`.slice(0, 250), conditionGroups: [{ conditions: [{ entity: "contact", junction: "and", filters: [
        { operator: "anyOf", property: "tags", value: [tag] }, { channels: ["email"], operator: "equals", property: "subscriptionStatus", value: "subscribed" }] }] }] });
      const segId = seg.segmentID || seg.id; await db.from("campaigns").update({ status: "segment", segment_id: segId }).eq("id", c.id); await log(c.id, `segment ${segId}`);
      const when = chicagoToUtc(date, time), future = when.getTime() > Date.now() + 5 * 60000;
      const subject = a.subject || E.SUBJECT[k] || "From Comfort Fresh";
      const camp = await omni("POST", "/campaigns", { name: `CF · ${E.SEG_LABEL[k]} · ${date}`.slice(0, 250), type: "regular", channel: "email",
        content: { email: { subject, senderName: "Comfort Fresh", templateID: tpl, ...(a.preheader ? { preheader: a.preheader } : {}) } },
        audience: { includedSegmentIDs: [segId] }, sendingSettings: future ? { strategy: "scheduled", scheduledAt: when.toISOString() } : { strategy: "immediate" } });
      await db.from("campaigns").update({ status: "draft", omnisend_campaign_id: camp.id, subject, preheader: a.preheader || null }).eq("id", c.id); await log(c.id, `draft ${camp.id}`);
      const to = String(a.test_to || "brand@comfortfresh.shop").split(/[,\s]+/).filter(Boolean).slice(0, 5);
      await omni("POST", `/campaigns/${camp.id}/test-email`, { recipients: to });
      await db.from("campaigns").update({ status: "tested" }).eq("id", c.id); await log(c.id, `test sent to ${to.join(", ")}`);
      return { campaign_id: c.id, omnisend_campaign_id: camp.id, audience: k, listed: emails.length, send_date: date, send_time: `${time} America/Chicago`, test_sent_to: to, next: "Sy reviews the test, then approve_campaign + send_campaign (Sy's key)." };
    },
  } as any,

  approve_campaign: { description: "Sy's OK for a tested campaign.", role: "sy", schema: { campaign_id: { type: "string" } }, required: ["campaign_id"],
    run: async (a, actor) => { const { data: c } = await db.from("campaigns").select("*").eq("id", a.campaign_id).single(); if (!c) throw new Error("Campaign not found.");
      if (c.status !== "tested") throw new Error(`Campaign is "${c.status}"; it must be tested first.`);
      await db.from("campaigns").update({ status: "approved", sy_ok: true, sy_ok_by: actor.name, sy_ok_at: new Date().toISOString() }).eq("id", c.id); await log(c.id, `approved by ${actor.name}`);
      return { ok: true }; } } as any,

  send_campaign: { description: "Send or schedule an approved campaign in Omnisend. Irreversible. Requires Sy's key, confirm='SEND', and passes the email caps.", role: "sy",
    schema: { campaign_id: { type: "string" }, confirm: { type: "string", description: "must be SEND" } }, required: ["campaign_id", "confirm"],
    run: async (a, actor) => {
      if (a.confirm !== "SEND") throw new Error("Set confirm to SEND.");
      const { data: c } = await db.from("campaigns").select("*").eq("id", a.campaign_id).single(); if (!c) throw new Error("Campaign not found.");
      if (!c.sy_ok || c.status !== "approved") throw new Error("Needs approve_campaign first.");
      const cap = E.capCheck(c.audience, String(c.send_date), "Omnisend", ((await db.from("sends").select("audience,day,channel,name")).data || []).map((s: any) => ({ ...s, day: String(s.day) })));
      if (!cap.ok) throw new Error(`Blocked by the email cap: ${cap.conflict || "email #" + cap.email_number_in_30_days + " in 30 days"}.`);
      await omniBrandCheck();
      const cur = await omni("GET", `/campaigns/${c.omnisend_campaign_id}`); if (cur?.status && cur.status !== "draft") throw new Error(`Omnisend shows "${cur.status}", so it can't be sent again.`);
      await omni("POST", `/campaigns/${c.omnisend_campaign_id}/send`);
      const after = await omni("GET", `/campaigns/${c.omnisend_campaign_id}`).catch(() => null); const st = after?.status === "scheduled" ? "scheduled" : "sent";
      await db.from("campaigns").update({ status: st, sent_at: new Date().toISOString(), sent_by: actor.name }).eq("id", c.id); await log(c.id, `send called by ${actor.name}; Omnisend ${after?.status}`);
      await db.from("sends").insert({ audience: c.audience, day: c.send_date, channel: "Omnisend", name: c.subject, by: actor.name, campaign_id: c.id });
      return { status: st, omnisend_status: after?.status || null };
    } } as any,

  list_activity: { description: "Recent actions by people and bots (who did what, when, and whether it worked).", role: "viewer", schema: { limit: { type: "integer", maximum: 200 }, actor: { type: "string" } },
    run: async (a) => { let q = db.from("audit").select("at,actor,tool,ok,result").order("at", { ascending: false }).limit(a.limit || 40); if (a.actor) q = q.eq("actor", a.actor); return (await q).data; } },
  server_status: { description: "Is the CDP server in sync? Last Shopify and Omnisend sync, row counts, which secrets are set.", role: "viewer", schema: {},
    run: async () => {
      const st = Object.fromEntries((((await db.from("settings").select("k,v").in("k", ["last_sync", "consent_sync", "shopify_cursor"])).data) || []).map((r: any) => [r.k, r.v]));
      const n = async (t: string) => (await db.from(t).select("*", { count: "exact", head: true })).count || 0;
      return { last_sync: st.last_sync || null, consent_sync: st.consent_sync || null, orders_since: st.shopify_cursor?.since || null,
        counts: { customers: await n("customers"), orders: await n("orders"), tasks: await n("tasks"), comments: await n("comments"), campaigns: await n("campaigns"), email_drafts: await n("email_drafts") },
        secrets: { shopify: !!Deno.env.get("SHOPIFY_ADMIN_TOKEN"), omnisend: !!Deno.env.get("OMNISEND_API_KEY") } };
    } },
  sync_now: { description: "Pull new Shopify orders and refresh Omnisend email consent now (also runs hourly).", role: "member", schema: {},
    run: async () => { const out: any = {}; try { out.shopify = await syncShopify(); } catch (e) { out.shopify_error = String((e as Error).message); } try { out.consent = await syncConsent(); } catch (e) { out.consent_error = String((e as Error).message); } return out; } },
};

const READS = new Set(["whoami", "get_overview", "list_audiences", "search_customers", "get_customer", "list_moves", "get_meta", "list_tasks", "list_comments", "list_email_drafts", "list_campaigns", "list_activity", "server_status"]);
const toolList = () => Object.entries(T).map(([name, t]) => ({ name, description: t.description + ` [role: ${t.role}]`, annotations: { readOnlyHint: READS.has(name), destructiveHint: name === "send_campaign" },
  inputSchema: { type: "object", properties: t.schema, ...((t as any).required ? { required: (t as any).required } : {}) } }));

async function actorFor(req: Request): Promise<Actor | null> {
  const h = req.headers.get("authorization") || "";
  const key = (h.replace(/^Bearer\s+/i, "").trim() || new URL(req.url).searchParams.get("key") || "").trim(); if (!key) return null;
  const { data } = await db.from("api_keys").select("name,role,active").eq("key_hash", await sha256(key)).maybeSingle();
  return data && data.active ? { name: data.name, role: data.role } : null;
}
const J = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" } });

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, content-type, mcp-session-id, mcp-protocol-version", "Access-Control-Allow-Methods": "POST, GET, OPTIONS" } });
  if (req.method !== "POST") return new Response("Comfort Fresh CDP MCP server: POST JSON-RPC with Authorization: Bearer <key>", { status: 405, headers: { Allow: "POST, OPTIONS" } });
  const actor = await actorFor(req);
  if (!actor) return J({ jsonrpc: "2.0", id: null, error: { code: -32001, message: "Missing or invalid CDP key (Authorization: Bearer <key>)." } }, 401);
  let msg: any; try { msg = await req.json(); } catch { return J({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } }, 400); }
  const handle = async (m: any) => {
    if (m.id === undefined) return null; // notification
    if (m.method === "initialize") return { jsonrpc: "2.0", id: m.id, result: { protocolVersion: m.params?.protocolVersion || "2025-03-26", capabilities: { tools: { listChanged: false } }, serverInfo: { name: "comfort-fresh-cdp", version: "1.0.0" },
      instructions: "Comfort Fresh CDP. Start with get_overview and list_moves. Prepare emails with prepare_campaign; only Sy's key can approve_campaign and send_campaign. Never invent offers: use the audience offer from list_audiences." } };
    if (m.method === "ping") return { jsonrpc: "2.0", id: m.id, result: {} };
    if (m.method === "tools/list") return { jsonrpc: "2.0", id: m.id, result: { tools: toolList() } };
    if (m.method === "tools/call") {
      const name = m.params?.name, args = m.params?.arguments || {}, t = T[name];
      if (!t) return { jsonrpc: "2.0", id: m.id, error: { code: -32602, message: `Unknown tool ${name}` } };
      try { need(actor, t.role); const out = await t.run(args, actor);
        // Log every action and every customer-data lookup; plain dashboard reads are not logged.
        if (!READS.has(name) || name === "search_customers" || name === "get_customer") await db.from("audit").insert({ actor: actor.name, tool: name, args, ok: true, result: JSON.stringify(out).slice(0, 500) });
        return { jsonrpc: "2.0", id: m.id, result: { content: [{ type: "text", text: JSON.stringify(out) }] } };
      } catch (e) { const msg = (e as Error).message; await db.from("audit").insert({ actor: actor.name, tool: name, args, ok: false, result: msg });
        return { jsonrpc: "2.0", id: m.id, result: { isError: true, content: [{ type: "text", text: msg }] } }; }
    }
    return { jsonrpc: "2.0", id: m.id, error: { code: -32601, message: `Method not found: ${m.method}` } };
  };
  if (Array.isArray(msg)) { const out = (await Promise.all(msg.map(handle))).filter(Boolean); return out.length ? J(out) : new Response(null, { status: 202 }); }
  const out = await handle(msg); return out ? J(out) : new Response(null, { status: 202 });
});
