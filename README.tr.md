[English](README.md) · [Türkçe](README.tr.md)

<p align="center">
  <img src="docs/assets/cover-tr.svg" alt="Claude Code ekip kurulumu: tek şef, farklı uzmanlar, değişiklik önizlemesi ve isteğe bağlı OTLP kullanımı" width="100%">
</p>

# Ustam

<!-- ustam-hub-quickstart:start -->
## Ustam 1.0.0-beta.2 ile başlayın

Codex, Claude Code ve OpenCode için aynı yerel uygulama.

**Mac durumu:** Yayımlanan beta.1/beta.2 Mac indirmelerinde ilk açılış sorunu çözülmüş değildir. Yerelde derlenen uygulama bir Mac üzerinde doğrulandı; bu, herkese açık indirmenin açıldığını kanıtlamaz. beta.3 yayımlanmadı. [Mac notlarına bakın](docs/ustam-hub.tr.md).

1. **İndirin:** [Beta sürümü](https://github.com/metapak/ustam-claude-orchestrator/releases/tag/ustam-v1.0.0-beta.2) açın ve Windows/Linux yerel ZIP’ini tamamen çıkarın: [Windows](https://github.com/metapak/ustam-claude-orchestrator/releases/download/ustam-v1.0.0-beta.2/ustam-1.0.0-beta.2-windows-x86_64.zip) · [Linux](https://github.com/metapak/ustam-claude-orchestrator/releases/download/ustam-v1.0.0-beta.2/ustam-1.0.0-beta.2-linux-x86_64.zip).
2. **Açın:** Windows’ta **Ustam.exe**, Linux’ta **Ustam** dosyasını açın. Mac’te yerel kaynak derlemesi için **Ustam.app** dosyasını açın. Mac uygulaması kendi çalışma ortamını içerir ve tek başına taşınabilir; Windows/Linux’ta çıkarılan dosyaları birlikte tutun. Haricî Python gerekmez.
3. **Uygulamaları seçin:** Codex, Claude Code veya OpenCode seçin. Kullandığınız sağlayıcının CLI’ı kurulu ve oturumu açık olmalıdır.
4. **Projeleri ekleyin:** Klasörleri yerel tarayıcı sayfasında ekleyin; orkestrayı seçin, değişiklikleri kontrol edip uygulayın.

Bu beta imzasızdır ve notarize edilmemiştir. Mac Gatekeeper indirmeyi engelleyebilir. Sağlayıcıların hesap/model erişimi ayrıca gereklidir. [Yerel merkez rehberi](docs/ustam-hub.tr.md).
<!-- ustam-hub-quickstart:end -->

## Projeler ve orkestralar

Bir proje ekleyin, orada kullandığınız sağlayıcıyı seçin; ardından projenin kurulum alanında kayıtlı bir orkestra seçin veya yenisini oluşturun. Kaydetmeden önce modelleri ve görevleri inceleyin. Kayıtlı orkestra yeniden kullanılabilen ayardır; kaydetmek sağlayıcı işi başlatmaz. Projeye uygulanacak değişiklikleri yazmadan önce inceleyin.

Yapılandırma ve önizleme çevrimdışı çalışabilir. Gerçek işi başlatmak seçili sağlayıcının CLI’ını, girişini ve model erişimini gerektirir. Ekip ayarları ile çalışma zamanının gerçek yürütme sınırları ayrıdır; sayfa bu sınırları bildirir. Kullanım/geçmiş kaydedilmiş işleri anlatır; canlı orkestra animasyonu değildir.

## İleri düzey uyumluluk

Önceki sağlayıcıya özel konsol mevcut projeler için korunur. Ekran görüntüleri, on görev hazır ayarı ve eski başlatıcılar [eski konsol başvurusunda](docs/legacy-console.tr.md) ayrı anlatılır. Güncel kurulum için [birleşik uygulama rehberini](docs/ustam-hub.tr.md) izleyin.

## Lisans

[Apache-2.0](LICENSE) · [Atıf](NOTICE). Bu bağımsız topluluk projesi sağlayıcıların geliştiricileri tarafından onaylanmış değildir.
