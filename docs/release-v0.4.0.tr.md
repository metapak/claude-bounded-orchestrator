[English](release-v0.4.0.md) | [Türkçe](release-v0.4.0.tr.md)

# Claude Bounded Orchestrator v0.4.0

0.4.0 sürümü, yerel Claude ekibini tek marka olarak korur ve diğer bütün modelleri açıkça seçilen, yalnızca öneri üreten haricî API seçeneği hâline getirir.

## Öne çıkanlar

- Dengeli, yüksek kalite, ekonomik ve özel yerel görev dağılımları yalnızca `opus`, `sonnet`, `haiku` veya tam `claude-*` model kimliklerini kabul eder.
- GPT, DeepSeek ve diğer sağlayıcı kimlikleri yerel roller için reddedilir; kurucu haricî öneri sağlayıcısının kullanılmasını açıklar.
- Yönlendirmeli kurulum varsayılan olarak haricî sağlayıcı kullanmaz; istenirse OpenAI GPT veya DeepSeek V4.1 Flash açıkça seçilebilir.
- Yeni ve ek paketsiz DeepSeek köprüsü güncel `deepseek-flash` API kısa adını kullanır, model ile düşünme düzeyini denetler, gönderilen metni sınırlar ve `DEEPSEEK_API_KEY` değerini yalnızca çalışma ortamından okur.
- Haricî sağlayıcıların çalışma alanı araçları yoktur ve güvenilmeyen öneri metni döndürür. Yerel Claude uygulayıcısı tek dosya yazarı olarak kalır.
- macOS, Linux ve Windows başlatıcıları hedef/işlem seçimini, profil açıklamalarını, API uyarısını, son ayar incelemesini, kurulum sonucunu ve sonraki adımları daha açık gösterir.
- Var olan MCP sunucuları, değiştirilmiş dosyalar, eski OpenAI kayıtları, yedekler, önizleme ve güvenli kaldırma davranışları korunur.
- Yayın paketlerinde özel çalışma klasöründen yalnız `.claude/.bounded-orchestrator/.gitignore` bulunur; görev durumu, kilitler ve yedekler pakete alınmaz.
- Kaldırma işlemi, kullanıcı tarafından değiştirilmiş MCP kaydının ihtiyaç duyduğu sağlayıcı köprüsünü korur; değiştirilmemiş sağlayıcı kurulumu ise tamamen kaldırılır.

## Doğrulama

Otomatik testler; marka dışı yerel model reddini, varsayılan sağlayıcı durumunu, OpenAI geriye dönük uyumluluğunu, yerel sahte sunucuyla DeepSeek MCP çağrılarını, gönderim sınırını, anahtarların dosyalara yazılmamasını, sağlayıcı değişimini, güvenli kaldırmayı, kısıtlı terminal kodlamalarını ve yayın paketlerini kapsar. Ücretli canlı API isteği yapılmamıştır; hesap ve bölge erişimini her kullanıcı doğrulamalıdır.
