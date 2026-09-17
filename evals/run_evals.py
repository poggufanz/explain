#!/usr/bin/env python3
"""Minimal eval driver for the `explain` skill.

What it does (and deliberately does not do)
------------------------------------------
* Builds simple git fixture repositories (`fixtures/repos/*`) that reproduce the
  working-tree situations the skill must handle, and captures their real ground
  truth (`git status --porcelain -uall`, `git diff HEAD`, `git log`,
  `git show --stat`, file contents, unborn-HEAD flag).
* Runs one fresh-context model sample per scenario, system prompt = SKILL.md,
  user prompt = the captured fixture state + the scenario's user message.
* Grades each sample with a single rubric call over the REAL transcript.
  There is no regex re-implementation of the skill's behavior here.
* Writes `results/<run>.json` containing, per sample: model id, skill sha256,
  fixture ground truth, the full prompt, the full output, and the rubric
  verdict. Nothing is fabricated: if a sample did not run, it is absent.

Honest limits, recorded in every result file:
* These are FIXTURE-CONTEXT SIMULATIONS, not tool-using agent runs. This harness
  cannot spawn tool-using subagents, so the model is handed the exact terminal
  output it would have produced. Tool execution is therefore not exercised.
* Native harness auto-discovery/auto-triggering is not exercised. Trigger
  queries are graded by a single-skill description proxy (see --triggers).

Standalone reproduction:
    EVAL_API_KEY=... EVAL_BASE_URL=https://api.openai.com/v1 EVAL_MODEL=gpt-4.1 \
    python run_evals.py --out results/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent  # <repo>/evals (this harness lives outside the skill dir)
SKILL_PATH = HERE.parent / "skills" / "explain" / "SKILL.md"
FIXTURE_ROOT = HERE / "fixtures" / "repos"
RESULTS_DIR = HERE / "results"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "eval", "GIT_AUTHOR_EMAIL": "eval@example.invalid",
    "GIT_COMMITTER_NAME": "eval", "GIT_COMMITTER_EMAIL": "eval@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_TERMINAL_PROMPT": "0",
}


def sh(cmd, cwd, check=True):
    env = {**os.environ, **GIT_ENV}
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, env=env)
    if check and p.returncode != 0:
        raise RuntimeError(f"{cmd} in {cwd} failed: {p.stderr.strip()}")
    return p.stdout.replace("\r\n", "\n")


# ---------------------------------------------------------------- fixtures ---

CART_BASE = """<?php
namespace App;
class Cart
{
    private array $items = [];
    public function addItem(int $itemId, int $qty, int $price): void
    {
        $this->items[] = ['item_id' => $itemId, 'qty' => $qty, 'price' => $price];
    }
    public function items(): array { return $this->items; }
    public function total(): int
    {
        $sum = 0;
        foreach ($this->items as $item) { $sum += $item['qty'] * $item['price']; }
        return $sum;
    }
}
"""
CART_IMPL = CART_BASE.replace(
    "public function addItem(int $itemId, int $qty, int $price): void",
    "public function addItem(int $itemId, int $qty, int $price, int $discount = 0): void").replace(
    "['item_id' => $itemId, 'qty' => $qty, 'price' => $price];",
    "['item_id' => $itemId, 'qty' => $qty, 'price' => $price, 'discount' => $discount];").replace(
    "$sum += $item['qty'] * $item['price'];",
    "$sum += $item['qty'] * $item['price'] - $item['discount'];")

CONTROLLER_BASE = """<?php
namespace App\\Http;
use App\\Cart;
class CartController
{
    public function __construct(private Cart $cart) {}
    public function store(array $request): array
    {
        $this->cart->addItem($request['item_id'], (int) $request['qty'], (int) $request['price']);
        return ['total' => $this->cart->total()];
    }
}
"""
CONTROLLER_IMPL = """<?php
namespace App\\Http;
use App\\Cart;
class CartController
{
    public function __construct(private Cart $cart) {}
    public function store(array $request): array
    {
        $discount = (int) ($request['discount_amount'] ?? 0);
        if ($discount > (int) config('cart.max_item_discount')) {
            throw new \\InvalidArgumentException('diskon melebihi batas');
        }
        $this->cart->addItem($request['item_id'], (int) $request['qty'], (int) $request['price'], $discount);
        return ['total' => $this->cart->total()];
    }
}
"""
MIGRATION_ADD = """<?php
// migrasi: tambah kolom discount_amount (nullable) ke cart_items
Schema::table('cart_items', function (Blueprint $table) {
    $table->integer('discount_amount')->nullable()->after('price');
});
"""

BASE = {
    "composer.json": '{"name":"example/shop","require-dev":{"phpunit/phpunit":"^10.5"},"scripts":{"test":"phpunit"}}\n',
    "app/Cart.php": CART_BASE,
    "app/Http/CartController.php": CONTROLLER_BASE,
    "app/Tax.php": "<?php\nnamespace App;\nclass Tax\n{\n    public static function forCart(Cart $cart): int\n    {\n        return (int) round($cart->total() * 0.11);\n    }\n}\n",
    "app/Invoice/InvoiceService.php": "<?php\nnamespace App\\Invoice;\nuse App\\Cart;\nuse App\\Tax;\nclass InvoiceService\n{\n    public function draftFor(Cart $cart): array\n    {\n        return ['netto' => $cart->total(), 'tax' => Tax::forCart($cart)];\n    }\n}\n",
    "app/Support/Money.php": "<?php\nnamespace App\\Support;\nclass Money\n{\n    public static function format(int $amount): string\n    {\n        return number_format($amount / 100, 2, ',', '.');\n    }\n}\n",
    "app/Support/DiscountLegacy.php": "<?php\nnamespace App\\Support;\nclass DiscountLegacy\n{\n    public static function apply(int $total, int $percent): int\n    {\n        return (int) ($total - ($total * $percent / 100));\n    }\n}\n",
    "database/migrations/2026_01_10_000000_create_cart_items_table.php": "<?php\n// tabel cart_items: id, cart_id, item_id, qty, price, timestamps\nSchema::create('cart_items', function (Blueprint $table) {\n    $table->id();\n    $table->integer('cart_id');\n    $table->integer('item_id');\n    $table->integer('qty');\n    $table->integer('price');\n    $table->timestamps();\n});\n",
    "config/cart.php": "<?php\nreturn ['max_item_discount' => env('MAX_ITEM_DISCOUNT', 0)];\n",
    "routes/web.php": "<?php\nuse App\\Http\\CartController;\nRoute::post('/cart', [CartController::class, 'store']);\n",
    "docs/runbooks/release.md": "# Release checklist\n\n1. `composer install --no-dev`\n2. `php artisan migrate --force`\n",
}

SPEC_DISCOUNT = """# Spec: Diskon per item

1. `cart_items.discount_amount` (nullable, integer) ditambahkan lewat migrasi.
2. `Cart::addItem()` menerima `discount_amount` opsional; validasi menolak nilai di atas `MAX_ITEM_DISCOUNT`.
3. `Cart::total()` menghitung netto = sum(qty*price) - sum(discount).
4. `Tax::forCart()` memakai total netto; invoice memakai netto baru.
5. Batas diskon dibaca dari env `MAX_ITEM_DISCOUNT`.
6. Operator menjalankan `php artisan migrate` sebelum rilis.
"""
SPEC_REAP = """# Spec: Reap keranjang menganggur

1. Keranjang open > 72 jam diubah menjadi cancelled oleh command `carts:reap`.
2. Command dijadwalkan tiap jam lewat scheduler.
3. Tim support menandai tiket terkait 'auto-cancelled' (langkah manual, di luar CLI).
4. Tidak ada perubahan harga, tagihan, akses, atau route publik.
"""
SPEC_LOGIN = """# Spec: Ubah alur login

1. Login memakai magic link selain password.
2. Rate limit 5 percobaan per menit per email.
"""
PLAN_UNAPPROVED = """# Plan: Diskon per item (belum disetujui)

1. Tambah kolom `discount_amount` nullable di `cart_items`.
2. Ubah signature `Cart::addItem(int,int,int)` -> tambah `int $discount = 0`.
3. Tambah validasi `$discount <= config('cart.max_item_discount')`.
4. Ubah `Cart::total()` menjadi netto.
"""
SPEC_PHPUNIT = "# Spec: bump phpunit\n\n1. phpunit 10 -> 11.\n2. Rename helper `Money::format` -> `Money::display`.\n"

IMPL = {
    "app/Cart.php": CART_IMPL,
    "app/Http/CartController.php": CONTROLLER_IMPL,
    "database/migrations/2026_02_01_000000_add_discount_to_cart_items.php": MIGRATION_ADD,
    "config/cart.php": "<?php\nreturn ['max_item_discount' => env('MAX_ITEM_DISCOUNT', 5000)];\n",
}
FEATURE = list(IMPL)

PRICING = "<?php\nnamespace App\\Pricing;\nclass PricingRule\n{\n    public function discountFor(int $itemId, int $qty): int\n    {\n        return DB::table('item_promos')->where('item_id', $itemId)->value('discount') ?? 0;\n    }\n}\n"
EXPORT = "<?php\nnamespace App\\Jobs;\nclass ExportOrderSummary\n{\n    public function handle(Cart $cart): void\n    {\n        Storage::put('exports/'.time().'.csv', (string) $cart->total());\n    }\n}\n"
API_ROUTE = "<?php\nuse App\\Http\\CartController;\n\n// dikonsumsi aplikasi mobile (repo terpisah)\nRoute::get('/api/cart', [CartController::class, 'show']);\n"
SERVICES = "<?php\nreturn ['payments' => ['webhook_secret' => env('PAYMENT_WEBHOOK_SECRET'), 'oauth_redirect' => env('PAYMENT_OAUTH_REDIRECT')]];\n"
WEBHOOK = "<?php\nnamespace App\\Payments;\nclass DiscountWebhook\n{\n    public function handle(array $payload): void\n    {\n        $this->verify($payload['signature'], config('services.payments.webhook_secret'));\n    }\n}\n"
PAY_RUNBOOK = "# Runbook pembayaran\n\n- Webhook URL: https://app.example.com/webhooks/payments (diatur di dashboard Stripe)\n- OAuth redirect URI: https://app.example.com/oauth/callback (dashboard Stripe)\n- DNS: pay.example.com CNAME ke edge.psp.example (dashboard registrar)\n"
REAP = {
    "app/CartReaper.php": "<?php\nnamespace App;\nclass CartReaper\n{\n    public function staleBefore(\\DateTimeImmutable $now): array\n    {\n        return DB::table('carts')->where('status', 'open')->where('updated_at', '<', $now->modify('-72 hours'))->pluck('id')->all();\n    }\n    public function reap(array $ids): int\n    {\n        return DB::table('carts')->whereIn('id', $ids)->update(['status' => 'cancelled']);\n    }\n}\n",
    "app/Console/Commands/ReapStaleCarts.php": "<?php\nnamespace App\\Console\\Commands;\nclass ReapStaleCarts extends Command\n{\n    protected $signature = 'carts:reap';\n    public function handle(CartReaper $reaper): int\n    {\n        $this->info('cancelled '.$reaper->reap($reaper->staleBefore(new \\DateTimeImmutable('now'))));\n        return self::SUCCESS;\n    }\n}\n",
    "routes/console.php": "<?php\nSchedule::command('carts:reap')->hourly();\n",
}
LOGIN = {
    "app/Auth/MagicLink.php": "<?php\nnamespace App\\Auth;\nclass MagicLink\n{\n    public function issue(string $email): string\n    {\n        return URL::temporarySignedRoute('login.magic', now()->addMinutes(15), ['email' => $email]);\n    }\n}\n",
    "app/Http/AuthController.php": "<?php\nnamespace App\\Http;\nclass AuthController\n{\n    public function login(array $request)\n    {\n        RateLimiter::hit('login:'.$request['email'], 60);\n        return MagicLink::issue($request['email']);\n    }\n}\n",
    "routes/web.php": "<?php\nuse App\\Http\\CartController;\nuse App\\Http\\AuthController;\nRoute::post('/cart', [CartController::class, 'store']);\nRoute::post('/login', [AuthController::class, 'login']);\n",
}
REFACTOR = {
    "app/Support/Money.php": "<?php\nnamespace App\\Support;\nclass Money\n{\n    public static function display(int $amount): string\n    {\n        return number_format($amount / 100, 2, ',', '.');\n    }\n}\n",
    "composer.json": '{"name":"example/shop","require-dev":{"phpunit/phpunit":"^11.0"},"scripts":{"test":"phpunit"}}\n',
}
LARGE = {**IMPL}
LARGE.update({
    "app/Http/Requests/DiscountRequest.php": "<?php\nclass DiscountRequest\n{\n    public function rules(): array { return ['discount_amount' => 'integer|min:0']; }\n}\n",
    "app/Services/DiscountService.php": "<?php\nclass DiscountService\n{\n    public function cap(): int { return (int) config('cart.max_item_discount'); }\n}\n",
    "app/Services/CartTotals.php": "<?php\nclass CartTotals\n{\n    public function netto(array $items): int { return array_sum(array_map(fn ($i) => $i['qty'] * $i['price'] - ($i['discount'] ?? 0), $items)); }\n}\n",
    "app/Repositories/CartRepository.php": "<?php\nclass CartRepository\n{\n    public function saveDiscount(int $id, int $discount): void { DB::table('cart_items')->where('id', $id)->update(['discount_amount' => $discount]); }\n}\n",
    "app/Http/Resources/CartResource.php": "<?php\nclass CartResource\n{\n    public function toArray(array $cart): array { return ['total' => $cart['total'], 'currency' => 'IDR']; }\n}\n",
    "app/Listeners/LogDiscountApplied.php": "<?php\nclass LogDiscountApplied\n{\n    public function handle(array $event): void { Log::info('discount applied', $event); }\n}\n",
    "app/Exceptions/DiscountCapExceeded.php": "<?php\nclass DiscountCapExceeded extends \\RuntimeException {}\n",
    "app/Console/Commands/BackfillDiscounts.php": "<?php\nclass BackfillDiscounts\n{\n    public function handle(): void { DB::table('cart_items')->whereNull('discount_amount')->update(['discount_amount' => 0]); }\n}\n",
    "resources/js/cart-discount.js": "export function renderDiscount(row) {\n  return `<span class=\"discount\">${row.discount_amount ?? 0}</span>`;\n}\n",
    "tests/Feature/DiscountTest.php": "<?php\ntest('total memakai netto', function () {\n    $c = new \\App\\Cart();\n    $c->addItem(1, 2, 1000, 500);\n    expect($c->total())->toBe(1500);\n});\n",
    "database/factories/CartItemFactory.php": "<?php\nclass CartItemFactory\n{\n    public function definition(): array { return ['qty' => 1, 'price' => 1000, 'discount_amount' => 0]; }\n}\n",
})

# name -> fixture spec.  mode: worktree | stage | commit | commit-two
#       | commit-plus-local | nodirgit | unborn
VARIANTS = {
    "b-committed-clean": dict(files=IMPL, mode="commit", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT),
    "b-committed-plus-local": dict(files={k: IMPL[k] for k in ("app/Cart.php", "database/migrations/2026_02_01_000000_add_discount_to_cart_items.php", "config/cart.php")},
                                   mode="commit-plus-local", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT,
                                   local={"app/Http/CartController.php": CONTROLLER_IMPL, "tests/Feature/DiscountTest.php": LARGE["tests/Feature/DiscountTest.php"]}),
    "b-staged": dict(files=IMPL, mode="stage", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT),
    "b-unstaged-untracked": dict(files=IMPL, mode="worktree", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT,
                                 extra_untracked={"scratch/notes.txt": "catatan lokal\n"}),
    "b-rename-delete": dict(files={**IMPL, "app/Support/BackendSupport/Money.php": BASE["app/Support/Money.php"]},
                            mode="stage", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT,
                            rename=[("app/Support/Money.php", "app/Support/BackendSupport/Money.php")],
                            delete=["app/Support/DiscountLegacy.php"]),
    "b-unrelated-changes": dict(files=IMPL, mode="worktree", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT,
                                unrelated={"app/Support/Money.php": BASE["app/Support/Money.php"].replace("$amount / 100", "$amount / 1000")},
                                extra_untracked={"tmp/debug.log": "noise\n"}),
    "a-spec-only": dict(files={}, mode="worktree", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT),
    "a-plan-unapproved": dict(files={}, mode="worktree", spec="docs/specs/discount-plan.md", spec_content=PLAN_UNAPPROVED),
    "b-nongit": dict(files=IMPL, mode="nodirgit", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT),
    "b-unborn-head": dict(files=IMPL, mode="unborn", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT),
    "b-ops-heavy": dict(files={**IMPL, "config/services.php": SERVICES, "app/Payments/DiscountWebhook.php": WEBHOOK, "docs/runbooks/payments.md": PAY_RUNBOOK},
                        mode="worktree", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT),
    "b-upstream-downstream": dict(files={**IMPL, "app/Pricing/PricingRule.php": PRICING, "app/Jobs/ExportOrderSummary.php": EXPORT},
                                  mode="worktree", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT),
    "b-business-process": dict(files=REAP, mode="worktree", spec="docs/specs/reap-stale-carts.md", spec_content=SPEC_REAP),
    "b-unknown-consumers": dict(files={**IMPL, "routes/api.php": API_ROUTE}, mode="worktree", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT),
    "b-large-scope": dict(files=LARGE, mode="worktree", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT),
    "b-refactor": dict(files=REFACTOR, mode="worktree", spec="docs/specs/phpunit-bump.md", spec_content=SPEC_PHPUNIT),
    "b-ambiguous-range": dict(files=IMPL, mode="commit-two", spec="docs/specs/item-discount.md", spec_content=SPEC_DISCOUNT,
                              second_commit={"composer.json": REFACTOR["composer.json"]}),
    "c-login-flow": dict(files=LOGIN, mode="worktree", spec="docs/specs/login-flow.md", spec_content=SPEC_LOGIN),
}


def _w(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def build_fixture(name, spec):
    root = FIXTURE_ROOT / name
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    files, mode = spec.get("files", {}), spec.get("mode", "worktree")
    spec_path, spec_text = spec.get("spec"), spec.get("spec_content", "")
    for rel, content in BASE.items():
        _w(root, rel, content)
    if mode == "nodirgit":
        for rel, c in files.items():
            _w(root, rel, c)
        if spec_path:
            _w(root, spec_path, spec_text)
        for rel, c in (spec.get("extra_untracked") or {}).items():
            _w(root, rel, c)
        return root
    if mode == "unborn":
        for rel, c in files.items():
            _w(root, rel, c)
        if spec_path:
            _w(root, spec_path, spec_text)
        sh(["git", "init", "-q", "-b", "main"], root)
        return root
    committed_modes = ("commit", "commit-two", "commit-plus-local")
    if spec_path and mode in committed_modes:
        _w(root, spec_path, spec_text)
    sh(["git", "init", "-q", "-b", "main"], root)
    sh(["git", "add", "-A"], root)
    sh(["git", "commit", "-qm", "chore: project base"], root)
    if spec_path and mode not in committed_modes:
        _w(root, spec_path, spec_text)
    for rel, c in files.items():
        _w(root, rel, c)
    if mode in committed_modes:
        sh(["git", "add", "-A"], root)
        sh(["git", "commit", "-qm", "feat: fitur yang baru selesai"], root)
    for rel, c in (spec.get("local") or {}).items():
        _w(root, rel, c)
    for rel, c in (spec.get("second_commit") or {}).items():
        _w(root, rel, c)
        sh(["git", "add", "-A"], root)
        sh(["git", "commit", "-qm", "chore: bump dependency"], root)
    for rel, c in (spec.get("unrelated") or {}).items():
        _w(root, rel, c)
    for rel, c in (spec.get("extra_untracked") or {}).items():
        _w(root, rel, c)
    for old, new in spec.get("rename") or []:
        old_p, new_p = root / old, root / new
        if new_p.exists() and old_p.exists():
            old_p.unlink()
        elif old_p.exists():
            new_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_p), str(new_p))
    for rel in spec.get("delete") or []:
        p = root / rel
        if p.exists():
            p.unlink()
    if mode in ("stage", "commit", "commit-two", "commit-plus-local"):
        sh(["git", "add", "-A"], root)
    return root


def capture(root: Path) -> dict:
    is_git = (root / ".git").exists()
    b = {"root": str(root), "is_git": is_git, "files": {}}
    if is_git:
        b["status"] = sh(["git", "status", "--porcelain", "-uall"], root)
        if sh(["git", "rev-parse", "--verify", "HEAD"], root, check=False).strip():
            b["diff_head"] = sh(["git", "diff", "HEAD"], root)
            b["log"] = sh(["git", "log", "--oneline", "--decorate", "-10"], root)
            b["show_stat"] = sh(["git", "show", "--stat", "--oneline", "HEAD"], root)
            b["unborn"] = False
        else:
            b.update(diff_head="", show_stat="", unborn=True,
                     log="(repo git tanpa commit: HEAD belum lahir)")
    else:
        b.update(status="", diff_head="", log="(bukan repo git)", show_stat="", unborn=False)
    for p in sorted(root.rglob("*")):
        if ".git" in p.parts or p.is_dir():
            continue
        rel = p.relative_to(root).as_posix()
        try:
            b["files"][rel] = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            b["files"][rel] = "<binary>"
    return b


# ------------------------------------------------------------------ prompts ---

HEADER = """You are a coding agent working inside a real repository on the machine below.
You have a shell, but the repository state has ALREADY been captured and is shown
verbatim below; treat it as the output of the commands you would have run.
"""


def render_prompt(bundle, turns):
    p = [HEADER, f"\nRepository root: {bundle['root']}\n"]
    p.append("\n### `git status --porcelain -uall`\n```\n" + (bundle["status"] or "(empty)") + "\n```\n")
    p.append("\n### `git log --oneline --decorate -10`\n```\n" + (bundle["log"] or "(empty)") + "\n```\n")
    p.append("\n### `git diff HEAD`\n```diff\n" + (bundle["diff_head"] or "(empty)") + "\n```\n")
    p.append("\n### `git show --stat HEAD`\n```\n" + (bundle["show_stat"] or "(empty)") + "\n```\n")
    p.append("\n### Repository files\n")
    for rel, content in bundle["files"].items():
        p.append(f"\n#### `{rel}`\n```\n{content}\n```\n")
    convo = "\n\n".join(f"<{t['role']}>\n{t['content']}\n</{t['role']}>" for t in turns)
    p.append("\n## Conversation so far\n\n" + convo)
    p.append("\n\n## Your turn\nWrite ONLY the next assistant message. Do not narrate the environment.\n")
    return "".join(p)


# --------------------------------------------------------------- execution ---

LIMITS = [
    "FIXTURE-CONTEXT SIMULATION, not a tool-using agent run: this harness cannot spawn "
    "tool-using subagents, so the model is handed the captured terminal output.",
    "Native harness auto-discovery is not exercised; trigger queries use a single-skill "
    "description proxy.",
]


def run_suite(scenarios, skill_text, model_fn, judge_fn, only=None, reps_override=None):
    bundles = {name: capture(build_fixture(name, spec)) for name, spec in VARIANTS.items()}
    rows = []
    for sc in scenarios:
        if only and sc["id"] not in only:
            continue
        bundle = bundles[sc["fixture"]]
        turns = [{"role": "user", "content": sc["prompt"]}]
        for rep in range(reps_override or sc.get("reps", 1)):
            transcript, prompt_used = [], ""
            live = [dict(t) for t in turns]
            for i in range(sc.get("turns", 1)):
                prompt_used = render_prompt(bundle, live)
                out = model_fn(skill_text, prompt_used)
                transcript.append({"role": "user", "content": live[-1]["content"]})
                transcript.append({"role": "assistant", "content": out})
                if i < sc.get("turns", 1) - 1:
                    live.append({"role": "assistant", "content": out})
                    live.append({"role": "user", "content": sc["followups"][i]})
            verdict = judge_fn(sc, transcript, bundle) if judge_fn else None
            rows.append({
                "scenario": sc["id"], "rep": rep + 1, "moment": sc.get("moment"),
                "coverage": sc.get("coverage", []), "fixture": sc["fixture"],
                "fixture_state": {k: bundle[k] for k in ("status", "diff_head", "log", "show_stat", "unborn", "is_git")},
                "prompt": prompt_used, "transcript": transcript, "verdict": verdict,
            })
    return rows


def summarize(rows):
    out = []
    for r in rows:
        crit = (r["verdict"] or {}).get("criteria", [])
        out.append({
            "scenario": r["scenario"], "rep": r["rep"],
            "passed": sum(1 for c in crit if c.get("ok")), "of": len(crit),
            "failed": [c["id"] for c in crit if not c.get("ok")],
        })
    return out


def dispose_http(base_url, api_key, model, temperature=0.2):
    def call(system, prompt):
        body = json.dumps({"model": model, "temperature": temperature,
                           "messages": [{"role": "system", "content": system or ""},
                                        {"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=body,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {api_key}"})
        with urllib.request.urlopen(req, timeout=240) as resp:
            return json.load(resp)["choices"][0]["message"]["content"]
    return call


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(RESULTS_DIR))
    ap.add_argument("--only", default="")
    ap.add_argument("--reps", type=int, default=None)
    ap.add_argument("--scenarios", default=str(HERE / "evals.json"))
    ap.add_argument("--skill", default=str(SKILL_PATH))
    ap.add_argument("--no-skill", action="store_true")
    ap.add_argument("--tag", default="")
    args = ap.parse_args(argv)

    api_key = os.environ.get("EVAL_API_KEY")
    if not api_key:
        print("EVAL_API_KEY is required.", file=sys.stderr)
        return 2
    model = os.environ.get("EVAL_MODEL", "gpt-4.1")
    model_fn = dispose_http(os.environ.get("EVAL_BASE_URL", "https://api.openai.com/v1"), api_key, model)

    def judge_fn(sc, transcript, bundle):
        raise SystemExit("Standalone mode has no judge configured; supply your own judge_fn.")

    doc = json.loads(Path(args.scenarios).read_text(encoding="utf-8"))
    skill_text = "" if args.no_skill else Path(args.skill).read_text(encoding="utf-8")
    rows = run_suite(doc["scenarios"], skill_text, model_fn, judge_fn,
                     only=[s for s in args.only.split(",") if s], reps_override=args.reps)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = args.tag or ("baseline" if args.no_skill else "skill")
    path = out / f"{name}.json"
    path.write_text(json.dumps({
        "model": model, "skill_sha256": hashlib.sha256(skill_text.encode()).hexdigest(),
        "limits": LIMITS, "summary": summarize(rows), "rows": rows,
    }, indent=2), encoding="utf-8")
    print(json.dumps(summarize(rows), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
