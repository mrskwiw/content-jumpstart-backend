// Terms of Service — first-party render of our Termly export (cleaned).
// To update: regenerate in Termly, re-run scripts/clean_termly, replace
// src/content/legal/terms.html. Styling lives in LegalDocument.css.
import termsHtml from '@/content/legal/terms.html?raw';
import LegalDocument, { LegalLinks } from '@/components/legal/LegalDocument';

export default function TermsOfService() {
  return <LegalDocument html={termsHtml} footer={<LegalLinks />} />;
}
