// Terms of Service — DRAFT pending legal review.
// Generated as review-ready starting copy (legal-advisor). For a payment platform,
// have this reviewed / regenerated via Termly or counsel before Stripe live activation.
// Governing-law and entity-address placeholders are marked [[...]] — fill before publishing.

function Section({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-3">
        {n}. {title}
      </h2>
      <div className="space-y-2">{children}</div>
    </section>
  );
}

export default function TermsOfService() {
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950">
      <div className="max-w-4xl mx-auto px-6 py-12 text-neutral-800 dark:text-neutral-200 text-sm leading-relaxed">
        <h1 className="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
          TERMS OF SERVICE
        </h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-8">
          Last updated July 27, 2026
        </p>

        <p>
          These Terms of Service (&ldquo;Terms&rdquo;) govern your access to and use of{' '}
          <strong>Content Jumpstart</strong> and related websites and applications (the
          &ldquo;Services&rdquo;), operated by <strong>Basement Squirrel Games</strong>{' '}
          (&ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo;). By creating an account or using
          the Services, you agree to these Terms. If you do not agree, do not use the Services.
        </p>

        <Section n="1" title="Eligibility & accounts">
          <p>
            You must be at least 18 years old and able to form a binding contract. You are
            responsible for your account credentials and for all activity under your account. Provide
            accurate information and keep it current. Notify us promptly of any unauthorized use.
          </p>
        </Section>

        <Section n="2" title="The Services">
          <p>
            Content Jumpstart uses artificial intelligence to generate social-media and marketing
            content and to run research tools from the inputs you provide. Features, limits, and
            pricing may change over time. We may modify, suspend, or discontinue any part of the
            Services at any time.
          </p>
        </Section>

        <Section n="3" title="Fees, credits & payment">
          <p>
            The Services are sold on a prepaid credit basis. Payments are processed by{' '}
            <strong>Stripe</strong>; by purchasing, you also agree to Stripe&rsquo;s terms. Credits
            are consumed when you run paid operations, and the credit cost of each operation is shown
            before you confirm it. Prices are stated exclusive of taxes unless noted; you are
            responsible for applicable taxes.
          </p>
        </Section>

        <Section n="4" title="Refunds">
          <p>
            Credits that have been spent, and any operation for which generation or research has
            begun, are non-refundable, except as set out in our{' '}
            <a href="/refund" className="text-blue-600 dark:text-blue-400 hover:underline">
              Refund Policy
            </a>
            , which is incorporated into these Terms.
          </p>
        </Section>

        <Section n="5" title="AI-generated content">
          <p>
            The Services produce AI-generated output. Such output may be inaccurate, incomplete,
            outdated, or not unique, and similar output may be generated for other users.{' '}
            <strong>
              You are solely responsible for reviewing, editing, fact-checking, and ensuring the
              legality and suitability of any output before you use or publish it.
            </strong>{' '}
            The Services do not provide legal, financial, medical, or other professional advice.
          </p>
        </Section>

        <Section n="6" title="Your content & license">
          <p>
            You retain ownership of the inputs you submit (&ldquo;Input&rdquo;). As between you and
            us, and to the extent permitted by law, you own the output generated for you
            (&ldquo;Output&rdquo;), subject to your compliance with these Terms and the rights of
            third parties. You grant us a limited license to process your Input and Output as needed
            to operate, secure, and improve the Services. You represent that your Input does not
            infringe any third party&rsquo;s rights or violate any law.
          </p>
        </Section>

        <Section n="7" title="Acceptable use">
          <p>You agree not to use the Services to:</p>
          <ul className="list-disc ml-6 space-y-1 mt-1">
            <li>violate any law or the rights of others, including IP, privacy, or publicity rights;</li>
            <li>generate or distribute unlawful, deceptive, defamatory, harassing, or harmful content;</li>
            <li>infringe or misappropriate intellectual property or confidential information;</li>
            <li>attempt to reverse engineer, disrupt, overload, or gain unauthorized access to the Services;</li>
            <li>resell or provide the Services to third parties except as expressly permitted; or</li>
            <li>circumvent usage limits, security, or billing controls.</li>
          </ul>
        </Section>

        <Section n="8" title="Third-party services & sub-processors">
          <p>
            The Services rely on third parties including <strong>Stripe</strong> (payments) and{' '}
            <strong>Anthropic</strong> (AI processing). Your use may be subject to their terms, and
            we are not responsible for third-party services. How these parties process personal
            information is described in our{' '}
            <a href="/privacy" className="text-blue-600 dark:text-blue-400 hover:underline">
              Privacy Policy
            </a>
            .
          </p>
        </Section>

        <Section n="9" title="Privacy">
          <p>
            Our{' '}
            <a href="/privacy" className="text-blue-600 dark:text-blue-400 hover:underline">
              Privacy Policy
            </a>{' '}
            explains how we process personal information and describes your GDPR/CCPA rights. By using
            the Services, you acknowledge that policy.
          </p>
        </Section>

        <Section n="10" title="Intellectual property in the Services">
          <p>
            The Services, including our software, design, and trademarks, are owned by us or our
            licensors and are protected by law. Except for the rights expressly granted here, we
            reserve all rights.
          </p>
        </Section>

        <Section n="11" title="Disclaimers">
          <p className="uppercase">
            The Services and all Output are provided &ldquo;as is&rdquo; and &ldquo;as
            available,&rdquo; without warranties of any kind, whether express, implied, or statutory,
            including any implied warranties of merchantability, fitness for a particular purpose,
            title, and non-infringement. We do not warrant that the Services will be uninterrupted,
            error-free, or that Output will be accurate or fit for your purposes.
          </p>
        </Section>

        <Section n="12" title="Limitation of liability">
          <p className="uppercase">
            To the maximum extent permitted by law, we will not be liable for any indirect,
            incidental, special, consequential, or punitive damages, or any loss of profits, revenue,
            data, or goodwill. Our total liability arising out of or relating to the Services will not
            exceed the greater of the amounts you paid us in the three (3) months before the event
            giving rise to the claim, or one hundred U.S. dollars ($100).
          </p>
        </Section>

        <Section n="13" title="Indemnification">
          <p>
            You will indemnify and hold harmless Basement Squirrel Games and its personnel from any
            claims, damages, and expenses (including reasonable legal fees) arising from your Input or
            Output, your use of the Services, or your violation of these Terms or applicable law.
          </p>
        </Section>

        <Section n="14" title="Term & termination">
          <p>
            You may stop using the Services at any time. We may suspend or terminate your access if
            you violate these Terms, or to protect the Services or other users. Sections that by their
            nature should survive termination (including fees owed, disclaimers, limitations of
            liability, and indemnification) will survive.
          </p>
        </Section>

        <Section n="15" title="Governing law & disputes">
          <p>
            These Terms are governed by the laws of [[Governing law: State, USA]], without regard to
            conflict-of-laws rules. The exclusive venue for disputes will be the state or federal
            courts located in [[County/State]], and you consent to their jurisdiction, except where
            prohibited by law.
          </p>
        </Section>

        <Section n="16" title="Changes to these Terms">
          <p>
            We may update these Terms from time to time. Material changes will be indicated by
            updating the &ldquo;Last updated&rdquo; date and, where appropriate, by additional notice.
            Your continued use of the Services after changes take effect constitutes acceptance.
          </p>
        </Section>

        <Section n="17" title="Contact">
          <p>
            Basement Squirrel Games
            <br />
            [[Business mailing address]]
            <br />
            <a
              href="mailto:support@content-jumpstart.com"
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              support@content-jumpstart.com
            </a>
          </p>
        </Section>

        <div className="mt-10 pt-6 border-t border-neutral-200 dark:border-neutral-800 text-sm text-neutral-500 dark:text-neutral-400">
          <a href="/privacy" className="text-blue-600 dark:text-blue-400 hover:underline">
            Privacy Policy
          </a>
          {' · '}
          <a href="/refund" className="text-blue-600 dark:text-blue-400 hover:underline">
            Refund Policy
          </a>
        </div>
      </div>
    </div>
  );
}
