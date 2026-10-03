"""The log → gates → one row per key → one email a day (plan.md §7, Phase 2).

    python src/digest.py            build it and send it
    python src/digest.py --dry-run  print it, send nothing

It sends every day, changed or not (§4): a missing email is then itself the
failure signal, alongside the coverage block.

Credentials and the recipient are read from the environment and from nowhere
else, because config/*.yaml is committed (config/digest.yaml lists the names).
A git-ignored `.env` in the project root is loaded for local runs; real
environment variables always win over it (src/dotenv_lite.py).
"""

import html
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage

import yaml

import changes
import coverage
import dotenv_lite
import ranking
from ranking import describe_key, money

SMTP_USER = "IPAD_SMTP_USER"
SMTP_PASS = "IPAD_SMTP_PASS"
DIGEST_TO = "IPAD_DIGEST_TO"

WIDTH = 64


def load_settings():
    return yaml.safe_load((ranking.CONFIG / "digest.yaml").read_text(encoding="utf-8"))


# ── The body ─────────────────────────────────────────────────────────────────

def build(config, settings, observations, now):
    """(subject, body). Pure: everything it reads is passed in."""
    gated = ranking.gate(config, ranking.latest_poll(observations))
    within, over = ranking.split_budget(config, ranking.best_per_key(gated.candidates))
    references = ranking.new_references(config, observations, now)
    moved, first = changes.since(config, observations, now, settings["changes_window_hours"])
    covered = coverage.measure(config, observations, now, settings["coverage"])

    lines = [f"iPad Digest — {_day(now)}    "
             f"(Pencil Pro {money(config.rules['pencil_cost'])} included in every price)", ""]
    lines += _changes_block(config, moved, first)
    lines += _ranked_block(config, f"within budget ({money(config.rules['budget'])})",
                           within, references)
    lines += _ranked_block(config, "over budget", over, references)
    lines += _held_block(config, gated.held)
    lines += _coverage_block(config, settings["coverage"], covered, gated.dismissed)
    return f"{settings['subject']} — {_day(now)}", "\n".join(lines)


def _heading(title):
    return f"── {title} " + "─" * max(3, WIDTH - len(title) - 4)


def _changes_block(config, moved, first):
    """Changes first: they are why today's email differs from yesterday's (§7)."""
    lines = [_heading("changed since yesterday")]
    for source in first:
        lines.append(f"  first day of {config.short_name(source)} in the log: "
                     f"everything from it is new")
    order = {changes.NEW: 0, changes.PRICE: 1, changes.STOCK: 2, changes.GONE: 3}
    for change in sorted(moved, key=lambda ch: (order[ch.kind], ch.candidate.effective_price)):
        lines.append("  " + _change_line(config, change))
    if not moved and not first:
        lines.append("  nothing changed")
    return lines + [""]


def _change_line(config, change):
    c = change.candidate
    what = f"{describe_key(c.resolved.key):<20}  {config.short_name(c.observation['source']):<13}"
    if change.kind == changes.NEW:
        return (f"+ NEW   {what}  {c.observation['condition_raw']}  "
                f"{money(c.price)} ({money(c.effective_price)} eff.)")
    if change.kind == changes.PRICE:
        arrow = "↓ DROP" if c.price < change.was else "↑ RISE"
        return f"{arrow}  {what}  {money(change.was)} → {money(c.price)}"
    if change.kind == changes.STOCK:
        state = "back in stock" if c.observation["in_stock"] else "out of stock"
        return f"! STOCK {what}  {state}"
    return f"− GONE  {what}  {money(c.price)}  ({_listed(change.listed_hours)})"


def _listed(hours):
    if hours == 0:
        return "seen in one poll"
    return f"listed ~{hours:.0f}h" if hours < 48 else f"listed ~{hours / 24:.0f}d"


def _ranked_block(config, title, rows, references):
    """One row per key, cheapest first; the other listings are a count (§7)."""
    lines = [_heading(title)]
    for best, others in rows:
        o, resolved = best.observation, best.resolved
        details = [config.short_name(o["source"]), o["condition_raw"]]
        if resolved.connectivity == "cellular":
            details.append("cellular")
        more = f"   +{others} more" if others else ""
        lines.append(f"  {money(best.effective_price):>7}  {describe_key(resolved.key):<20} "
                     f"{resolved.ram_gb:>2}GB   {' · '.join(details)}{more}")
        lines.append(f"           {money(best.price)} listed · {_reference(config, best, references)}")
        lines.append(f"           {o['url']}")
    if not rows:
        lines.append("  none")
    return lines + [""]


def _reference(config, candidate, references):
    """The "is it cheap for what it is?" test (§2)."""
    reference = references.get(candidate.resolved.key)
    if reference is None:
        return "new ref: —"
    price, source = reference
    text = f"new ref: {money(price)} ({config.short_name(source)})"
    if candidate.observation["condition_raw"] == "new" and candidate.price == price:
        return text + " — this is it"
    if candidate.price >= price:
        return text + " — not below new"
    return text + f" — {money(price - candidate.price)} below new"


def _held_block(config, held):
    """Where the parser and the condition table admit what they don't know (§7)."""
    lines = [_heading(f"held for review ({len(held)})")]
    for o, reason in held:
        lines.append(f'  ?  {reason}: "{o["title"]}" ({config.short_name(o["source"])})')
    return lines + [""]


def _coverage_block(config, settings, covered, dismissed):
    lines = [_heading(f"coverage (last {settings['days']} days)")]
    polled = [c for c in covered if c.last is not None]
    if polled:
        lines.append("  " + " · ".join(f"{config.short_name(c.source)} {c.polls}/{c.expected} polls"
                                       for c in polled))
    for c in covered:
        if c.last is None:
            lines.append(f"  ⚠ {config.short_name(c.source)}: never polled")
        elif c.stale_hours is not None:
            lines.append(f"  ⚠ {config.short_name(c.source)}: last poll {c.stale_hours:.0f}h ago "
                         f"({c.last}) — its rows above are that old")
    if any(c.stale_hours is not None for c in covered):
        lines.append("  GitHub disables scheduled workflows after 60 days of repo inactivity;"
                     " check the Actions tab.")
    if dismissed:
        lines.append("  dismissed quietly: " + ", ".join(f"{n} {why}" for why, n in sorted(dismissed.items())))
    return lines


def _day(now):
    return f"{now:%b} {now.day}"


# ── Sending ──────────────────────────────────────────────────────────────────

def credentials():
    """(user, password), or exit naming what is missing. Exiting here rather
    than at SMTP auth matters: Gmail answers a missing password with a generic
    authentication failure, which reads like a wrong password."""
    user, password = os.environ.get(SMTP_USER), os.environ.get(SMTP_PASS)
    missing = [name for name, value in ((SMTP_USER, user), (SMTP_PASS, password)) if not value]
    if missing:
        raise SystemExit(f"{' and '.join(missing)} not set — see config/digest.yaml.")
    return user, password


def recipient():
    address = os.environ.get(DIGEST_TO)
    if not address:
        raise SystemExit(f"{DIGEST_TO} not set — see config/digest.yaml.")
    return address


def build_message(subject, body, sender, to):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to
    message.set_content(body)
    # The rows are aligned columns, and Gmail shows plain text in a
    # proportional font. The HTML part is the same text, kept monospaced.
    message.add_alternative(
        f'<pre style="font-family: Consolas, Menlo, monospace; font-size: 13px">'
        f"{html.escape(body)}</pre>", subtype="html")
    return message


def send(message, user, password, smtp):
    """Deliver, or exit non-zero with a line saying which step failed."""
    try:
        with smtplib.SMTP(smtp["host"], smtp["port"], timeout=30) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(message)
    except smtplib.SMTPAuthenticationError:
        # Never echo the password, not even its length.
        raise SystemExit(
            f"SMTP rejected the login for {user}. {SMTP_PASS} must be a 16-character "
            f"Google App Password, not the account password, and the account needs "
            f"2-Step Verification enabled for one to be issued.")
    except (smtplib.SMTPException, OSError) as error:
        # Gmail answers an unknown account by dropping the connection rather
        # than with an auth error, so a credentials problem can land here too.
        raise SystemExit(
            f"Could not send via {smtp['host']}:{smtp['port']} — {type(error).__name__}: "
            f"{error}\nIf the network is fine, check {SMTP_USER} and {SMTP_PASS}.")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    # An unrecognised flag is an error: the workflow builds the arguments, and
    # a flag that silently did nothing would look like a normal run.
    unknown = [a for a in argv if a != "--dry-run"]
    if unknown:
        raise SystemExit(f"Unknown argument(s): {' '.join(unknown)}. The only flag is --dry-run.")

    if dotenv_lite.load(ranking.ROOT / ".env"):
        print("Loaded .env")
    config, settings = ranking.Config(), load_settings()
    subject, body = build(config, settings, ranking.load_observations(), datetime.now(timezone.utc))

    if "--dry-run" in argv:
        # Needs neither credentials nor a recipient: --dry-run has to work on a
        # machine where they were never set.
        sys.stdout.reconfigure(encoding="utf-8")   # a piped Windows stdout is cp1252
        print(f"{subject}\n\n{body}")
        return 0

    user, password = credentials()
    to = recipient()
    send(build_message(subject, body, user, to), user, password, settings["smtp"])
    print(f"Sent: {subject}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
