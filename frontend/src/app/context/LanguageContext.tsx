import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

type Lang = 'en' | 'hi';

const translations: Record<string, Record<Lang, string>> = {
  // TopNav
  'nav.wordmark': { en: 'Jan Saathi', hi: 'जन साथी' },
  'nav.subtext': { en: 'Government schemes, spoken simply', hi: 'सरकारी योजनाएं, आसान भाषा में' },
  'nav.login': { en: 'Log in with Google', hi: 'Google से लॉगिन करें' },
  'nav.profile': { en: 'My Profile', hi: 'मेरा प्रोफाइल' },
  'nav.logout': { en: 'Log out', hi: 'लॉग आउट' },
  'nav.admin': { en: 'Admin', hi: 'एडमिन' },
  // Footer
  'footer.tagline': { en: 'The citizen does not need to know a scheme exists. Jan Saathi finds it for them.', hi: 'नागरिक को योजना का नाम जानने की जरूरत नहीं। जन साथी खुद ढूंढता है।' },
  'footer.credit': { en: 'Built at Build4Bharat Hackathon 9.0', hi: 'Build4Bharat Hackathon 9.0 में बनाया गया' },
  // Landing
  'hero.headline': { en: 'Your government schemes. Found in 8 seconds.', hi: 'आपकी सरकारी योजनाएं। 8 सेकंड में मिलती हैं।' },
  'hero.subtext': { en: 'Speak in Hindi or English. Jan Saathi matches you to every scheme you qualify for — and tells you exactly how much you can claim.', hi: 'हिंदी या अंग्रेज़ी में बोलें। जन साथी आपके लिए सभी योजनाएं ढूंढता है — और बताता है कि आप कितना पा सकते हैं।' },
  'voice.tap': { en: 'Tap to speak', hi: 'बोलने के लिए दबाएं' },
  'voice.listening': { en: 'Listening...', hi: 'सुन रहा हूं...' },
  'voice.processing': { en: 'Thinking...', hi: 'सोच रहा हूं...' },
  'input.placeholder': { en: 'Or type here — your state, occupation, income...', hi: 'या यहाँ टाइप करें — राज्य, काम, आमदनी...' },
  'input.submit': { en: 'Find my schemes', hi: 'मेरी योजनाएं ढूंढें' },
  'example.1': { en: 'I am a farmer in UP, earning ₹80,000/year', hi: 'मैं UP का किसान हूं, ₹80,000 सालाना कमाता हूं' },
  'example.2': { en: 'Pregnant woman, BPL card, Rajasthan', hi: 'गर्भवती महिला, BPL कार्ड, राजस्थान' },
  'example.3': { en: 'Daily wage worker, 55 years old, no pension', hi: 'दिहाड़ी मज़दूर, 55 साल, कोई पेंशन नहीं' },
  'stat.1': { en: '57% of eligible citizens never claim their benefits', hi: '57% पात्र नागरिक अपना हक नहीं ले पाते' },
  'stat.2': { en: '600M Indians speak Hindi as first language', hi: '60 करोड़ भारतीय हिंदी में बात करते हैं' },
  'stat.3': { en: '500+ central government schemes matched', hi: '500+ केंद्र सरकार की योजनाएं खोजी जाती हैं' },
  'how.heading': { en: 'Three steps. No forms. No English required.', hi: 'तीन कदम। कोई फॉर्म नहीं। अंग्रेज़ी की ज़रूरत नहीं।' },
  'how.1.title': { en: 'Speak naturally', hi: 'बस बोलिए' },
  'how.1.body': { en: 'Tell us your state, occupation, age, and income in your own words', hi: 'अपनी भाषा में राज्य, काम, उम्र और आमदनी बताएं' },
  'how.2.title': { en: 'We find your schemes', hi: 'हम योजनाएं ढूंढते हैं' },
  'how.2.body': { en: 'AI matches your profile against 500+ schemes in under 8 seconds', hi: 'AI 8 सेकंड में 500+ योजनाओं में से आपके लिए सही योजना चुनता है' },
  'how.3.title': { en: 'Get guided step by step', hi: 'हर कदम पर मार्गदर्शन' },
  'how.3.body': { en: 'Every document, every form, every office — spoken to you', hi: 'हर दस्तावेज़, हर फॉर्म, हर दफ्तर — आवाज़ में बताया जाता है' },
  // Chat
  'chat.first': { en: "Namaste! I'm Jan Saathi. Tell me about yourself — your state, what work you do, your age, and roughly how much you earn in a year. You can speak or type.", hi: "नमस्ते! मैं जन साथी हूं। मुझे अपने बारे में बताइए — आप कहाँ रहते हैं, क्या काम करते हैं, उम्र क्या है, और साल में कितना कमाते हैं। बोल सकते हैं या टाइप कर सकते हैं।" },
  'chat.placeholder': { en: 'Type your message...', hi: 'यहाँ लिखें...' },
  'chat.send': { en: 'Send', hi: 'भेजें' },
  'chat.hold': { en: 'Hold to speak', hi: 'बोलने के लिए दबाएं' },
  'profile.header': { en: 'Your profile', hi: 'आपका प्रोफाइल' },
  'profile.state': { en: 'State', hi: 'राज्य' },
  'profile.occupation': { en: 'Occupation', hi: 'पेशा' },
  'profile.age': { en: 'Age', hi: 'उम्र' },
  'profile.income': { en: 'Annual income', hi: 'सालाना आमदनी' },
  'profile.category': { en: 'Category (SC/ST/OBC/General)', hi: 'वर्ग' },
  'profile.bpl': { en: 'BPL card', hi: 'BPL कार्ड' },
  'profile.gender': { en: 'Gender', hi: 'लिंग' },
  'gap.claim': { en: 'You can claim up to ₹{gap_value} per year', hi: 'आपको हर साल ₹{gap_value} मिल सकते हैं' },
  'gap.across': { en: 'Across {scheme_count} schemes you qualify for', hi: '{scheme_count} योजनाओं में आप पात्र हैं' },
  'gap.cta': { en: 'See my schemes →', hi: 'मेरी योजनाएं देखें →' },
  'gap.your_benefits': { en: 'Your Potential Benefits', hi: 'आपके संभावित लाभ' },
  'gap.per_year': { en: '/year', hi: '/वर्ष' },
  'chat.speak': { en: 'Listen to response', hi: 'उत्तर सुनें' },
  'save.prompt': { en: 'Save your profile to skip these questions next time', hi: 'अगली बार सवाल छोड़ने के लिए प्रोफाइल सेव करें' },
  'save.google': { en: 'Save with Google', hi: 'Google से सेव करें' },
  'save.notnow': { en: 'Not now', hi: 'अभी नहीं' },
  'chat.stt_error': { en: "I couldn't catch that — could you type it instead?", hi: "सुन नहीं पाया — क्या आप टाइप करके बता सकते हैं?" },
  'chat.network_error': { en: 'Something went wrong on our end. Please try again.', hi: 'कुछ गड़बड़ हो गई। कृपया दोबारा कोशिश करें।' },
  // Schemes
  'schemes.gap_banner': { en: 'You qualify for ₹{gap_value} per year across {count} schemes', hi: 'आप {count} योजनाओं में ₹{gap_value} प्रति वर्ष के पात्र हैं' },
  'schemes.gap_sub': { en: 'Based on your profile: {state} · {occupation} · Age {age} · ₹{income}/yr', hi: 'आपके प्रोफाइल के अनुसार: {state} · {occupation} · उम्र {age} · ₹{income}/वर्ष' },
  'filter.all': { en: 'All', hi: 'सभी' },
  'filter.agriculture': { en: 'Agriculture', hi: 'कृषि' },
  'filter.health': { en: 'Health', hi: 'स्वास्थ्य' },
  'filter.education': { en: 'Education', hi: 'शिक्षा' },
  'filter.employment': { en: 'Employment', hi: 'रोज़गार' },
  'filter.social': { en: 'Social welfare', hi: 'सामाजिक कल्याण' },
  'sort.highest': { en: 'Highest benefit first', hi: 'सबसे ज़्यादा लाभ पहले' },
  'sort.easiest': { en: 'Easiest to apply', hi: 'आसानी से मिलने वाला पहले' },
  'sort.best': { en: 'Best match', hi: 'सबसे सटीक मिलान' },
  'scheme.how_apply': { en: 'How to apply', hi: 'कैसे करें आवेदन' },
  'scheme.ask': { en: 'Ask Jan Saathi', hi: 'जन साथी से पूछें' },
  'scheme.per_year': { en: '₹{value}/year', hi: '₹{value}/वर्ष' },
  'scheme.apply_online': { en: 'Apply online →', hi: 'ऑनलाइन आवेदन करें →' },
  'scheme.start': { en: 'Start application', hi: 'आवेदन शुरू करें' },
  'scheme.guide': { en: 'Guide me through this', hi: 'इसमें मार्गदर्शन करें' },
  'scheme.back': { en: '← Back to chat', hi: '← चैट पर वापस जाएं' },
  'scheme.empty': { en: "We didn't find any schemes matching your current profile. Try updating your details.", hi: "आपके प्रोफाइल के अनुसार कोई योजना नहीं मिली। अपनी जानकारी अपडेट करके देखें।" },
  'scheme.update': { en: 'Update my profile', hi: 'प्रोफाइल अपडेट करें' },
  // Scheme Detail
  'detail.overview': { en: 'Overview', hi: 'अवलोकन' },
  'detail.eligibility': { en: 'Eligibility', hi: 'पात्रता' },
  'detail.documents': { en: 'Documents', hi: 'दस्तावेज़' },
  'detail.howto': { en: 'How to Apply', hi: 'कैसे आवेदन करें' },
  'detail.what': { en: 'What is this scheme?', hi: 'यह योजना क्या है?' },
  'detail.benefit': { en: 'Annual benefit: ₹{value}', hi: 'सालाना लाभ: ₹{value}' },
  'detail.qualify': { en: 'Do you qualify?', hi: 'क्या आप पात्र हैं?' },
  'detail.need': { en: "What you'll need", hi: 'आपको क्या चाहिए' },
  'detail.note': { en: 'Carry originals + one photocopy of each', hi: 'हर दस्तावेज़ की असली और एक फोटोकॉपी साथ रखें' },
  'detail.steps': { en: 'Step-by-step guide', hi: 'कदम-दर-कदम मार्गदर्शन' },
  'detail.office': { en: 'Where to go: {office_type}', hi: 'कहाँ जाएं: {office_type}' },
  'detail.official': { en: 'Official website →', hi: 'आधिकारिक वेबसाइट →' },
  'detail.listen': { en: '▶ Listen to full guide', hi: '▶ पूरी जानकारी सुनें' },
  'detail.pause': { en: '⏸ Pause', hi: '⏸ रोकें' },
  'detail.submit': { en: 'Submit application', hi: 'आवेदन जमा करें' },
  'detail.submitting': { en: 'Submitting...', hi: 'जमा हो रहा है...' },
  'detail.success': { en: 'Application submitted! Your reference number is {ref_number}', hi: 'आवेदन जमा हो गया! आपका संदर्भ नंबर है {ref_number}' },
  'detail.expected': { en: 'Expected processing time: 15 working days', hi: 'अनुमानित समय: 15 कार्य दिवस' },
  'detail.track_cta': { en: 'Track my application →', hi: 'आवेदन ट्रैक करें →' },
  // Tracker
  'track.header': { en: 'Track your application', hi: 'आवेदन की स्थिति जांचें' },
  'track.sub': { en: 'Enter the reference number you received after submitting', hi: 'आवेदन के बाद मिला संदर्भ नंबर डालें' },
  'track.placeholder': { en: 'e.g. JAN-2024-00341', hi: 'जैसे JAN-2024-00341' },
  'track.btn': { en: 'Track', hi: 'ट्रैक करें' },
  'track.s1': { en: 'Application submitted', hi: 'आवेदन जमा हुआ' },
  'track.s2': { en: 'Under review', hi: 'समीक्षाधीन' },
  'track.s3': { en: 'Approved', hi: 'स्वीकृत' },
  'track.rejected': { en: 'Rejected', hi: 'अस्वीकृत' },
  'track.expected': { en: 'Expected by: {date}', hi: 'अपेक्षित: {date}' },
  'track.notfound': { en: 'No application found with this reference number. Please check and try again.', hi: 'इस नंबर से कोई आवेदन नहीं मिला। कृपया जाँचकर दोबारा कोशिश करें।' },
  // Profile
  'profile.saved': { en: 'Your saved profile', hi: 'आपका सेव किया गया प्रोफाइल' },
  'profile.save': { en: 'Save changes', hi: 'बदलाव सेव करें' },
  'profile.clear': { en: 'Clear profile', hi: 'प्रोफाइल हटाएं' },
  'profile.schemes_header': { en: "Schemes you've looked at", hi: 'आपकी देखी गई योजनाएं' },
  'profile.no_schemes': { en: 'No saved schemes yet', hi: 'अभी कोई योजना सेव नहीं की' },
  'profile.sessions_header': { en: 'Your recent searches', hi: 'आपकी हाल की खोजें' },
  'profile.no_sessions': { en: 'No past searches', hi: 'कोई पुरानी खोज नहीं' },
  // 404
  '404.heading': { en: 'Page not found', hi: 'पृष्ठ नहीं मिला' },
  '404.body': { en: "The page you're looking for doesn't exist.", hi: 'आप जो पृष्ठ ढूंढ रहे हैं वह मौजूद नहीं है।' },
  '404.cta': { en: 'Go to home page', hi: 'होम पेज पर जाएं' },
  // Auth
  'auth.signing': { en: 'Signing you in...', hi: 'लॉगिन हो रहा है...' },
  // Loading
  'loading': { en: 'Loading...', hi: 'लोड हो रहा है...' },
  // Admin
  'admin.title': { en: 'Jan Saathi Admin', hi: 'जन साथी एडमिन' },
  'admin.dashboard': { en: 'Dashboard', hi: 'डैशबोर्ड' },
  'admin.pipeline': { en: 'Data pipeline', hi: 'डेटा पाइपलाइन' },
  'admin.schemes': { en: 'Schemes', hi: 'योजनाएं' },
  'admin.sessions': { en: 'Sessions', hi: 'सत्र' },
  'admin.users': { en: 'Users', hi: 'उपयोगकर्ता' },
  'admin.view_site': { en: 'View live site', hi: 'लाइव साइट देखें' },
  'admin.sessions_today': { en: 'Sessions today', hi: 'आज के सत्र' },
  'admin.total_gap': { en: 'Total gap surfaced', hi: 'कुल लाभ खोजा' },
  'admin.schemes_db': { en: 'Schemes in DB', hi: 'DB में योजनाएं' },
  'admin.pending': { en: 'Pending review', hi: 'समीक्षा बाकी' },
  'admin.top_schemes': { en: 'Top 10 most matched schemes today', hi: 'आज सबसे अधिक मिलान हुई 10 योजनाएं' },
  'admin.recent': { en: 'Recent sessions (last 50)', hi: 'हाल के सत्र (पिछले 50)' },
  'admin.gap_chart': { en: 'Gap unlocked per day (₹)', hi: 'प्रतिदिन खोला गया लाभ (₹)' },
  'admin.run_pipeline': { en: 'Run pipeline now', hi: 'पाइपलाइन चलाएं' },
  'admin.review_queue': { en: 'Schemes pending manual review ({count})', hi: 'मैन्युअल समीक्षा के लिए लंबित योजनाएं ({count})' },
  'admin.approve': { en: 'Approve and ingest', hi: 'स्वीकृत करें और जोड़ें' },
  'admin.reject': { en: 'Reject', hi: 'अस्वीकार करें' },
  'admin.search_schemes': { en: 'Search schemes...', hi: 'योजना खोजें...' },
  'admin.export_csv': { en: 'Export CSV', hi: 'CSV निर्यात करें' },
  'admin.admin_accounts': { en: 'Admin accounts', hi: 'एडमिन खाते' },
  'admin.citizen_accounts': { en: 'Registered citizen accounts', hi: 'पंजीकृत नागरिक खाते' },
  'admin.query_patterns': { en: 'Most common query patterns', hi: 'सबसे सामान्य प्रश्न पैटर्न' },
  'admin.export_rag': { en: 'Export unanswered queries for RAG training', hi: 'RAG प्रशिक्षण के लिए निर्यात करें' },
  'admin.ai_check': { en: 'AI quality check', hi: 'AI गुणवत्ता जांच' },
  'admin.run_verify': { en: 'Run Groq verification', hi: 'Groq सत्यापन चलाएं' },
  'admin.apply_suggestions': { en: 'Apply suggested corrections', hi: 'सुझाए गए सुधार लागू करें' },
  'admin.re_embed': { en: 'Re-embed this scheme', hi: 'इस योजना को फिर से embed करें' },
};

interface LangContextType {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
}

const LangContext = createContext<LangContextType>({
  lang: 'en',
  setLang: () => {},
  t: (k) => k,
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    const stored = localStorage.getItem('js_lang');
    return (stored === 'hi' ? 'hi' : 'en') as Lang;
  });

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    localStorage.setItem('js_lang', l);
  }, []);

  const t = useCallback((key: string, vars?: Record<string, string | number>) => {
    let str = translations[key]?.[lang] || key;
    if (vars) {
      Object.entries(vars).forEach(([k, v]) => {
        str = str.replace(`{${k}}`, String(v));
      });
    }
    return str;
  }, [lang]);

  return <LangContext.Provider value={{ lang, setLang, t }}>{children}</LangContext.Provider>;
}

export const useLang = () => useContext(LangContext);