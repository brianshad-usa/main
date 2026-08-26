# Photographic social style — automatic photo intake

`sync_photos.py` pulls new frames from the Dropbox brand-photo folder into the
live photographic social style, with no manual step. Brian just drops photos into
the folder; within a few hours they appear in the rotation.

- **Source:** `C:\Users\brian.shad\Dropbox\Prolink\Marketing\2026 Photos`
  (override with the `PHOTO_SRC` env var)
- **Into:** `assets/photos/` (progressive JPEG, ≤1600px, crisp) + registered in
  `assets/variety_assets.json` under `photographic` (and `behind_the_scenes`
  when people are detected)
- **Ledger:** `assets/photos/.ingested.json` — content-hash record so a file is
  never re-processed or duplicated (rename-proof). It also holds the one-time
  baseline of the 14 frames present at deployment, so only files added *later*
  get auto-ingested.
- **Filters (skips non-photos):** too small (`min side < 600` or `width < 900`),
  extreme aspect (`>2.6` or `<0.42`), and near-solid / logo-slate frames
  (`>60%` near-white, or very low detail). Brand slides won't get pulled in.
- **Default render hints for new photos:** center focal `[0.5, 0.5]` and
  `text: "bottom"` — bottom-anchored headline with the card's directional scrim,
  which keeps text legible and rarely lands on a face. Fine-tune any photo by
  editing its entry in `assets/variety_assets.json`; the sync never overwrites an
  entry that already exists.
- **Git:** the script only writes files. The existing **ProLink Auto-Commit
  Watcher** commits + pushes them. `sync_photos.py` never touches git itself.

Idempotent: running it against an unchanged folder reports `0 new`.

Manual run / preview:

```powershell
python C:\Users\brian.shad\prolink-landing-page\main\sync_photos.py            # sync
python C:\Users\brian.shad\prolink-landing-page\main\sync_photos.py --dry-run  # preview only
```

## One-time setup — register the scheduled task

Run this once in PowerShell as Brian. It registers **"ProLink Photo Sync"** to run
hidden at logon and every 3 hours, auto-restarting (mirrors the Auto-Commit
Watcher's resilience). It does not start the task itself.

```powershell
$repo   = "C:\Users\brian.shad\prolink-landing-page\main"
$script = Join-Path $repo "sync_photos.py"
$py     = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python.exe).Source }   # pythonw = no console window

$action = New-ScheduledTaskAction -Execute $py -Argument "`"$script`"" -WorkingDirectory $repo

# Run at logon, then repeat every 3 hours indefinitely
$trigger = New-ScheduledTaskTrigger -AtLogOn
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours 3) `
    -RepetitionDuration (New-TimeSpan -Days 3650)).Repetition

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -MultipleInstances IgnoreNew `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 5) -Hidden

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName "ProLink Photo Sync" `
    -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Pulls new Dropbox brand photos into assets/photos + variety_assets.json for the photographic social style. Idempotent; the ProLink Auto-Commit Watcher pushes the changes." -Force
```

To verify or remove:

```powershell
Get-ScheduledTask -TaskName "ProLink Photo Sync"
Start-ScheduledTask -TaskName "ProLink Photo Sync"    # run on demand
# Unregister-ScheduledTask -TaskName "ProLink Photo Sync" -Confirm:$false
```
