[English](release-v0.3.1.md) | [Türkçe](release-v0.3.1.tr.md)

# Claude Bounded Orchestrator v0.3.1

0.3.1 sürümü, etkin çıktı kodlaması bütün Türkçe karakterleri gösteremeyen Windows terminallerindeki etkileşimli kurulum hatasını düzeltir.

Kurucu artık terminal destekliyorsa Türkçe metni aynen gösterir. CP1252 gibi kısıtlı kodlamalarda ise `UnicodeEncodeError` ile kapanmak yerine yalnızca gösterilemeyen karakterleri değiştirir. Profil seçimi ve kurulum normal şekilde devam eder.

Bu sürüm, dengeli profil seçim akışını katı CP1252 çıktısıyla baştan sona çalıştıran ve kurulumun tamamlandığını doğrulayan bir gerileme testi içerir. 0.3.0 sürümündeki profil, OpenAI MCP, gizli anahtar koruması, çakışma koruması ve sınırlı tek uygulayıcı davranışları değişmemiştir.
