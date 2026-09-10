[English](release-v0.2.0.md) | [Türkçe](release-v0.2.0.tr.md)

# Claude Bounded Orchestrator v0.2.0

0.2.0 sürümü, tarihli model kimliklerini sabitlemeden her rol için hedeflenen Claude model ailesini ve düşünme düzeyini açıkça belirtir.

## Görev dağılımı

| Rol | Model kısa adı | Düşünme düzeyi |
|---|---|---|
| Ana yönetici | `opus` | `xhigh` |
| İnceleyici | `sonnet` | `medium` |
| Araştırmacı | `sonnet` | `medium` |
| Uygulayıcı | `sonnet` | `high` |
| Kontrolcü | `sonnet` | `high` |
| Kullanım kontrolcüsü | `sonnet` | `high` |
| Hata çözümleyici | `opus` | `high` |
| Son inceleyici | `opus` | `high` |
| Danışman | `opus` | `xhigh` |

## Güncelleme davranışı

Yeni kurulumda ana yöneticinin varsayılanları `.claude/settings.json` dosyasına yazılır. Bu dosya zaten varsa kurulum onu korur ve elle inceleyip birleştirmeniz için `.claude/bounded-orchestrator.settings.example.json` oluşturur. Yardımcı dosyalarında çakışma varsa `--force` açıkça seçilmedikçe mevcut dosyalar korunur.

Ortam değişkenleri ile oturum veya çalıştırma sırasında verilen seçenekler proje ayarlarının önüne geçebilir. Yardımcı dosyalarındaki ayarlar, desteklendiği yerde hedeflenen rol dağılımını belirtir; ortam düzeyindeki efor ayarı daha yüksek önceliğe sahip olabilir. Kullanılabilen modeller ve efor düzeyleri hesaba ve güncel Claude Code istemcisine bağlıdır.

## Doğrulama sınırı

Statik doğrulama ve testler, ayarlar ile belgelerin yardımcı tanımlarından sessizce uzaklaşmaması için görev dağılımının tamamını kontrol eder. Gerçek model seçimi Claude Code çalışma zamanına bağlıdır ve belgelenen canlı deneme ile doğrulanmalıdır.
