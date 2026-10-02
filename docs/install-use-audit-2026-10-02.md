# Installation and use audit · 2026-10-02

The setup path is download → open launcher → select project → Check changes → Install. The downloaded package folder and the target project are separate. Keep the package for later updates. Python 3.11+ is a prerequisite; Claude Code runs the resulting team. No global installation is supported.

## Changes from the audit

- A normal terminal update previously regenerated role files and manifest routing from `balanced`, even after a console save. It now preserves saved profile and role choices. Explicit `--preset` and the interactive profile selection still choose new defaults. A single role override starts from saved routing and changes only that role, marking the profile custom. Existing shared settings still use the original preserve/manual-merge policy.
- The selected project path is always visible, with a short explanation of where settings go and how to choose another project.
- Each person's model and effort controls start collapsed. Duties, team capacity and the orchestra remain visible. Advanced project settings remain collapsed.
- Checking, installing, saving, undoing and removal have visible status messages. The preview receives focus; new status messages scroll into view. Changing language translates the existing status without moving the page again.
- File conflicts are classified before generic file errors, so a stale save preview is closed and the user receives the conflict recovery message.
- Mobile task cards use two columns, preventing narrow four-column labels caused by a later desktop rule overriding the mobile layout.
- Hovered task cards keep dark text on a light gold background; previously the generic burgundy button hover made the selected card's dark label difficult to read.

## Verification performed

| Area | Evidence and result |
| --- | --- |
| Repository checks | `python3 scripts/validate.py`, `node --check .claude/tools/console/app.js`, `git diff --check`: passed. |
| Automated suite | `python3 -m unittest discover -s tests -q`: 119 tests, 118 passed and one expected skip for the unsupported-platform branch because secure removal is available on this Mac. |
| Fresh setup | Actual Chrome, empty disposable project: checking showed progress and wrote no project files; Install showed progress, completed and persisted settings. |
| Settings and reload | Chrome: website draft, custom conductor model, helper count change, Save, page reload and Undo last change preserved/restored the expected counts. Expanded model controls stayed expanded after a choice. |
| Updates | Regression tests: normal update and dry run preserve saved economy routing; one role override preserves other roles; explicit quality profile takes precedence. Console-created roster, concurrency, profile and routing survive a CLI update. Actual generated agent frontmatter is checked. |
| Removal | Chrome: preview requires a separate checkbox, Cancel leaves files present, confirmed removal deletes unchanged agent files while retaining a manually edited implementer file. Backups and project directory remain. Existing automated tests cover stale preview, directory handles, symlink/race protection and retained file edits. |
| Error recovery | Chrome: an existing modified/unowned agent causes a visible conflict error and leaves the save preview closed. |
| Language and layout | Chrome desktop 1360×900 and mobile 390×844, Turkish and English; no JavaScript page errors or horizontal mobile overflow. Screenshots inspected for the collapsed controls, target path, readable task cards and orchestra. |
| Launcher | Existing tests exercise package selection retry/cancel, path quoting, project selection, ready URL, browser-open failure and server failure. Native AppleScript scripts compile on macOS. |
| Archives | `python3 scripts/build_release.py --output-dir /tmp/ustam-claude-release-audit`: source, macOS/Linux and Windows ZIPs plus checksums generated successfully outside the repository. |

Tests used disposable directories only. No real project or installed user configuration was used. Browser evidence was produced in `/tmp/ustam-claude-{before,preview,usage,error}.png` and mobile viewport captures `/tmp/ustam-claude-mobile-{cards,controls}.png`; these are local audit artifacts, not distributed product files.

## Platform and runtime boundaries

The host is macOS with Python 3.14.7 and an actual Google Chrome executable driven through Playwright. Native Finder double-click, Gatekeeper approval, a real macOS folder selection, Windows VBS/PowerShell execution and an actual Linux desktop were not exercised. POSIX file/API tests on macOS do not prove Linux-native behavior. Windows automatic removal stays disabled because the required secure directory-handle operations are unavailable; the guides continue to say so. No change weakens that restriction.

A live Claude Code session, provider access, model availability, account quota and effective session overrides were not tested. The UI reports project-file choices and explicitly supplied historical/synthetic usage. Updating package files in a running console requires closing it and opening the new package. Terminal profile changes can require merging the generated settings example because shared settings are preserved. Those boundaries remain stated in the bilingual guides.
