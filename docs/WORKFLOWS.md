# Daily workflows

## The ChatGPT Work connection: an important distinction

**The default is a Work handoff.** No supported mechanism was verified that lets this private local app create a conversation directly inside the ChatGPT Work interface, upload its sources automatically, force Work mode, select its model and collect its results. The app does not use undocumented ChatGPT endpoints or your browser cookies.

The documented Responses API and Codex app-server integrations are different from remotely controlling the ChatGPT Work interface. They must not be represented as “Work.” To honour your preference, the app makes no automatic AI requests in its default mode.

Your normal workflow:

1. Upload a transcript once, or select an existing file.
2. Choose the task. Add its dates/video URL if known. For long-form forecasts, optionally check **Also create an advance register**.
3. Select any prior registers, assessment records, monthly tracker, selfie or thumbnail reference images that belong to this task.
4. Click **Prepare Work task** and download the packet from its task window.
5. Extract it. In ChatGPT, select **Work** and your chosen model/effort. Attach `TASK.md` and the reference images. Say: **“Follow the task and return result.json plus any images.”**
6. Return to the task in this app. Import `result.json`. Upload separately generated images/PDFs in File space, reopen the task from **View tasks**, and attach the saved output.
7. Review the results and mark them reviewed.

The task contains your full prompts and sources, so you do not need to compose the prompt again. It asks Work for a structured output envelope; `examples/result-template.json` shows the format. You can alternatively upload individual Markdown/image/PDF outputs and attach them to the task. Downloaded packets contain the selected source material, including any private content you deliberately included.

Model preference starts at **`gpt-6-astra`, medium**. This is selectable in Settings, with a free-text model field so it can evolve. A Work packet records your preference but cannot enforce the ChatGPT model picker or account entitlement. The app cannot automatically access ChatGPT memories, chat history, Library or previous thumbnails; its saved private profile, task history and supplied references provide continuity.

### Optional automatic OpenAI API generation

If you later choose to use the separate API integration:

```bash
"$HOME/.local/lib/mystical-mark-studio/current/.venv/bin/python" "$HOME/.local/lib/mystical-mark-studio/current/manage.py" credentials
systemctl --user restart mystical-mark-studio
```

Enter your OpenAI API key privately at the terminal prompt. Leave other values blank to preserve them. A single `-` removes a value. Then choose **api** in Settings. Each generation request asks you to confirm sending the selected sources to the API. API access/billing is distinct from the Work interface; account/model/tool access is not guaranteed by a model name.

Text generation uses the Responses API with `store: false`. This setting is not a guarantee of zero provider retention; use the provider's data controls for your account. The app does not record your key in the browser or backup archive. It is kept in the mode-0600 local `secrets.env` service environment file.

Research tasks enable web search and reject outputs if no web-search call is present. An advance-register task never enables web search. Sources are passed in full, with a 750,000-character selection limit; oversized requests fail rather than silently truncating the transcript. Provider context limits may be lower for a selected model.

Long-form API tasks make a text request followed by an image request. Text outputs are checkpointed first. If the image fails, the job is marked **partial** and the existing text remains saved. Image outputs include the original and an exact **1280 × 720** version fitted without cropping. Padding may be present when the image provider returns a different aspect ratio. Review image text and anatomy before publishing.

The text-model and reasoning preference is recorded per job. No automatic retry is performed for a timed-out paid API request. A restart marks in-flight jobs **interrupted**; inspect existing outputs and provider usage before making another request. These API paths were tested with simulated responses, not a live key.

## Forecast accountability and your recurring preferences

Generalized `references/advance-register.md` and `references/assessment.md` prompts are included. Existing installations preserve their exact earlier templates in the private creator profile. They carry forward:

- Prospective/open-window/retrospective timing labels, actual extraction time, exact quotations and timestamp links.
- Stable claim IDs; original uncertainty, criteria, scope and event windows.
- Support, partial support, contradiction, expired/unconfirmed, pending, unresolved and non-assessable categories.
- Contrary evidence, pre-existing background, unique-event tracking and research/access logs.
- A website-ready Markdown article plus a separate weekly assessment record.
- Monthly reconciliation with a compact **monthly-only** carry-forward tracker. Weekly tasks do not require an accumulating backlog.
- A yearly extension that reconciles selected monthly material, preserves IDs/windows and discloses missing months; it does not replace or extend the monthly tracker.

Outputs are immutable files. Importing a second `register.md` creates another file ID rather than overwriting the original. The app stores SHA-256 hashes and prepared task snapshots for provenance. **This is not independently certified preregistration or a tamper-proof external timestamping system.** You still review the extraction and publish/register it according to your chosen process.

Your YouTube description insertion is stored in your private creator profile; the first upgrade migrates the original block exactly. When `youtube_metadata.json` is imported, the app builds `youtube_description.txt` itself, with the insertion unchanged, a separate custom-additions slot, chapters and hashtags. Use that TXT output when pasting into YouTube. The model's other Markdown prose still needs review.

The guidance-only article workflow excludes the weekly forecast breakdown. All generation prompts preserve your actual words and qualifications, distinguish research from intuitive interpretation, maintain queer inclusion, and never invent higher-self answers for you.

## Writing, client summaries and posts

Save scripts in **Writing room**. Each save keeps the preceding revision; the revision window lets you read/copy an older version. Navigation does not silently autosave text, so save before changing sections. **Export Markdown** stores a reusable file and downloads it.

**Turn into X / Threads posts** preserves every word and its order. It normalises whitespace and splits at word boundaries with conservative limits (X: 280 weighted budget; Threads: 500 UTF-16 units). It does not add numbering or replace your guidance with a summary/link. A single overlong word/URL triggers an error rather than being dropped. You can edit each segment before saving.

Client workflow: upload the transcript as **private**, prepare the Client readings task, import the summary, and open it in File space. Use **Edit a copy** to revise it if needed, then **Create client PDF** after reviewing its faithfulness. The PDF is generated locally and saved private. It does not email the client. The layout follows the earlier quick-reference structure without including Jenn's personal reading in this distribution.

### Optional X / Threads direct publishing

Set credentials using the terminal command above:

- `X_USER_ACCESS_TOKEN`: a user-context OAuth token for an approved X developer application with posting permission. App-only bearer tokens do not authorize posting as you.
- `THREADS_ACCESS_TOKEN` and numeric `THREADS_USER_ID`: tokens/identity for your approved Threads application with required publish/reply permissions.

This release accepts tokens you obtain through each platform's authorized developer flow. It does **not** implement an in-app OAuth sign-in, token refresh, media publishing or platform analytics synchronization. Tokens can expire; update them through `manage.py credentials`. Platform approvals, pricing and restrictions apply. No live posting was performed during development.

Saved posts can be edited and approved from Publishing desk. Changing text resets the approval information based on the newly submitted review. **Approved** saves a reviewed post for an explicit Publish click. **Scheduled** authorizes the exact reviewed text at the selected time. The picker uses your device's local timezone; saved schedules use UTC and display your profile timezone. Keep the device timezone correct.

The scheduler checks about every 20 seconds. Delays under 15 minutes are delivered when it can run; longer misses become **overdue** for review. A failure or restart during sending becomes **uncertain** because a platform may have accepted a post before the response was lost. Inspect the platform and saved remote IDs. There is intentionally no automatic retry of an uncertain send. Successful earlier segments of a thread stay recorded.

## Analytics import and comparisons

Live API aggregation for YouTube, Instagram, TikTok, X and Threads is not included. The working path is a documented CSV adapter, with the empty template in `examples/analytics-template.csv`:

```csv
platform,account,content_id,date,metric,value,basis
```

Convert each platform export to one row per metric/date/content item. Allowed platforms and metrics are listed in the import dialog. Use `daily` for activity on that specific date and `lifetime_snapshot` for a cumulative total measured on that date. Do not label a weekly cumulative total as daily. Use an empty `content_id` only for an account total.

Reimporting the same platform/account/content/date/metric/basis replaces that observation. The dashboard separates daily data from lifetime snapshots. Snapshot charts use the latest available observation for each item in the selected range; they are not period growth. Account totals take precedence over their post-level components to avoid double counting. Cross-platform sums are activity, **not deduplicated audience**, and platform view definitions differ. Missing metrics stay missing.

Export CSV or prepare a Work analysis packet. No analytics are fabricated for disconnected accounts.


## Large monthly Work tasks (1.1.1)

In Settings choose `work`. Select all four weekly registers and all four assessments, then prepare one monthly task. The old combined-text limit no longer applies to manual Work handoffs. Download the packet and attach its complete TASK.md in one Work conversation. All source text remains in that file; no splitting or truncation occurs. Recreate a task that previously failed to prepare after updating. Already saved tasks keep their frozen prompts. Direct API mode retains its 750,000-character guard; use Work for larger reviews. Receiving-service upload and model-context limits still apply independently.
