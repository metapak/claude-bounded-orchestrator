[English](README.md) · [Türkçe](README.tr.md)

<p align="center">
  <img src="docs/assets/cover-tr.svg" alt="Claude Bounded Orchestrator için sıcak renkli orkestra sahnesinde şef ve farklı yardımcı karakterleri" width="100%">
</p>

# Claude Bounded Orchestrator

[![Lisans: Apache-2.0](https://img.shields.io/badge/lisans-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/downloads/)

**Claude Code için yerel kurulum ve çalışma düzeni: ana oturum işleri proje yardımcılarına dağıtır; tarayıcı konsolu planlanan ayarları ve gözlenen kullanımı gösterir.**

Claude Bounded Orchestrator, ana Claude oturumuna yalnız koordinasyon görevi verir: kullanıcıyla konuşur, planlar, küçük işler dahil yürütmeyi yardımcılara devreder, kısa kanıtları okur ve sonucu bildirir. Dosya inceleme, araştırma, uygulama, test ve bağımsız değerlendirme uzmanlara aittir. Bu davranış bir talimat kuralıdır; ana oturumun araçlarına teknik kilit koymaz. Küçük ve yerel görev listesi de birbirine bağlı adımları izler.

Siz ne istediğinizi normal şekilde yazmaya devam edersiniz. Proje, arka plandaki çalışma düzenini sağlar.

## Hızlı başlangıç: yerel kurulum ekranını açın

**1. [Güncel main ZIP dosyasını](https://github.com/metapak/claude-bounded-orchestrator/archive/refs/heads/main.zip) indirip çıkarın.** Tarayıcıdan kurulum için bu güncel kaynak arşivini kullanın; eski sürüm paketlerinde grafik başlatıcı bulunmayabilir. Sonraki ayar değişiklikleri için çıkarılan klasörü saklayın.

**2. Gerekenleri kontrol edin.** Güncel [Claude Code](https://code.claude.com/docs/en/getting-started) ve Python 3.11 veya yenisini kurun. Başlatıcı bilgisayarınızdaki Python'u kullanır; Python veya kalıcı arka plan hizmeti kurmaz.

**3. Kurulum ekranını açın.** macOS’te çıkarılan klasördeki `launchers/Bounded Orchestrator.app` dosyasına, Windows’ta `launchers/Launch Bounded Orchestrator.vbs` dosyasına çift tıklayın. Açılan klasör seçicisinden mevcut yerel proje klasörünü seçin; kaynak kodu çalışmaları için Git önerilir, ancak başlatıcı bunu zorunlu tutmaz. macOS imzasız uygulamayı engellerse macOS/Linux rehberindeki alternatif yolu izleyin.

**4. Ekibi seçip değişiklikleri inceleyin.** Tarayıcıda çalışma biçimini ve 1–10 yardımcıyı seçin. Her yardımcı için görev, Claude modeli ve düşünme düzeyi belirleyin; aynı görev birden çok kez seçilebilir. **Değişiklikleri kontrol et** ile yalnız seçili projeye yazılacakları görün, ardından **Kur** düğmesine basın. İlgisiz ayarlar korunur ve yedekler Git dışında tutulur; çakışmalar inceleme gerektirir. Claude Code'u bu projede yeniden başlatıp isteğinizi normal şekilde anlatın.

**5. Sonra tekrar açın.** Aynı başlatıcıdan tercihleri **Kaydet** ile değiştirin veya önceki konsol değişikliğini **Geri al** ile kaldırın. **Konsolu kapat** yerel sunucuyu durdurur. Planlanan yardımcılar ayardır; Kullanım ekranı yalnız açıkça verdiğiniz dışa aktarımda gözlenen kullanımı gösterir.

![Yerel konsolun Türkçe Kullanım ekranında temizlenmiş yerleşik örnek veriler ve üç çizim karakteri](docs/assets/console-tr.png)

*Güncel Kullanım ekranının temsili örneği. Yerleşik temizlenmiş örnek veriler kullanılır; değerler sizin proje ayarlarınız veya kullanımınız değildir.*

Linux için çift tıklamalı grafik başlatıcı yoktur; isteğe bağlı komutlu kurulum macOS/Linux rehberindedir. Ayrıntılar: [macOS/Linux rehberi](INSTALL-MACOS.md) ve [Windows rehberi](INSTALL-WINDOWS.md). Depo testleri canlı Claude Code oturumunu ve iki işletim sistemindeki yerel çift tıklama akışını doğrulamaz.

<details>
<summary>İsteğe bağlı terminal ve elle kurulum</summary>

Çıkarılan depo klasöründen önizleyip kurabilirsiniz:

```bash
python3 scripts/install.py /projenizin/yolu --dry-run
python3 scripts/install.py /projenizin/yolu
```

Varsayılan profil `balanced` olur. Diğer örnekler:

```bash
python3 scripts/install.py /projenizin/yolu --preset economy
python3 scripts/install.py /projenizin/yolu --preset quota-saver
python3 scripts/install.py /projenizin/yolu --preset custom \
  --role-model implementer=opus --role-effort implementer=xhigh
```

Yerel modeller `opus`, `sonnet`, `haiku`, `fable` veya tam `claude-*` kimliğidir. Ana oturumda `low`, `medium`, `high`, `xhigh`; yardımcı dosyalarında ayrıca `max` düşünme düzeyi kullanılabilir. Komutlu yönlendirme için macOS/Linux’ta `./setup.command`, Windows’ta `setup.ps1` veya `setup.cmd` vardır. Windows PowerShell seçeneği:

```powershell
.\scripts\install.ps1 -Target C:\projenizin\yolu -DryRun
.\scripts\install.ps1 -Target C:\projenizin\yolu
```

İsteğe bağlı, yalnız kısa bilgiler tutan görev listesi [örneklerde](docs/examples.md) anlatılır. Bu listeye istem, kaynak, günlük, anahtar veya kişisel bilgi koymayın.

</details>

## Artık ne yapıyor?

Siz istediğiniz sonucu normal şekilde anlatırsınız. Ana Claude oturumu işi sınırlı görevlere ayırır; inceleme, uygulama, doğrulama ve son değerlendirmeyi ayrı rollere verir ve her kapsamta tek bir uygulayıcıyı sorumlu tutar. Kesintiler, kullanıcıdan yanıt bekleyen işler, onarımın kime döneceği ve kanıta dayalı tek yeniden deneme kaydedilir. Böylece yarım kalan çalışma geçmişi kaybolmadan devam ettirilebilir.

Tarayıcı konsolunda dengeli, yüksek kalite, ekonomik, kota tasarrufu ve özel profiller ile 1–10 gerçek yardımcı slotu bulunur. Her slotun görevi, Claude modeli, düşünme düzeyi ve isteğe bağlı kısa etiketi seçilebilir; aynı görev tekrar edebilir. Planlanan ekip, geçmiş kullanımda gözlenen yardımcı sayısı değildir. Model ve token raporu yalnız açıkça verilen Claude Code OpenTelemetry dosyasını özetler; dosya yoksa sayı uydurmaz. Hesap kullanımı için Claude Code içindeki `/usage` ekranına bakın.

## Ne kazandırır?

- Ana Claude oturumu kullanıcıyla konuşur, planlar, işleri devreder, kısa uzman raporlarını okur ve sonucu bildirir; yürütme işini üstlenmez. Bu kural teknik araç kilidi değil, model talimatıdır.
- Yalnızca uygulayıcıya dosya değiştirme araçları verilir.
- Değişikliği yapan ile kontrol eden birbirinden ayrılır.
- Yardımcılar yeni yardımcı oluşturamaz; yerleşik derinlik sınırı `1` olur.
- Düzeltme döngüleri sınırlıdır, aynı başarısız yöntem durmadan tekrarlanmaz.
- Hafif görev listesi bekleyen, engellenen ve tamamlanan adımları görünür tutar.
- Tasarım ve güvenlik uzmanlığı yalnızca açıkça istendiğinde kullanılır ve yeni yetki vermez.
- Kurulum mevcut Claude ayarlarını ve çakışan dosyaları varsayılan olarak korur.
- Yerel konsolda hazır profil veya 1–10 gerçek yardımcı slotu seçilebilir; aynı görev birden çok yardımcıya verilebilir.
- Yerel ve özel roller yalnızca Claude kısa adlarını veya tam `claude-*` kimliklerini kabul eder.
- İstenirse OpenAI GPT veya DeepSeek yalnızca yama önerisi üretmek için haricî API olarak eklenebilir.

## Kurulan yapı

```text
.claude/
├── agents/                  # görevleri sınırlı yardımcılar ve seçilen orchestra-slot-XX.md dosyaları
├── skills/                  # isteğe bağlı tasarım ve güvenlik rehberleri
├── tools/task_ledger.py     # devam ettirilebilir kısa görev takibi
├── tools/usage_report.py    # açıkça verilen model/token ölçümlerinin özeti
├── tools/local_eval.py      # son dosyalara bağlı, açıkça çalıştırılan kontrol
├── bounded-orchestrator.eval.example.json
├── tools/openai_mcp.py      # yalnızca OpenAI seçilirse kurulur
├── tools/deepseek_mcp.py    # yalnızca DeepSeek seçilirse kurulur
├── settings.json            # yeni kurulumda ana model, düşünme düzeyi ve derinlik sınırı
└── .bounded-orchestrator/   # Git dışı kayıt, yedek ve görev durumu
CLAUDE.md                    # işaretli ve kaldırılabilir talimat bölümü
.mcp.json                    # yalnızca haricî öneri sağlayıcısı seçilirse eklenir/birleştirilir
```

Projede `.claude/settings.json` zaten varsa kurulum bu dosyayı değiştirmez; elle birleştirmeniz için `bounded-orchestrator.settings.example.json` oluşturur. İstediğiniz `model`, `effortLevel` ve `env` alanlarını inceleyerek birleştirebilirsiniz. Çakışan dosyalar da `--force` seçilmedikçe korunur.

## İsteğe bağlı haricî öneri sağlayıcısı

Yerel ve özel görev dağılımı yalnızca Anthropic Claude modelleriyle çalışır. Kurulum ekranında varsayılan seçim **Yok** olur. İsterseniz tek bir haricî öneri sağlayıcısını açıkça seçebilirsiniz:

```bash
# OpenAI GPT
export OPENAI_API_KEY="anahtarınız"
python scripts/install.py /projenizin/yolu --external-provider openai \
  --external-model gpt-5.6-sol --external-effort high

# DeepSeek V4.1 Flash
export DEEPSEEK_API_KEY="anahtarınız"
python scripts/install.py /projenizin/yolu --external-provider deepseek \
  --external-model deepseek-flash --external-effort high
```

[Güncel resmî DeepSeek V4.1 Flash duyurusuna](https://www.deepseek.com/en/news/deepseek-v4-1-flash/) göre API kısa adı `deepseek-flash`tır; erişim hesabınıza ve bölgenize bağlıdır. DeepSeek düşünme düzeyi `low`, `high` veya `max` olabilir. OpenAI için `none`, `low`, `medium`, `high`, `xhigh` veya `max` seçilebilir; gerçek destek modele bağlıdır.

API anahtarı Claude Code'u başlattığınız ortamda tanımlanır. Kurucu anahtarı kaydetmez veya ekrana yazmaz; MCP ayarına yalnızca sağlayıcı, model ve düşünme düzeyi eklenir. Var olan `.mcp.json` sunucuları korunur. Çakışan bir girdi değiştirilmez ve elle inceleme için örnek dosya yazılır.

Her iki köprü de Python standart kütüphanesini ve Claude Code'un [yerel MCP desteğini](https://code.claude.com/docs/en/mcp) kullanır. Haricî sağlayıcı yalnızca ana yöneticinin açıkça verdiği görev, izinli yollar, kurallar ve seçilmiş bağlamı görür. Çalışma alanını okuyamaz veya değiştiremez; güvenilmeyen bir öneri döndürür. Yerel Claude uygulayıcısı tek dosya yazarı olarak kalır, kabul edilen öneriyi uygular ve normal kontrol süreci devam eder.

Sonraki komutlu kurulumda `--external-provider` yazılmazsa önceki seçim korunur. Kurucuya ait değişmemiş bağlantıyı kaldırmak için `--external-provider none`, `--no-external-openai` veya `--no-external-deepseek` kullanılabilir. Değiştirilmiş veya başkasına ait girdiler uyarıyla korunur. Haricî API kullanımı ayrıca ücret oluşturabilir.

Kaldırma işlemini önce önizleyebilirsiniz:

```bash
python scripts/install.py /projenizin/yolu --uninstall --dry-run
python scripts/install.py /projenizin/yolu --uninstall
```

Kurulumdan sonra değiştirilmiş dosyalar silinmez. Kalan görev durumu ve yedeklerin Git'e eklenmemesi için çalışma klasöründeki `.gitignore` dosyası da korunur.

## Roller

| Rol | Görevi | Model ailesi | Düşünme düzeyi | Dosya değiştirme |
|---|---|---|---|---:|
| Ana Claude oturumu | Planlar, devreder, kısa kanıtları okur ve sonucu bildirir | `opus` | `xhigh` | Talimata göre yürütme yapmaz; normal oturum izinleri teknik olarak kalır |
| İnceleyici | Projedeki yolları ve sınırları bulur | `sonnet` | `medium` | Hayır |
| Araştırmacı | Güncel dış bilgileri doğrular | `sonnet` | `medium` | Hayır |
| Uygulayıcı | Kendisine verilen değişikliği yapar | `sonnet` | `high` | Evet |
| Kontrolcü | Sonucu kanıtlarla sınar | `sonnet` | `high` | Hayır |
| Hata çözümleyici | Kanıtlanmış bir hatanın nedenini açıklar | `opus` | `high` | Hayır |
| Kullanım kontrolcüsü | Sınırlı bir kullanım akışını gözlemler | `sonnet` | `high` | Hayır |
| Son inceleyici | Değişmeyen son hâli bağımsız inceler | `opus` | `high` | Hayır |
| Danışman | Riskli tek bir karar için görüş verir | `opus` | `xhigh` | Hayır |

Bu adlar tarihli bir model sürümünü sabitlemek yerine güncel Claude ailesini seçen kısa adlardır. Model erişimi ve desteklenen düşünme düzeyleri hesabınıza ve güncel Claude Code istemcinize bağlıdır. Ortam değişkenleri ile oturum veya çalıştırma sırasında verilen seçenekler proje ayarlarının önüne geçebilir; yardımcı dosyalarındaki ayarlar desteklendiği yerde hedeflenen rol dağılımını uygular.

## Desteklenen sistemler ve sınırlar

Kurulum ve paket oluşturma araçları Python 3.11 standart kütüphanesini kullanır. macOS/Linux için kabuk dosyaları, Windows için PowerShell ve cmd dosyaları bulunur. Otomatik kontroller macOS, Windows ve Ubuntu üzerinde kurulum, görev listesi ve paketleme davranışını sınayacak şekilde hazırlanmıştır.

Talimatlar tek başına kesin bir güvenlik sınırı değildir. Yardımcı derinliği ve araç listeleri Claude Code'un somut kontrolleridir; rol sırası, tek uygulayıcı kuralı, son hâli sabitleme ve sınırlı tekrar kuralları ise modelin izlemesi gereken talimatlardır. `Bash`, `Edit` ve `Write` olmasa bile değişiklik yapabilir; bu nedenle kontrol rollerine yalnızca kanıt toplamak için kullanma talimatı verilir. Depo, kurulum, API ve tarayıcı kontrolleri canlı Claude Code oturumunun yerini tutmaz. macOS uygulaması ve Windows çift tıklama başlatıcısı her iki işletim sisteminde de yerel arayüzden açılarak doğrulanmadı.

## Belgeler

- [Mimari ve güvenlik gerekçesi](docs/architecture.md)
- [Kullanım örnekleri](docs/examples.md)
- [Sık sorulan sorular ve sorun giderme](docs/faq.md)
- [Yol haritası](docs/roadmap.md)
- [Canlı deneme rehberi](docs/runtime-smoke-test.md)
- [v0.4.0 sürüm notları](docs/release-v0.4.0.tr.md)
- [Kullanım raporu ve isteğe bağlı yerel değerlendirme](docs/usage-and-local-eval.tr.md)
- [v0.5.0 sürüm notları](docs/release-v0.5.0.tr.md)
- [v0.3.1 sürüm notları](docs/release-v0.3.1.tr.md)
- [v0.3.0 sürüm notları](docs/release-v0.3.0.tr.md)
- [v0.2.0 sürüm notları](docs/release-v0.2.0.tr.md)
- [macOS/Linux kurulumu](INSTALL-MACOS.md)
- [Windows kurulumu](INSTALL-WINDOWS.md)
- [Katkı rehberi](CONTRIBUTING.md) · [Güvenlik](SECURITY.md) · [Değişiklikler](CHANGELOG.md)

## Projenin durumu

`0.5.0`; sınırlı çalışma düzeni, gerçek yardımcı ekibi kuran yerel tarayıcı ekranı, isteğe bağlı OpenTelemetry kullanım görünümü, son dosyalara bağlı yerel değerlendirme ve devam ettirilebilir görev denemeleri sunar. Orkestradaki bilinen görevlerin karakterleri ayrıdır. Şefe tıklayınca hareket başlar, başka yere tıklayınca durur. Sahne canlı çalışma, bağlam doluluğu veya kalan kota yerine gözlenen token paylarını gösterir. Sınırlı inceleme düzeni ve isteğe bağlı, yalnız öneri üreten haricî sağlayıcılar korunur. Proje, [Codex Bounded Orchestrator](https://github.com/metapak/codex-bounded-orchestrator) çalışma düzenini Claude Code'un proje yardımcılarına, becerilerine, ortak talimatlarına ve ayarlarına uyarlar. Atıflar için [NOTICE](NOTICE) ve [kaynak bilgisi](docs/provenance.md) belgelerine bakabilirsiniz.

Proje işinize yararsa vereceğiniz bir GitHub yıldızı daha fazla kişinin projeyi bulmasına yardımcı olur. Hata bildirimleri ve odaklı katkılar memnuniyetle karşılanır.

## Lisans

Apache License 2.0. Ayrıntılar için [LICENSE](LICENSE).

## Yerel tarayıcı konsolu

```sh
python3 scripts/configure.py /path/to/project
```

[Tercihler, Kullanım ve Çalışmalar](docs/local-console.tr.md): npm gerektirmez; önizleme, açık Kur/Kaydet, geri alma ve isteğe bağlı yerel kullanım analizi. Planlanan ekip ile geçmişte gözlenen kullanım ayrıdır; bilinmeyen ajan kimliği veya geçmiş düşünme düzeyi uydurulmaz.
