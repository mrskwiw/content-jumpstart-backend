// Cookie Policy — first-party render of our Termly export (cleaned).
// To update: regenerate in Termly, re-run scripts/clean_termly, replace
// src/content/legal/cookies.html. Styling lives in LegalDocument.css.
import cookiesHtml from '@/content/legal/cookies.html?raw';
import LegalDocument, { LegalLinks } from '@/components/legal/LegalDocument';

export default function CookiePolicy() {
  return <LegalDocument html={cookiesHtml} footer={<LegalLinks />} />;
}
