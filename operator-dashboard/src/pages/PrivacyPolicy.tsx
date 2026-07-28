// Privacy Policy — first-party render of our Termly export (cleaned).
// To update: regenerate in Termly, re-run scripts/clean_termly, replace
// src/content/legal/privacy.html. Styling lives in LegalDocument.css.
import privacyHtml from '@/content/legal/privacy.html?raw';
import LegalDocument, { LegalLinks } from '@/components/legal/LegalDocument';

export default function PrivacyPolicy() {
  return <LegalDocument html={privacyHtml} footer={<LegalLinks />} />;
}
