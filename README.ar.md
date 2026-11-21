# Mesin Bahts — آلة البحث

**اللغة:** [English](README.md) · [Indonesia](README.id.md) · العربية

<p dir="rtl"><strong>Mesin Bahts (آلة البحث) عُدّة للوكلاء البرمجيين (Claude Code وCodex وOpenCode ونحوها) لكتابة البحث الشرعي باللغة العربية: يُطابَق كل نقل بصفحة كتاب المكتبة الشاملة (Shamela) المحال عليها، ثم يُخرَج نص البحث ملفَّي Word وPDF.</strong></p>

<img src="dok/banner.jpg" width="100%" alt="طالبة محجبة في مكتبة تتطاير حولها الكتب">

[![الاختبار](https://github.com/Farisarditiyanto/mesin-bahts/actions/workflows/tes.yml/badge.svg)](https://github.com/Farisarditiyanto/mesin-bahts/actions/workflows/tes.yml)
[![الإصدار](https://img.shields.io/github/v/release/Farisarditiyanto/mesin-bahts?label=%D8%A7%D9%84%D8%A5%D8%B5%D8%AF%D8%A7%D8%B1)](https://github.com/Farisarditiyanto/mesin-bahts/releases)
[![الترخيص](https://img.shields.io/badge/%D8%A7%D9%84%D8%AA%D8%B1%D8%AE%D9%8A%D8%B5-AGPLv3%2B-blue)](LICENSE)

<div dir="rtl">

يكتب الوكيلُ البحثَ في `naskah.txt`، لكل بحث مجلد. يرفض `cek` كل نقل لا يوجد في صفحة الكتاب المحال عليها، ثم يُخرج `rakit` نصَّ البحث ملفَّي Word وPDF.

هذا الملف خريطة للوكيل. يكفي المستخدمَ أن يلصق رابط هذا المستودع في [وكيل برمجي](#الوكلاء-والموصلات) (coding agent)، ثم يجيب عن أسئلته.

| | |
|---|---|
| لمن | وكيل برمجي يستطيع تشغيل الأوامر؛ والمستخدم طالب يكتب بحثًا |
| قواعد العمل | [`AGENTS.md`](AGENTS.md) (بالإندونيسية) |
| مدخل الأوامر | `python mesin/bahts.py <perintah>` |
| المسار | `baru` ← جمع المادة ← `ambil` ← كتابة `naskah.txt` ← `cek` ← `rakit` ← المراجِع ← إعادة `cek` و`rakit` |
| موصِّلات MCP | `shamela` (إلزامي)، `qurangallery`، `turath`، `hadithunlocked`، `tafsir`، `quran` |
| المتطلبات | يذكرها `python mesin/bahts.py periksa`؛ ويحتاج `rakit` إلى Windows وMicrosoft Word |
| الإصدار | [الإصدارات](https://github.com/Farisarditiyanto/mesin-bahts/releases)، [`CHANGELOG.md`](CHANGELOG.md) |
| الترخيص | AGPLv3 أو ما بعدها ([`LICENSE`](LICENSE)) |

الأوامر والعلامات ومخرجات البرنامج بالإندونيسية، وتُذكر هنا كما تُكتب أو تُطبع. معاني ما يرد منها: bahts = البحث، naskah = نص البحث، kitab = الكتاب، `GAGAL` = فشل، perhatian = تنبيه، `BELUM` = لم يتم بعد، `BERIKUTNYA` = الخطوة التالية.

## البداية

1. اقرأ [`AGENTS.md`](AGENTS.md) (بالإندونيسية) كاملًا: هو قواعد العمل. ابدأ من قسم «Pemakai baru».
2. شغِّل `python mesin/bahts.py periksa` (في Linux/macOS: `python3`). عالج كل سطر `BELUM` بالأمر الذي يذكره.
3. تأكد أن الموصِّل `shamela` متصل، أي أن الأداة `shamela_search_phrase` موجودة. طريقة تسجيله والدخول في كل وكيل: `AGENTS.md` قسم «Pemakai baru» الخطوة 4.
4. جلسة لاحقة، أو لا تعرف أين وصل البحث: `python mesin/bahts.py tahap <folder>`، واتبع سطر `BERIKUTNYA`.

إن لم يكن المستودع على الحاسوب: شغِّل هذه الأوامر من مجلد المستندات عند المستخدم، قبل الخطوة 2. المجلد الذي يُنزَّل إليه المستودع والطريقة بلا `git`: `AGENTS.md` «Pemakai baru» الخطوة 1.

<div dir="ltr">

```bash
git clone https://github.com/Farisarditiyanto/mesin-bahts
cd mesin-bahts
python mesin/bahts.py periksa
```

</div>

متطلبات الحاسوب وطريقة معالجتها في مكان واحد: `python mesin/bahts.py periksa`. يحتاج `rakit` إلى Windows وMicrosoft Word المكتبي؛ ويمكن في Linux/macOS الكتابة و`cek` دون Word وPDF. جمع المادة يحتاج الموصِّل `shamela` (حساب shamela.link)، والدراسات السابقة تحتاج مفتاح OpenAlex (`AGENTS.md` «Pemakai baru» الخطوة 6).

### الوكلاء والموصلات

| الوكيل | يقرأ قائمة الموصِّلات من |
|---|---|
| [Claude Code](https://claude.com/claude-code) (ومنه تبويب Code في تطبيق Claude) | `.mcp.json`، مع قائمة Connectors في تطبيق Claude |
| [OpenCode](https://opencode.ai) (مجاني) | `opencode.json` |
| [Command Code](https://commandcode.ai) | `.mcp.json`، مع مُدخَل `shamela` محلي يحمل `clientId` |
| Codex (سطر الأوامر والتطبيق) | يسجِّله الوكيل |
| [Hermes Agent](https://hermes-agent.nousresearch.com) (مجاني) | يسجِّله الوكيل |

- أوامر تسجيل `shamela` والدخول لكل وكيل: `AGENTS.md` «Pemakai baru» الخطوة 4 (وهو مكانها الوحيد).
- النماذج المجانية أكثر خطأً في الخطوات، فالمراجِع في الخطوة 5 أهم.
- الموصِّلات: `shamela` إلزامي؛ و`qurangallery`، `turath`، `hadithunlocked`، `tafsir`، `quran` بلا حساب. فائدتها وترتيب البدائل: `AGENTS.md` الخطوتان 4-5 و«Alur kerja» الخطوة 2. أرقام اختبار كل موصِّل، ومنها خادم MCP الرسمي لـshamela.ws الذي لم يُثبَّت عمدًا: [`dok/uji-riset.md`](dok/uji-riset.md).
- كل الموصِّلات دلالة على الطريق فقط: الكتاب يُنزَّل بـ`ambil`، والنقل يجب أن يجتاز `cek`.

### بلِّغ المستخدم

- الاسم على الغلاف اسمه، فهو المسؤول عن المحتوى، وعليه أن يسأل أستاذه هل يُسمح بالاستعانة بالذكاء الاصطناعي.
- `cek` لا يغني عن القراءة: اطلب منه أن يراجع بنفسه أهم النقول.
- بعض النماذج المجانية تستعمل المحادثة في تدريب نماذجها.
- هذا المشروع لا يمثل أي جامعة.

### الحدود

- ليس لوضع المحادثة العادي (Claude chat، ChatGPT): لا بد أن يستطيع الوكيل تشغيل الأوامر على حاسوب المستخدم.
- ليس ضمانًا للمحتوى: `cek` يثبت فقط أن النص موجود في ذلك الجزء/الصفحة. أما القائل وسياق الباب وجودة المصدر فيحكم فيها المراجِع في الخطوة 5 (`AGENTS.md` «Alur kerja»).
- ليس للبحوث بغير العربية: شكل الصفحة والتوثيق والفهارس على قواعد البحث العربي ([معيار الصفحة](#معيار-الصفحة)).
- ليس محرِّر نصوص: يُعدَّل المحتوى من `naskah.txt` لا من ملف `.docx`.
- بلا Windows وMicrosoft Word لا يخرج Word ولا PDF، ولا يُستعمل بديل عن Word.

## طريقة العمل

| الخطوة | الأمر | الناتج |
|---|---|---|
| إنشاء المجلد | `baru <folder> "<judul>"` | `naskah.txt` (هيكل نص البحث)، `riset.txt` |
| جمع المادة | الموصِّل `shamela_*`، `temukan`، `katalog`، `hadits`، `dirasat`؛ ودون إنترنت: `tafsir <surat:ayat>`، `takhrij <id> <juz> <hal>`، `rawi <id> <juz> <hal>`، `akar <id> "<الجذر>"`؛ والكتاب الذي ليس في الشاملة: `waqfeya "<العنوان>"` | رقم الكتاب والجزء/الصفحة (دلالة فقط) |
| تنزيل الكتاب | `ambil <id>` أو `ambil <folder>`؛ الوقفية: `ambil w<nomor>` | `kitab/<id>/`، `kitab/waqfeya/w<nomor>/` |
| بيانات النشر | `kartu <id>` | التوثيق الأول والمصادر |
| قراءة النص | `cari`، `teks`، `bab`، `halaman` | نص محلي يُنسخ كما هو |
| الفحص | `cek <folder>` (و`--jejak` للنقل غير الموجود) | `GAGAL: n`، تنبيهات، `NASKAH_SHA256` |
| المراجِع | `bukti <folder> [awal-akhir]` | نص الصفحة حول كل حاشية (الشاملة، والوقفية، وملفات PDF البحثية)، والفقرات التي بلا حاشية |
| الإخراج | `rakit <folder> [--fasl n]` (Windows + Word) | `.docx` + `.pdf` (الغلاف، الحواشي، المصادر والمراجع، الفهارس)، `HALAMAN_ISI`، `HALAMAN` |
| الحالة | `tahap <folder>` | `NASKAH=`، `HASIL=`، `RAKIT=`، `BERIKUTNYA` |
| المخططات | `diagram <folder>` (Node.js + Chrome/Edge) | كل `<nama>.mmd` (Mermaid) يصير `<nama>.png`، ويطبع بـ`#G` |
| المعاينة البصرية | `pratinjau <folder> [halaman]` | صفحات ملف PDF الناتج صورًا شبكية 2×2 من نوع PNG في TEMP (أو صفحة واحدة) لمراجعة التنسيق |

كل الأوامر = `python mesin/bahts.py <perintah>`. القائمة الكاملة ومعاملاتها: `python mesin/bahts.py`. علامات نص البحث (`#F`، `{Q:}`، `{H:}`، `@format`، …): `python mesin/bahts.py tanda`. نص بحث نموذجي يجتاز `cek`: [`contoh/naskah.txt`](contoh/naskah.txt) (`ambil 11223` ثم `cek contoh`).

### ما يثبته `cek`

- كل نقل بين علامتي تنصيص يجب أن يُقرأ في الجزء/الصفحة من الكتاب المحال عليه. إن لم يوجد هناك، أو كان بلا عنوان = `GAGAL`.
- الجزء/الصفحة المطبوعان في الحاشية يُطابَقان بعنوان الدليل. واسم الكتاب في الحاشية يجب أن يوافق دليله، ودرجة الحديث في التخريج يجب أن تُقرأ في صفحة الدليل. والنقل من حاشية المحقق، أو ما تسبقه في الكتاب عبارة «قال …» منسوبةً إلى غير المؤلف، يصير تنبيهًا.
- الآيات والأرقام داخل النقل تُطابَق بورودها كلماتٍ تامة في صفحة الدليل؛ ولا يُحتسب رقم من صفحة مجاورة.
- الآيات تُطبع من مصحف حفص بالرسم العثماني (`mesin/quran_hafs_v22.json`) عبر `{Q:surah:ayat}`. الآية المكتوبة باليد بين ﴿…﴾ مع إحالة «سورة …» = `GAGAL`، وبلا إحالة = تنبيه. والآية بلا ﴿…﴾ بعد «قال الله تعالى» المحالة على «سورة …» = `GAGAL` أيضًا.
- `<<sid|juz|hal|#123>>` لا يجتاز إلا إذا كان 123 رأس حديث في أول سطر من تلك الصفحة («123 - حدثنا»، «36 - (123)»، «(123) - حدثنا»)؛ وتُرفض أرقام الآيات والحواشي. وهذا يثبت وجود الرقم لا اللفظ.
- التخريج «رقم الحديث (123)، 4/56.» المتبوع مباشرة بدليل: يجب أن يكون الرقم رأس حديث قرب تلك الصفحة، وأن يكون لفظ الدليل في الحديث ذي الرقم نفسه. والنتيجة تنبيه لا `GAGAL`.
- `cek --jejak`: النقل غير الموجود يُبحث عنه في الكتب المنزَّلة الأخرى، بحدٍّ أقصى 3 كتب لكل نص؛ واللفظ المختلف قليلًا يُشار إليه بـ«Paling mirip»؛ والنقل الممتد إلى الصفحة التالية يُذكر مداه (ص21-22). وهي دلالة فقط. الكتاب الذي تتعذر قراءته يُتجاوز مع تحذير «jejak belum lengkap». أول بحث يُهيِّئ نص الكتاب، فقد يطول.
- المصادر خارج الشاملة: `<<luar|berkas.pdf|hal>>` يُشار إلى صفحتها فقط، ولا تُجاز أبدًا. كتب الوقفية `<<w…|berkas|hal>>`: لا يحكم `cek` على لفظها لأن النص المستخرج آليا فيه أخطاء حروف؛ يقرؤه المراجِع في المصورة. و`GAGAL` فقط إذا لم يُنزَّل الكتاب، أو لم توجد الصفحة، أو وُجد النقل بنصه في صفحة أخرى.
- طرق النقل (تنبيه perhatian، لا `GAGAL`): جملة خارج علامتي التنصيص توافق صفحة الدليل في ثماني كلمات متتالية فأكثر، ونقل بالمعنى بلا «انظر:»، واقتباس نصي مسبوق بـ«قال …:» فقط وموثق بـ«انظر:»، واقتباس يزيد على ستين كلمة. وحدّ الكلمات من قواعد المستودع. أما مطابقة النقل بالمعنى لصفحة الدليل فلا يُحكم فيها: الدليل ذو القطعة لا يثبت إلا قطعته.
- تخريج حديث خارج الصحيحين بلا درجة (وبلا «ولم أقف على حكم …») = `GAGAL`.
- كل تنبيه (perhatian) يجب التعامل معه: يُطبع كل سطر برمزه («! 3f9a2c baris …»)، ثم يُصلَح في النص، أو يُقبَل بسطر `terima <الرمز> <السبب>` في `riset.txt` إن تعذر إصلاحه. وما دام فيه تنبيه لم يُتعامل معه يطبع `tahap` القيمة `NASKAH=PERHATIAN` ويطبع `rakit` «BELUM SELESAI». ولا تُقبَل تنبيهات `riset.txt`. ولا تحكم الآلة في السبب: ذلك عمل المراجِع في الخطوة 5.
- ما لا يقدر `cek` على الحكم فيه (القائل، كون الكتاب معتمدًا، النقل بلا حاشية): آخر «Alur kerja» في `AGENTS.md`، وهو عمل المراجِع في الخطوة 5.

لا يستعمل `cek` ولا `rakit` الإنترنت ولا الموصِّلات: يجب أن تكون نتيجتهما واحدة بلا شبكة.

### معيار الصفحة

- الأساس «[القواعد المنظمة لتسجيل الرسالة العلمية وكتابتها وطباعتها وتقديمها](https://units.imamu.edu.sa/colleges/cmc/AcademicDepts/SiteAssets/Pages/d_j_e_p/%D8%A7%D9%84%D9%82%D9%88%D8%A7%D8%B9%D8%AF%20%D8%A7%D9%84%D9%85%D9%86%D8%B8%D9%85%D8%A9%20%D9%84%D8%AA%D8%B3%D8%AC%D9%8A%D9%84%20%D8%A7%D9%84%D8%B1%D8%B3%D8%A7%D9%84%D8%A9%20%D8%A7%D9%84%D8%B9%D9%84%D9%85%D9%8A%D8%A9.pdf)» (جامعة الإمام، 1442هـ) وملاحظات أستاذ مادة البحث في معهد العلوم الإسلامية والعربية في جاكرتا. مصدر كل قاعدة: [`dok/standar.svg`](dok/standar.svg).
- إذا طلب الأستاذ شكلًا آخر: `AGENTS.md` «Sebelum tiap bahts» (`@format`، `@templat`، `@sampul`، `@spasi`، `@catatan_kaki`). لا تُعدَّل ملفات `mesin/` في مجلد المستخدم؛ والنمط الجديد في `mesin/format.json` تعديلٌ للآلة.
- الأرقام: لا تذكر قواعد الجامعة ولا ملاحظات الأستاذ نوع الأرقام. والنماذج الرسمية للجامعة تستعمل ٠١٢٣ في أرقام الصفحات والحواشي والإحالات والسنوات وأرقام الآيات والفهارس: «[دليل إعداد وكتابة الرسائل العلمية](https://units.imamu.edu.sa/shis/sij/FilesLibrary/Documents/Guide%20to%20preparing%20and%20writing%20scientific%20theses.pdf)» (جامعة الإمام، الطبعة الثانية) و«[مجلة العلوم الشرعية](https://journals.imamu.edu.sa/index.php/jis)». لذلك يطبع PDF الأرقام ٠١٢٣ في كل تلك المواضع أيًّا كان ما كُتب في نص البحث. والروابط وDOI (`https://…`، `www.…`، `doi.org/…`، `10.xxxx/…`) تُطبع من اليسار إلى اليمين كما هي.
- الحروف اللاتينية داخل النص العربي: لم يذكر المصدران حجمها. قواعد 1442 لا تذكر إلا الخط العربي؛ و[دليل 2022](https://units.imamu.edu.sa/deanships/GRADUATE/circulations/Documents/Law3A.pdf) للجامعة نفسها يكتب الرسائل المحررة بالإنجليزية بخط Times New Roman بحجم 14 (الحاشية 12)، والعربية بخط Sakkal Majalla بحجم 16 (الحاشية 12). واختيار الآلة: تطبع الكلمات اللاتينية بخط Times New Roman بنسبة حجم `latin` في الملف إلى حجم المتن مع التقريب إلى الأعلى (`imam`: المتن 18 ← 12، الحاشية 14 ← 10)؛ لأن الحروف اللاتينية في Traditional Arabic عريضة وتبدو عند الحجم نفسه أكبر كثيرًا من حروفه العربية.
- إذا طلب الأستاذ 0123 ← `@angka: latin`. أرقام الآيات في الحواشي وحدها ← `@angka_ayat: latin`.

## المستودع

| الموضع | المحتوى |
|---|---|
| `mesin/bahts.py` | المدخل الوحيد للأوامر |
| `mesin/olah.py`، `naskah.py`، `cek_*.py` وما يعينها | `cek`؛ تقسيم الملفات: `AGENTS.md` «Letak kode `cek`» |
| `mesin/quran_hafs_v22.json`، `nama_surah.json` | نص المصحف وأسماء السور |
| `mesin/shamela.py` | تنزيل الكتب، فهرس الكتب، `cari`، `teks`، `bab`، `halaman` |
| `mesin/turath.py` | الاتصال بموقع turath.io: `temukan`، `scan` |
| `mesin/jaringan.py` | الاتصال بالخدمات الخارجية، التحويل الآمن، الحصص، والتنزيل الكامل |
| `mesin/waqfeya.py` | كتب الوقفية: الفهرس، `ambil w…`، النص المستخرج آليا (OCR)، مقتطفات المصورة (PDF/PNG) |
| `mesin/hadits.py`، `dirasat.py` | دلالة التخريج، الدراسات السابقة |
| `mesin/layanan.py` | `tafsir` و`takhrij` و`rawi` و`akar` دون إنترنت (جداول خدمات الشاملة في `kitab/_meta`) |
| `mesin/diagram.py` | تحويل مخططات Mermaid إلى PNG (`diagram`) |
| `mesin/rumus.py` | تحويل معادلات LaTeX (`#E` و`{E:…}`) إلى معادلات Word OMML أصلية دون TeX |
| `mesin/pratinjau.py` | تحويل صفحات PDF إلى صور شبكية 2×2 بصيغة PNG في TEMP (`pratinjau`) |
| `mesin/ekspor.py` | كتاب منزَّل كاملًا (من الشاملة أو الوقفية) في ملف ‎.txt واحد للقراءة (`ekspor`) |
| `mesin/tahap.py`، `rakit.py`، `produk.py` | حالة البحث؛ جانب Python من `rakit` (القفل، مجلدات `.rakit-*`، تثبيت النتائج)؛ أسماء ملفات النتائج وأسطر التقرير |
| `mesin/rakit.ps1`، `word.ps1`، `teks_pdf.py` | مُخرِج Word/PDF، هوية عملية Word التابعة له، ونص PDF |
| `mesin/format.json` | أنماط شكل الصفحة (`@format`) |
| `mesin/sampul_qism.docx`، `sampul.doc`، `sampul_jakarta.docx`، `kepala_kotak.docx` | قوالب الغلاف ورأس الصفحة |
| `mesin/naskah_baru.txt`، `riset_baru.txt` | الهيكل الذي يُنشئه `baru` |
| `contoh/` | `naskah.txt` و`riset.txt` نموذجيان، و`jebakan/` للاختبار |
| `.mcp.json`، `opencode.json` | قائمة الموصِّلات (`opencode.json` نسخة لـOpenCode) |
| `dok/` | `mutamad.md` (الكتب المعتمدة في كل مذهب)، `uji-riset.md`، `takhrij.md` |
| `.github/` | `uji_*.py`، `workflows/tes.yml` |
| `kitab/`، `bahts/`، `sampul_saya.txt`، `keluaran_saya.txt`، `kunci_openalex.txt` | بيانات المستخدم على حاسوبه، خارج git |

### تعديل الآلة

- القواعد: `dok/mengubah-mesin.md`.
- الاختبار: `python .github/uji_semua.py` (القائمة تُقرأ من `.github/workflows/tes.yml`؛ كتب الاختبار في سطر `ambil` منه).
- التغيير الذي يحسه المستخدم يُكتب في [`CHANGELOG.md`](CHANGELOG.md) قسم «Belum dirilis».
- هذا الملف و[`README.id.md`](README.id.md) ترجمتان لـ[`README.md`](README.md): تُعدَّل الثلاثة معًا (`.github/uji_readme.py` يطابق بينها).
- المشكلات: issue فيه ناتج `periksa` والأمر والرسالة.

### الترخيص

الشفرة: GNU AGPLv3 أو ما بعدها ([`LICENSE`](LICENSE))؛ والإصدارات حتى 94d62d3 (ومنها 7.0.0) تبقى MIT. البحث الناتج ملك كاتبه؛ والقوالب المنسوخة إلى البحث يجوز استعمالها بلا شرط (إذن إضافي في `NOTICE`). نص المصحف والخطوط والشعار ونصوص الكتب: [`NOTICE`](NOTICE).

</div>
