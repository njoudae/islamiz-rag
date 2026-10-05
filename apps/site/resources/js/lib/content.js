// Static content from the approved design (fatwa-standalone.html).
//
// STATUS and the book list describe the real system. KB and DEMO_RESP are the
// design's prepared answers: the home preview and the ask page's opening example use them,
// and they are a clearly labelled fallback when the AI service is offline. CONFUSION_NOTES is
// the advice shown next to each kind of misclassification. Admin figures all come from the server.
import ENCYCLOPEDIA from '../data/encyclopedia.json';

/* ================= Static content ================= */
export const STATUS = {
  ANSWERABLE: {
    ar: 'إجابة مباشرة', icon: 'circle-check',
    pub: 'وجد الحكم ودليله في الموسوعة، فيعرضه لك مع المصدر.',
    gets: 'الحكم، والدليل، ورابط الباب في الموسوعة',
    admin: 'راجع عيّنة أسبوعية للتأكد من صحة الاستشهاد.',
    actLabel: 'راجع عيّنة', actRoute: 'admin-review', actFilter: 'ANSWERABLE'
  },
  NEEDS_CLARIFICATION: {
    ar: 'يحتاج توضيحاً', icon: 'circle-question-mark',
    pub: 'سؤالك يحتمل أكثر من مسألة، فيسألك سؤالاً واحداً قبل أن يجيب.',
    gets: 'سؤال استيضاح مع خيارات سريعة',
    admin: 'حسّن أسئلة الاستيضاح وخياراتها حتى يكمل السائل.',
    actLabel: 'افتح الطابور', actRoute: 'admin-review', actFilter: 'NEEDS_CLARIFICATION'
  },
  INSUFFICIENT_EVIDENCE: {
    ar: 'أدلة غير كافية', icon: 'book-x',
    pub: 'لم يجد في الموسوعة ما يكفي للإجابة بثقة، فلا يخمّن.',
    gets: 'أقرب الأبواب، واقتراح جهة تسألها',
    admin: 'فجوة معرفية: أضف مصدراً أو وسّع الفهرسة.',
    actLabel: 'فجوات المعرفة', actRoute: 'admin-gaps'
  },
  COMPLEX_CASE: {
    ar: 'حالة معقّدة', icon: 'scale',
    pub: 'المسألة تتوقف على تفاصيل شخصية كالميراث والطلاق، فيحيلك إلى مفتٍ.',
    gets: 'سبب الإحالة، والجهة المناسبة',
    admin: 'تحقّق أن قواعد الإحالة لا تحجب أسئلة يمكن إجابتها.',
    actLabel: 'افتح الطابور', actRoute: 'admin-review', actFilter: 'COMPLEX_CASE'
  },
  CONFLICTING_EVIDENCE: {
    ar: 'أقوال متعارضة', icon: 'git-compare',
    pub: 'للعلماء أكثر من قول معتبر، فيعرض الأقوال وأدلتها دون ترجيح.',
    gets: 'الأقوال، ومن قال بها، وأدلة كل قول',
    admin: 'اعرض الأقوال على مراجع شرعي للتأكد من نسبتها.',
    actLabel: 'افتح الطابور', actRoute: 'admin-review', actFilter: 'CONFLICTING_EVIDENCE'
  },
  OUT_OF_SCOPE: {
    ar: 'خارج النطاق', icon: 'ban',
    pub: 'السؤال ليس مسألة فقهية، فيوضّح ذلك ويدلّك على المصدر المناسب.',
    gets: 'توضيح النطاق، ورابط بديل إن وُجد',
    admin: 'إن تكرر موضوع، فكّر في ربطه بموسوعة أخرى.',
    actLabel: 'فجوات المعرفة', actRoute: 'admin-gaps'
  },
  FAILED: {
    ar: 'تعذّرت المعالجة', icon: 'triangle-alert',
    pub: 'حدث خطأ تقني في التفريغ أو المعالجة، فيطلب منك إعادة المحاولة.',
    gets: 'سبب الخطأ، وزر لإعادة المحاولة',
    admin: 'خطأ تقني: تتبّع السبب في جودة النموذج.',
    actLabel: 'أسباب الفشل', actRoute: 'admin-quality'
  }
};
export const ST_ORDER = ['ANSWERABLE','NEEDS_CLARIFICATION','INSUFFICIENT_EVIDENCE','COMPLEX_CASE','CONFLICTING_EVIDENCE','OUT_OF_SCOPE','FAILED'];
/* Order used where colours touch (stacked bar): keeps similar hues apart. */
export const ST_BAR = ['ANSWERABLE','CONFLICTING_EVIDENCE','NEEDS_CLARIFICATION','COMPLEX_CASE','INSUFFICIENT_EVIDENCE','OUT_OF_SCOPE','FAILED'];
export const ST_CLASSIFY = ST_ORDER.filter(s => s !== 'FAILED');

export const DORAR = 'https://dorar.net/feqhia';

/* The 52 books of الموسوعة الفقهية, in the encyclopedia's order; grouped for browsing. */
export const BOOK_GROUPS = [
  { id:'ibadat', name:'العبادات', note:'الطهارة والصلاة والزكاة والصوم والحج', books:['كتاب الطهارة','كتاب الصلاة','كتاب الزكاة','كتاب الصوم','كتاب الحج'] },
  { id:'food', name:'اللباس والأطعمة والذبائح', note:'ما يحل ويحرم من المطعوم والملبوس', books:['كتاب اللباس والزينة','كتاب الأشربة','كتاب الأطعمة','كتاب التذكية','كتاب الصيد','كتاب العقيقة'] },
  { id:'family', name:'فقه الأسرة', note:'من النكاح إلى النفقات والحقوق', books:['كتاب النكاح','كتاب الطلاق','كتاب الخلع','كتاب الإيلاء','كتاب الظهار','كتاب اللعان','كتاب العدة','كتاب الرضاع','كتاب الحضانة','كتاب النفقات','كتاب الحقوق المتعلقة بالأسرة'] },
  { id:'oaths', name:'الأيمان والنذور والتبرعات', note:'الأيمان والنذور والأوقاف والوصايا والهبات', books:['كتاب الأيمان','كتاب النذور','كتاب الأوقاف','كتاب الوصايا','كتاب الهبات'] },
  { id:'muamalat', name:'المعاملات المالية', note:'البيع والربا والشركات والعقود', books:['كتاب البيع','كتاب الربا','كتاب القرض','كتاب الإجارة','كتاب الجعالة','كتاب الشركة','كتاب الحوالة','كتاب الشفعة','كتاب الوكالة','كتاب المساقاة والمزارعة','كتاب الرهن','كتاب الكفالة والضمان','كتاب الوديعة','كتاب العارية','كتاب الصلح والإبراء','كتاب الحجر والتفليس','كتاب السباق','كتاب الغصب','كتاب اللقطة','كتاب إحياء الموات'] },
  { id:'qada', name:'الجنايات والقضاء', note:'الجنايات والحدود وطرق الإثبات', books:['كتاب الجنايات','كتاب الحدود والتعزيرات','كتاب القضاء وطرق إثبات الدعاوى'] },
  { id:'mawarith', name:'المواريث والجهاد', note:'قسمة التركات، وأحكام الجهاد', books:['كتاب المواريث','كتاب الجهاد'] }
];
// Each book's own page on Dorar, its number of entries and its chapters come from the
// encyclopedia's public table of contents (see data/encyclopedia.json for source and date).
export const BOOKS = [];
BOOK_GROUPS.forEach(g => g.books.forEach(b => {
  const source = ENCYCLOPEDIA.books[BOOKS.length];
  BOOKS.push({ no: BOOKS.length + 1, title: b, group: g.id, groupName: g.name, url: source.url, entries: source.entries, chapters: source.chapters });
}));
export const ENCYCLOPEDIA_READ_ON = ENCYCLOPEDIA.readOn;

/** The Dorar page of a book by its title, or the encyclopedia's home page when unknown. */
export const bookUrl = title => (BOOKS.find(b => b.title === title) || {}).url || DORAR;

/* ================= Demo knowledge (used when live answers are unavailable) ================= */
export const KB = {
  wudu_wind: {
    status:'ANSWERABLE', topic:'نواقض الوضوء', confidence:96,
    answer:'نعم، خروج الريح من نواقض الوضوء بإجماع العلماء، فمن خرجت منه ريح لزمه الوضوء قبل أن يصلي. أما من شكّ هل خرج منه شيء أم لا، فالأصل بقاء طهارته حتى يتيقّن.',
    evidence:[
      { text:'«لا يقبل الله صلاة أحدكم إذا أحدث حتى يتوضأ»', ref:'متفق عليه، من حديث أبي هريرة رضي الله عنه', quoted:true },
      { text:'«فلا ينصرف حتى يسمع صوتاً أو يجد ريحاً»', ref:'متفق عليه، في الشاك في الحدث', quoted:true }
    ],
    sources:[{ book:'كتاب الطهارة', chapter:'نواقض الوضوء' }],
    keys:['ريح','وضوء','ينقض','نواقض','حدث','خروج'], need:['ريح','حدث'], min:2
  },
  fast_forget: {
    status:'ANSWERABLE', topic:'الأكل والشرب ناسياً في الصيام', confidence:93,
    answer:'من أكل أو شرب ناسياً وهو صائم فصومه صحيح، ولا قضاء عليه عند جمهور العلماء، ويُمسك بقية يومه متى تذكّر. وذهب المالكية إلى وجوب القضاء في صوم الفرض.',
    evidence:[
      { text:'«من نسي وهو صائم فأكل أو شرب فليُتمّ صومه، فإنما أطعمه الله وسقاه»', ref:'متفق عليه', quoted:true }
    ],
    sources:[{ book:'كتاب الصوم' }],
    keys:['ناسي','نسيت','نسي','صائم','صيام','صوم','اكلت','شربت','اكل','رمضان'], need:['نسي','ناسي'], min:2
  },
  jam_travel: {
    status:'ANSWERABLE', topic:'الجمع بين الصلاتين للمسافر', confidence:88,
    answer:'يجوز للمسافر الجمع بين الظهر والعصر، وبين المغرب والعشاء، جمع تقديم أو تأخير، وهذا قول جمهور العلماء. ولا يجوز عند الحنفية إلا في عرفة ومزدلفة.',
    evidence:[
      { text:'ثبت أن النبي ﷺ في غزوة تبوك كان يصلي الظهر والعصر جميعاً، والمغرب والعشاء جميعاً.', ref:'رواه مسلم من حديث معاذ بن جبل رضي الله عنه', quoted:false }
    ],
    sources:[{ book:'كتاب الصلاة' }],
    keys:['جمع','الظهر','العصر','المغرب','العشاء','مسافر','سفر'], need:['جمع'], min:2
  },
  travel_prayer: {
    status:'ANSWERABLE', topic:'قصر الصلاة في السفر', confidence:91,
    answer:'يُشرع للمسافر قصر الصلاة الرباعية (الظهر والعصر والعشاء) إلى ركعتين. أما الفجر والمغرب فلا تُقصران بإجماع العلماء. واختلفوا في المسافة التي يُقصر فيها وفي مدة الإقامة التي ينقطع بها حكم السفر.',
    evidence:[
      { text:'﴿وَإِذَا ضَرَبْتُمْ فِي الْأَرْضِ فَلَيْسَ عَلَيْكُمْ جُنَاحٌ أَن تَقْصُرُوا مِنَ الصَّلَاةِ﴾', ref:'سورة النساء: 101', quoted:true }
    ],
    sources:[{ book:'كتاب الصلاة' }],
    keys:['قصر','يقصر','مسافر','سفر','صلاه','المغرب','الفجر','ركعتين'], need:['قصر','يقصر','مسافر','سفر'], min:2
  },
  jewelry: {
    status:'CONFLICTING_EVIDENCE', topic:'زكاة الحلي المعدّ للاستعمال', confidence:78,
    answer:'اختلف العلماء في زكاة الحلي المباح الذي تلبسه المرأة على قولين مشهورين، ولكلٍّ منهما أدلته المعتبرة. يعرض دليل القولين دون ترجيح، ولمعرفة ما يلزمك تحديداً اسأل مفتياً.',
    positions:[
      { view:'لا زكاة في الحلي المعدّ للاستعمال المباح.', held_by:'جمهور العلماء: المالكية والشافعية والحنابلة', evidence:'آثار عن جماعة من الصحابة، منهم عائشة وابن عمر وجابر رضي الله عنهم، أنهم لم يكونوا يزكّون الحلي.' },
      { view:'تجب الزكاة في الحلي إذا بلغ النصاب وحال عليه الحول.', held_by:'الحنفية، واختاره بعض المعاصرين', evidence:'حديث المرأة التي في يد ابنتها مسكتان من ذهب، فقال لها النبي ﷺ: «أتعطين زكاة هذا؟» رواه أبو داود والنسائي.' }
    ],
    evidence:[], sources:[{ book:'كتاب الزكاة' }],
    keys:['حلي','ذهب','مجوهرات','زكاه','البس','ذهبي','حليها'], need:['حلي','ذهب','مجوهرات'], min:2
  }
};
export const DEMO_RESP = {
  clarify_jam: {
    status:'NEEDS_CLARIFICATION', topic:'الجمع', confidence:95,
    answer:'كلمة «الجمع» تحتمل أكثر من مسألة في الفقه، والحكم يختلف باختلافها.',
    clarifying_question:'ماذا تقصد بالجمع؟',
    clarify_options:['الجمع بين الظهر والعصر للمسافر','الجمع بين الصلاتين بسبب المطر','الجمع بين نية القضاء ونية النفل في صيام واحد'],
    evidence:[], sources:[]
  },
  clarify_generic: {
    status:'NEEDS_CLARIFICATION', topic:'سؤال مختصر', confidence:90,
    answer:'سؤالك مختصر ويحتمل أكثر من مسألة، والحكم يتغير بحسب التفاصيل.',
    clarifying_question:'اذكر المسألة بتفصيل أكثر: ما الفعل، ومتى وقع، وما حالك وقتها؟',
    clarify_options:[], evidence:[], sources:[]
  },
  complex_inherit: {
    status:'COMPLEX_CASE', topic:'قسمة التركة', confidence:94,
    answer:'قسمة التركة تتوقف على حصر الورثة بدقة، وسداد الديون، وتنفيذ الوصية قبل القسمة، وأي خطأ في الحصر يغيّر الأنصبة كلها. لذلك يحيل دليل هذه المسألة إلى مختص بدل أن يحسبها لك.',
    refer_reasons:['تتعلق بحقوق أطراف متعددة، والخطأ فيها يقع على غيرك','تتطلب حصراً رسمياً للورثة وتوثيقاً للديون والوصايا','تُقسم التركة رسمياً بصك حصر ورثة من وزارة العدل (ناجز)'],
    evidence:[], sources:[{ book:'كتاب المواريث' }]
  },
  complex_generic: {
    status:'COMPLEX_CASE', topic:'مسألة شخصية', confidence:88,
    answer:'هذه المسألة تتوقف على ألفاظ وظروف شخصية دقيقة، ويترتب عليها حقوق وآثار، فلا يناسبها جواب عام.',
    refer_reasons:['الحكم يتغير بتغير اللفظ والنية والملابسات','قد يترتب عليها أثر في الأسرة أو الحقوق','الأنسب عرضها على مفتٍ أو على الرئاسة العامة للبحوث العلمية والإفتاء'],
    evidence:[], sources:[]
  },
  oos_general: {
    status:'OUT_OF_SCOPE', topic:'سؤال غير فقهي', confidence:98,
    answer:'هذا السؤال ليس مسألة فقهية. دليل مخصص للأسئلة الشرعية العملية المبنية على الموسوعة الفقهية في الدرر السنية.',
    evidence:[], sources:[]
  },
  oos_creed: {
    status:'OUT_OF_SCOPE', topic:'عقيدة أو تفسير أو حديث', confidence:92,
    answer:'سؤالك في العقيدة أو التفسير أو الحكم على الحديث، وهذه خارج الموسوعة الفقهية. تجد جوابها في موسوعات أخرى على موقع الدرر السنية: الموسوعة العقدية، وموسوعة التفسير، والموسوعة الحديثية.',
    evidence:[], sources:[], link:{ label:'افتح موقع الدرر السنية', href:'https://dorar.net' }
  },
  insuff_crypto: {
    status:'INSUFFICIENT_EVIDENCE', topic:'العملات الرقمية المستقرة', confidence:41,
    answer:'لم يجد دليل في الموسوعة الفقهية باباً يتناول هذه المعاملة المعاصرة بعينها. أقرب ما فيها أبواب الصرف والربا والبيع، لكنها لا تكفي للحكم بثقة، لذلك لا يقدّم دليل جواباً قد يكون خاطئاً.',
    suggest:'ارجع إلى قرارات المجامع الفقهية، أو اسأل مختصاً في المعاملات المالية المعاصرة.',
    evidence:[], sources:[{ book:'كتاب الربا', near:true },{ book:'كتاب البيع', near:true }]
  },
  insuff_generic: {
    status:'INSUFFICIENT_EVIDENCE', topic:'مسألة غير مغطاة', confidence:35,
    answer:'لم يجد دليل في الموسوعة ما يكفي للإجابة عن هذه المسألة بثقة، فلا يقدّم جواباً قد يكون خاطئاً.',
    suggest:'وضع العرض يغطي عدداً محدوداً من المسائل. أعد المحاولة لاحقاً، أو اسأل مفتياً.',
    evidence:[], sources:[]
  },
  failed_stt: {
    status:'FAILED', topic:'', confidence:0,
    answer:'', fail:'تعذّر تفريغ التسجيل الصوتي: مستوى الضجيج في الخلفية مرتفع، ولم يُتعرّف على كلمات كافية.',
    evidence:[], sources:[]
  }
};

/* ================= Admin: model quality ================= */
export const CONFUSION_NOTES = {
  'NEEDS_CLARIFICATION>ANSWERABLE': { p:'يجيب عن أسئلة غامضة بدل أن يستوضح أولاً.', fix:'أضف أمثلة استيضاح إلى تعليمات النموذج، وارفع عتبة الثقة للإجابة المباشرة إلى 75%.' },
  'CONFLICTING_EVIDENCE>ANSWERABLE': { p:'يرجّح قولاً واحداً في مسائل خلافية مشهورة.', fix:'زوّد الاسترجاع بقائمة المسائل الخلافية في الموسوعة، واطلب عرض الأقوال عند ورودها.' },
  'INSUFFICIENT_EVIDENCE>ANSWERABLE': { p:'يجيب دون أدلة كافية من الموسوعة، وهذا أخطر الأخطاء.', fix:'اشترط وجود مقطع مسترجع واحد على الأقل قبل أي إجابة مباشرة.' },
  'COMPLEX_CASE>ANSWERABLE': { p:'يفتي في حالات شخصية كان ينبغي إحالتها.', fix:'وسّع كلمات الإحالة: الحلف بالطلاق، والنذر المعلّق، وقسمة التركات.' },
  'OUT_OF_SCOPE>INSUFFICIENT_EVIDENCE': { p:'يعامل أسئلة العقيدة كأنها فقهية بلا أدلة.', fix:'أضف مصنّفاً أولياً لنطاق السؤال قبل البحث.' }
};
export const FB_REASONS = [
  { t:'إجابة غير دقيقة', s:.31 },
  { t:'لم يفهم سؤالي', s:.27 },
  { t:'المصدر غير مناسب', s:.18 },
  { t:'الإجابة طويلة', s:.14 },
  { t:'أسباب أخرى', s:.10 }
];
