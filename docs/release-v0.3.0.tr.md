[English](release-v0.3.0.md) | [Türkçe](release-v0.3.0.tr.md)

# Claude Bounded Orchestrator v0.3.0

0.3.0 sürümü, kurulum sırasında model dağılımını seçmeyi ve isteğe bağlı OpenAI değişiklik önerisi rolünü ekler.

## Yenilikler

- Tek tıklamalı kurulumda Türkçe `balanced` (dengeli), `quality` (yüksek kalite), `economy` (ekonomik) ve rolleri tek tek ayarlayan `custom` (özel) profilleri bulunur.
- Otomatik kurulumlar soru sormadan `--preset`, `--role-model ROL=MODEL` ve `--role-effort ROL=DUZEY` seçeneklerini kullanabilir.
- İsteğe bağlı ve ek pakete ihtiyaç duymayan yerel MCP köprüsü, seçilen model ve düşünme düzeyiyle OpenAI Responses API hizmetini çağırır.
- `OPENAI_API_KEY` yalnızca çalışma ortamından okunur ve hiçbir dosyaya kaydedilmez.
- OpenAI rolü sadece kendisine verilen bağlamı görür ve öneri döndürür. Çalışma alanına erişemez; yerel Claude uygulayıcısı tek dosya yazarı olarak kalır.
- Var olan ayarlar, çakışan dosyalar ve MCP sunucuları korunur. Kaldırma işlemi yalnızca bu proje tarafından eklenen ve değişmemiş girişleri temizler.
- Sağlayıcı seçeneğinin yazılmaması önceki seçimi korur; seçim ekranındaki “Hayır” veya `--no-external-openai` yalnızca kurucuya ait değişmemiş bağlantı dosyalarını açıkça kapatır.
- Ana oturum ayarlarında desteklenmeyen `max` değeri dosya yazılmadan reddedilir; yardımcıların ön yüz ayarlarında kullanılabilir.

MCP akışı ve sağlayıcı isteği yerel bir sahte Responses API ile baştan sona test edilmiştir. Yayın ortamında API anahtarı bulunmadığı için ücretli canlı istek çalıştırılmamıştır.
