<!-- source: c1b2511ee47c687e -->

## Random New World

Europa Universalis V için bir Yeni Dünya oluşturucu. Amerika kıtalarını baştan yaratır: kıtalar, kıyılar, yeryüzü şekilleri, iklim, nehirler, bitki örtüsü, kaynaklar, eyaletler ve yerli halklar. Eski Dünya'yı ise Paradox nasıl yaptıysa öyle bırakır. **Yarattığı her dünya kendi başına eksiksiz bir harita modudur.** Tek başına oynanır: istediğiniz kadar dünya saklayın, silin ya da bir dünyanın kodunu paylaşın. Dünya bu oluşturucu olmadan da oynanır; oyunun aynı sürümüne sahip herkes koddan aynı dünyayı elde eder.

Bu öğeyi hiçbir oynanış setinde etkinleştirmeniz gerekmez. İçinde yalnızca oluşturucu var.

## Bu öğede neden bir program var

EU5, modları yüklerken haritasını dosyalardan kurar. Mod veridir: kod çalıştıramaz. Oyunun betiği başlangıçta neyin kime ait olacağını belirleyebilir ama kara, dağ ya da nehir yaratamaz. EU5'te oyuna kod eklemenin resmî bir yolu yoktur.

Bu yüzden dünyayı, bu öğeyle gelen küçük bir program yaratır. EU5 kurulumunuzu okur, bir dünya oluşturur ve onu sıradan bir mod olarak kaydeder. Oyunu değiştirmez, oyuna bağlanmaz ve oyunun içinde çalışmaz. Paradox'un kullanıcı sözleşmesi, programları oyuncuların ücretsiz yapıp paylaşabileceği içerikler arasında sayar.

## Nasıl kullanılır

1. **Modlar** penceresinde Random New World'ün yanındaki **Klasörde Aç** düğmesine basın ve **Random New World Generator** dosyasına çift tıklayın.
2. Bir dünya türü seçin: süper kıta, kıtalar, küçük kıtalar, takımada ya da dağınık adalar. Rastgele tohumu bırakın, kendiniz bir tohum yazın ya da bir dünya kodu yapıştırın. **Temel ayarlar**, EU4'ün rastgele Yeni Dünyası gibi, alışılmış soruları tek kelimeyle yanıtlar: ne kadar kara, kaç yerli halk ve devlet, büyük bir yerli imparatorluğun ne sıklıkla doğacağı (asla, seyrek, bazen, sık) ve altın ile gümüşün ne kadar bol olacağı. **Özelleştir** altında her değeri değiştirebilirsiniz: kara, kıyılar, harita ölçeği ve büyük imparatorluklardan tek başına devletlere kadar yerli halklar. Sunulan her değer oynanabilir bir dünya verir.
3. **Oluştur** düğmesine basın. İki üç dakika içinde dünya, mod listenizde "RNW: Small continents 7K3Q" gibi bir adla (dünya türü ve etiketi) yeni bir mod olarak belirir; oluşturucuda adını değiştirebilirsiniz. Yeni Dünya gizli olduğu sürece mod listesindeki resminde aynı etiket kırmızıyla yazar, böylece dünyalar birbirine karışmaz.
4. Oyunda bu dünyayı işaretleyin (aynı anda yalnızca bir dünya) ve yeni bir oyun başlatın. EU5'i açtıktan sonra bir kampanya oynadıysanız önce EU5'i yeniden başlatın. Ne yapmanız gerektiğini oluşturucu tam olarak söyler.

Oluşturucu, yarattığınız her dünyayı koduyla birlikte saklar. **Ayarlar**'da göstermeyi seçene dek Yeni Dünya, siz oynamadan önce her yerde terra incognita olarak kalır: oluşturucunun resimlerinde, oyunun mod listesinde ve oyunun yeni oyun ekranındaki haritada. Tek bir ayar bunların hepsini kapatır. Dünya kodu, aynı oyun sürümüne sahip her bilgisayarda aynı dünyayı bayt bayt yeniden yaratır.

Oluşturucu oyunun bütün dillerini konuşur ve Steam'in EU5'i çalıştırdığı dilde açılır.

## Program ne yapar, ne yapmaz

- EU5 kurulumunuzu okur ve yalnızca iki yere yazar: yarattığı dünya modlarına (Belgeler'deki EU5 klasöründe `mod/rnw_world_…`) ve kendi veri klasörüne.
- Ağı kullanmaz, yönetici hakları istemez, kayıt defterine dokunmaz ve oyunun hiçbir dosyasını değiştirmez.
- Kaynak kodu Mozilla Public License 2.0 ile herkese açıktır: https://github.com/Sir-Starch/eu5-random-new-world. Her sürüm, etiketlenmiş bir commit'ten otomatik olarak derlenir ve her dosyanın SHA-256 sağlama toplamı orada yayımlanır.
- Bir programa güvenip güvenmemek sizin kararınızdır. Kodu okuyabilir, sağlama toplamlarını karşılaştırabilir ya da programı kendiniz derleyebilirsiniz.

## Windows uyarıları

- Steam'in indirdiği dosyalar internetten gelmiş olarak işaretlenmez, bu yüzden Windows SmartScreen'in bir şey sorması beklenmez. [Confirm in 020.]
- Virüs programları bazen henüz tanımadıkları yeni programlara alarm verir. Her sürümün sayfasında o sürümün VirusTotal taramasına bağlantı vardır.
- Windows 11'in Akıllı Uygulama Denetimi, bilinen bir imzası olmayan programları engeller ve Windows tek bir program için istisna tanımaz. [Until signed:] Oluşturucu henüz imzalı değil, bu yüzden Akıllı Uygulama Denetimi açıkken başlamaz. [Once signed:] Oluşturucu ve yerel modülü [signer] tarafından imzalanmıştır.

## Linux ve Steam Deck

Oyun Proton üzerinden çalışır. Klasörde Aç bu durumda Wine'ın dosya gezginini açar ve aynı oluşturucu orada, oyunun kendi Proton önekinde çalışır. Hiçbir şey kurmanız gerekmez. [Steam Deck: confirm.]

## Sınırlar

- **Yalnızca yeni kampanyalar.** Dünya, kampanya başlamadan önce oluşturulmalıdır.
- **Oynamadan önce oluşturun ya da yeniden başlatın.** Aynı oturumda bir kampanyanın ardından başka bir dünya başlarsa EU5 çöker (çökme oyun motorundadır). EU5'i açar açmaz oluşturmak yeniden başlatma gerektirmez; bir kampanyadan sonra yeni dünyadan önce EU5'i yeniden başlatın.
- **Oyun güncellemeleri.** EU5 güncellendikten sonra oluşturucu, yeni sürüme uyarlanana dek çalışmayı reddedebilir. Ardından dünyanızı yeniden oluşturmayı önerir. Eski kayıtlar, oynandıkları dünyaya ihtiyaç duyar: o dünyayı kodundan yeniden oluşturun.
- **Aynı anda tek dünya.** Bir oynanış setinde yalnızca bir oluşturulmuş dünyayı işaretleyin.
- **Çok oyunculu.** Her oyuncu aynı dünya kodunu, aynı oyun sürümüyle kullanır.
- **Bellek.** İki dakikalık oluşturma için yaklaşık 7,5 GB boş bellek. EU5 için önerilen 32 GB fazlasıyla yeter.
- **Başarımlar.** Oyunu değiştiren diğer modlar gibi, oyunun sağlama toplamını değiştirir. [Confirm what EU5 allows.]

## Kaldırma

Dünyaları oluşturucuda silin (**Dünyayı sil**) ya da klasörlerini kendiniz kaldırın, sonra aboneliği iptal edin. Sakladığınız dünyalar oluşturucu olmadan da oynanabilir kalır.

## Lisans ve emeği geçenler

Kod ve mod dosyaları: Mozilla Public License 2.0. Dünyalar, sizin EU5 kopyanızdan sizin bilgisayarınızda yaratılır ve Atölye üzerinden dağıtılmaz. Europa Universalis V, Paradox Interactive'in ticari markasıdır; bu modun Paradox Interactive ile bir bağlantısı yoktur.
