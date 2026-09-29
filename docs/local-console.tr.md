# Yerel tarayıcı konsolu

İndirilen/klonlanan kurulum deposundan çalıştırın:

```sh
python3 scripts/configure.py /proje/yolu
python3 scripts/configure.py /proje/yolu --no-browser --port 8765
```

Python 3.10+ yeterlidir; npm gerekmez. Tarayıcı varsayılan olarak açılır. Terminaldeki özel token içeren URL'yi kullanın; Ctrl+C ile durdurun. Başlatıcı bu kurulum deposundadır: daha sonra ayar değiştirmek için depoyu saklayın. Hedef, var olan bir proje klasörüdür; kullanıcı geneline kurulum desteklenmez.

**Ayarlar** seçilen projenin rol modeli/effort değerlerini, hazır profilleri ve eşzamanlılık sınırını gösterir. Önizleme dosya yazmaz. Kaydet ilk kez kullanıldığında mevcut kurulum aracıyla araç takımını kurar, ardından seçilen ayarları uygular; bu durum önizlemede belirtilir. Çakışan rol dosyaları varsa işlem durur. İlgisiz JSON alanları, izinler ve ortam değişkenleri korunur; tam ayar dosyası veya anahtarlar API'ye aktarılmaz. Kurulum aracının sahiplik ve yedek kuralları kullanılır. Önceki konsol güncellemesi geri alınabilir; Kaydet sonrası dışarıdan değişen dosyada geri alma reddedilir. İlk Kaydet sonrası geri alma araç takımını kurulu bırakır; kaldırma için mevcut uninstall komutunu kullanın. Birleştirilen ortak settings.json kaldırma işleminde korunur. Claude Code'u yeniden başlatın.

Görünen değerler proje dosyalarıdır; managed/local ayarlar, ortam, CLI ve mevcut oturum bunları geçersiz kılabilir. Eşzamanlılık `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` ile yazılır; Claude Code 2.1.217+ gerekir. Ultracode sınırı uygulamaz ve devam ettirilen ajanlar sınırı aşabilir. Konsol 1–20 aralığını kabul eder. Varsayılan politika tek uzmandır. Kısa rapor, bağlam ve yeniden deneme tercihleri kesin token bütçesi değildir. Reviewer için `omitClaudeMd: true` Claude Code 2.1.271+ gerektirir; ilgili politika ve sınırlar görev özetinde tekrar verilmelidir.

**Kullanım** yalnız açıkça seçtiğiniz yerel temizlenmiş OTLP JSON/JSONL dosyasını okur; telemetriyi açmaz. Delta/kümülatif Sum ölçümleri, bağımsız sayaçlar, sıfırlamalar ve tarih sırası dikkate alınır. Yinelenen dışa aktarımlar ve aynı zaman damgalı ölçümler sayılmaz; tek belgede zaman damgasız eşit delta ölçümler ayırt edilemez. Tarih filtresi UTC gözlem tarihini kullanır, tarihsiz noktaları çıkarır ve önceki kümülatif tabanı korur. Artışlar tarih sınırını aşabilir. Model/tarih/oturum/ajan ancak dosyada varsa görünür. Gerçek input/output/cacheRead/cacheCreation değerleri gösterilir. Kaynak maliyet ölçümü ayrı raporlanır; fiyat tahmini ve abonelik kotasına dönüşüm yapılmaz. En fazla 32 MiB okunur.

Model grafiği yalnız `claude_code.token.usage` ölçümünü kullanır; ana toplam okunan ve yazılan metindir. Önbellekten okunan ve önbelleğe alınan metin ayrı kalır, toplama ikinci kez eklenmez. Standart Claude Code OTLP verisinde proje veya çalışma biçimi bulunmaz; bu durumda grafik “Bilgi yok” der. Konsol kendi Kaydet/Geri al işlemlerinin zamanını, profil adını, proje yolu özetini ve kurulum kaydı özetini özel, Git tarafından yok sayılan bir dosyada tutar; anahtar veya konuşma saklamaz. Çalışma biçimi ancak dosyada ayrıca `project.path` varsa, oturumda tek bir `fresh` `claude_code.session.count` başlangıcı varsa ve gözlenen bütün token ölçümleri tek bir kayıtlı ayar aralığına uyuyorsa “ayar geçmişine göre tahmin” olarak gösterilir. Belirsiz, eski veya konsol dışından değişmiş oturumlar “Bilgi yok” kalır. Tarih filtresi bu tam oturum kontrolünü gevşetmez. Örnek grafik gerçek kullanım değildir.

**Görev Ayrıntıları** gerçek proje görev defteri metadatasını gösterir; defter yoksa açıkça veri yoktur. Konuşmalar okunmaz, görev veya görev token/maliyetleri uydurulmaz.

Sunucu yalnız 127.0.0.1'e bağlanır; Host/Origin doğrular, API için özel token, yazma için aynı kaynaktan JSON POST ister. İstek boyutu sınırlıdır; istekten kabuk komutu çalıştırmaz. [Teknik ayrıntılar ve resmi Anthropic kaynakları](local-console.md). Yerel doğrulamada Claude CLI bulunmadığı için canlı oturum entegrasyonu doğrulanmadı.
