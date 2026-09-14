[English](usage-and-local-eval.md) | [Türkçe](usage-and-local-eval.tr.md)

# Kullanım raporu ve isteğe bağlı yerel değerlendirme

Araç Claude konuşma dosyalarını okumaz ve telemetriyi açmaz. Açıkça verilmiş, temizlenmiş bir OpenTelemetry dışa aktarımı yoksa `unavailable` gösterir; Claude Code içindeki `/usage` elle kontrol seçeneğidir.

```bash
python .claude/tools/usage_report.py
python .claude/tools/usage_report.py --input temiz-otlp.json --json
```

Yalnız verilen OTLP JSON veya JSONL içindeki token/maliyet ölçüm noktaları özetlenir. Sonuçlar kendiliğinden kota yüzdesi veya fatura toplamı sayılmaz.
Yalnız delta veya kümülatif türü açıkça belirtilmiş OTLP Sum ölçümleri kabul edilir. Delta değerleri toplanır; kümülatif değerler kaynak/özellik akışına göre fark alınarak hesaplanır ve düşen değer sayaç sıfırlaması sayılır. Türü belirsiz ölçümler atlanır ve raporlanır.

`.claude/bounded-orchestrator.eval.example.json` dosyasını kopyalayıp açık `argv` listesini düzenleyin ve aracı kendiniz çalıştırın:

```bash
python .claude/tools/local_eval.py .claude/local-eval.json
python .claude/tools/task_ledger.py require-eval --label focused-tests
python .claude/tools/task_ledger.py check
```

Kabuk kullanmayan araç süre sınırıyla çalışır ve Git tarafından yok sayılan özet değerini kaydeder. Evrensel kalite ölçümü değildir. Ledger sabit deneme/olay geçmişi, kesinti durumları, tek sınırlı yeniden deneme ve sorumluya geri yönlendirme bilgisini tutar.
Her başarılı sonuç, HEAD ile ilgili izlenen ve yeni çalışma dosyalarının gizlilik koruyan parmak izine bağlanır. Sonraki bir değişiklik sonucu geçersiz kılar; sonuç dosyasının kendisi parmak izinden çıkarılır.
