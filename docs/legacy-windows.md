> Advanced compatibility only / Yalnız ileri düzey uyumluluk. These instructions describe the older provider-specific console, not the unified Ustam app. / Bu yönergeler birleşik Ustam uygulamasını değil eski sağlayıcı konsolunu anlatır.

# Windows setup

Have [Claude Code](https://code.claude.com/docs/en/getting-started) and [Python 3.11 or newer](https://www.python.org/downloads/) installed. Python is not included.

1. **Download:** [Get the current ZIP](https://github.com/metapak/ustam-claude-orchestrator/archive/refs/heads/main.zip) and open the extracted folder.
2. **Open:** Open `launchers` and double-click **Launch Ustam.vbs**.
3. **Choose a project:** Pick the folder where you use Claude Code.
4. **Install:** In the browser, keep the suggested team or change it. Click **Check changes**, then **Install**. Restart Claude Code in that project.

For later changes, reopen the launcher and click **Save**; no uninstall is needed. An already-open Claude Code session may need to be reopened before it uses the changes. Double-click behavior has not been tested on every Windows setup.

<details>
<summary>Optional PowerShell, external-provider, and uninstall steps</summary>

Run the PowerShell installer from the extracted folder:

```powershell
.\scripts\install.ps1 -Target C:\path\to\project -DryRun
.\scripts\install.ps1 -Target C:\path\to\project
```

Or double-click `setup.cmd`. It asks for the target folder, action, native profile, and optional external proposal provider. Its uninstall choice stops safely on Windows; use the manual steps below. Existing settings and conflicting files are preserved by default. Review `.claude\bounded-orchestrator.settings.example.json` if the target already had settings.

The guided screen explains balanced, quality, economy, quota saver, or per-role custom settings, then shows a final configuration review and next steps. Every native/custom role must use an Anthropic Claude alias or full `claude-*` ID. The lower-level installer remains non-interactive:

```powershell
.\scripts\install.ps1 -Target C:\path\to\project -Preset quality
```

External APIs default to none. To explicitly add a proposal-only provider, define its key in the environment that launches Claude Code:

```powershell
$env:OPENAI_API_KEY = "your key"
.\scripts\install.ps1 -Target C:\path\to\project -ExternalOpenAI -ExternalModel gpt-5.6-sol -ExternalEffort high
$env:DEEPSEEK_API_KEY = "your key"
.\scripts\install.ps1 -Target C:\path\to\project -ExternalProvider deepseek -ExternalModel deepseek-flash -ExternalEffort high
```

API keys are inherited at runtime and are never written to project files. External providers are proposal-only; native Claude remains the sole writer.

Later non-interactive runs preserve the existing provider choice when no provider switch is supplied. Use `-ExternalProvider none`, `-NoExternalOpenAI`, or `-NoExternalDeepSeek` to remove only an unchanged installer-owned MCP entry and bridge. Modified entries are kept with a warning.

The browser removal button and both `-Uninstall` and `-Uninstall -DryRun` are unavailable on Windows. They stop without changing the project because this release cannot guarantee secure file removal there. The latter command does not produce a removal preview.

</details>

## Manual cleanup on Windows

This is a conservative **partial cleanup**, not an automated uninstall. Close Claude Code in the project and make a copy of the project folder before changing anything.

1. Open `<project>\.claude\.bounded-orchestrator\install.json`. Its `files` object lists installed paths, each with `owned` and `sha256`. To print paths the installer owns and their recorded hashes in PowerShell, set `$project` to the exact project folder and run:

   ```powershell
   $project = 'C:\path\to\project'
   $manifest = Get-Content -LiteralPath (Join-Path $project '.claude\.bounded-orchestrator\install.json') -Raw | ConvertFrom-Json
   $manifest.files.PSObject.Properties | Where-Object { $_.Value.owned } | ForEach-Object { '{0}  {1}' -f $_.Name, $_.Value.sha256 }
   ```

2. For each listed file you consider removing, confirm it is **inside this project**, that neither it nor any parent folder is a link or junction, and that its current SHA-256 equals the listed value. For example, run `Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\path\to\project\.claude\agents\explorer.md'`. Delete only that exact unchanged file in File Explorer. Keep missing, modified, or `owned: false` files. Never remove an entire `.claude` folder just because it contains installed files.
3. Keep `.claude\.bounded-orchestrator\.gitignore`, `backups`, task/history data, and any other private runtime files. Keep `.claude\settings.json` unless its manifest entry says `owned: true`, its hash still matches, and you have confirmed it contains no project settings you want to retain.
4. Keep `CLAUDE.md` and `.mcp.json` intact during this cleanup. `CLAUDE.md` can contain your own instructions beside or inside the `<!-- claude-bounded-orchestrator:start -->` and `<!-- claude-bounded-orchestrator:end -->` markers. `.mcp.json` can contain unrelated servers; the tool's server names are `openai-bounded-implementer` and `deepseek-bounded-proposal`. Review those marked sections and entries separately before any manual edit. Keep `.claude\tools\openai_mcp.py` or `deepseek_mcp.py` while a retained MCP entry still refers to it.
5. Keep `install.json` as an ownership record while any marked instruction, MCP entry, bridge, or managed file remains. Restart Claude Code after your review. If you cannot verify a file or block, leave it in place.

## Windows'ta elle temizleme (Türkçe)

Windows'ta tarayıcıdaki kaldırma düğmesi ve `-Uninstall` ile `-Uninstall -DryRun` komutları güvenli biçimde durur; komut önizlemesi oluşturulmaz. Bu adımlar **kısmi temizliktir**. Önce Claude Code'u kapatın ve proje klasörünün bir kopyasını alın.

1. Projedeki `.claude\.bounded-orchestrator\install.json` dosyasını açın. `files` bölümünde her yolun `owned` ve `sha256` değerleri vardır. Yukarıdaki PowerShell komutu yalnız kurucunun sahip olduğu yolları ve kayıtlı özetlerini listeler.
2. Silmeyi düşündüğünüz her dosyanın seçilen projenin içinde olduğundan, dosyanın ve üst klasörlerinin bağlantı/junction olmadığından emin olun. `Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\proje\.claude\agents\explorer.md'` ile özeti alın. Yalnız `owned: true` olan ve özeti kayıtla aynı kalan **tek dosyayı** Dosya Gezgini'nde silin. Değişmiş, eksik veya araca ait olmayan dosyaları ve `.claude` klasörünün tamamını koruyun.
3. `.claude\.bounded-orchestrator\.gitignore`, `backups` ve çalışma verilerini koruyun. `.claude\settings.json` dosyasını, hem sahiplik/özet doğrulaması hem de içindeki proje ayarlarını koruma incelemesi yapılmadıkça silmeyin.
4. `CLAUDE.md` ve `.mcp.json` dosyalarını olduğu gibi bırakın; kişisel talimatlar ve başka MCP sunucuları içerebilirler. `CLAUDE.md` içindeki `<!-- claude-bounded-orchestrator:start -->` / `<!-- claude-bounded-orchestrator:end -->` işaretli bölümü ve `.mcp.json` içindeki `openai-bounded-implementer` / `deepseek-bounded-proposal` girdilerini ayrıca inceleyin. MCP girdisi kalıyorsa kullandığı `openai_mcp.py` veya `deepseek_mcp.py` köprüsünü de koruyun.
5. İşaretli bölüm, MCP girdisi, köprü veya başka yönetilen dosya kaldığı sürece sahiplik kaydı olan `install.json` dosyasını saklayın. Emin olmadığınız dosyayı silmeyin; incelemeden sonra Claude Code'u yeniden başlatın.
