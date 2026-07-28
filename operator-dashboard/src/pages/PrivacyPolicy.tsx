export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950">
      <div className="max-w-4xl mx-auto px-6 py-12 text-neutral-800 dark:text-neutral-200">

        {/* Header */}
        <h1 className="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">PRIVACY POLICY</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-8">Last updated April 26, 2026</p>

        <div className="space-y-2 text-sm leading-relaxed mb-8">
          <p>
            This Privacy Notice for <strong>Basement Squirrel Games</strong> ("we," "us," or "our") describes how and
            why we might access, collect, store, use, and/or share ("process") your personal information when you use
            our services ("Services"), including when you:
          </p>
          <ul className="list-disc ml-6 space-y-1 mt-2">
            <li>
              Visit our website at{' '}
              <a href="https://content-jumpstart.com" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline break-all">
                https://content-jumpstart.com
              </a>{' '}
              or any website of ours that links to this Privacy Notice
            </li>
            <li>Use <strong>Content Jumpstart</strong> — automated research and marketing tools</li>
            <li>Engage with us in other related ways, including any marketing or events</li>
          </ul>
          <p className="mt-4">
            <strong>Questions or concerns?</strong> Reading this Privacy Notice will help you understand your privacy
            rights and choices. We are responsible for making decisions about how your personal information is
            processed. If you do not agree with our policies and practices, please do not use our Services. If you
            still have any questions or concerns, please contact us at{' '}
            <a href="mailto:mrskwiw@gmail.com" className="text-blue-600 dark:text-blue-400 hover:underline">mrskwiw@gmail.com</a>.
          </p>
        </div>

        {/* Summary */}
        <section className="mb-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">SUMMARY OF KEY POINTS</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p><strong>What personal information do we process?</strong> When you visit, use, or navigate our Services, we may process personal information depending on how you interact with us and the Services, the choices you make, and the products and features you use.</p>
            <p><strong>Do we process any sensitive personal information?</strong> We do not process sensitive personal information.</p>
            <p><strong>Do we collect any information from third parties?</strong> We do not collect any information from third parties.</p>
            <p><strong>How do we process your information?</strong> We process your information to provide, improve, and administer our Services, communicate with you, for security and fraud prevention, and to comply with law.</p>
            <p><strong>In what situations and with which parties do we share personal information?</strong> We may share information in specific situations and with specific third parties.</p>
            <p><strong>How do we keep your information safe?</strong> We have adequate organizational and technical processes and procedures in place to protect your personal information. However, no electronic transmission over the internet can be guaranteed to be 100% secure.</p>
            <p><strong>What are your rights?</strong> Depending on where you are located geographically, the applicable privacy law may mean you have certain rights regarding your personal information.</p>
            <p>
              <strong>How do you exercise your rights?</strong> The easiest way to exercise your rights is by visiting{' '}
              <a href="https://content-jumpstart.com/dashboard/settings" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline break-all">
                https://content-jumpstart.com/dashboard/settings
              </a>{' '}
              or by contacting us.
            </p>
          </div>
        </section>

        {/* TOC */}
        <section className="mb-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">TABLE OF CONTENTS</h2>
          <ol className="space-y-1 text-sm text-blue-600 dark:text-blue-400">
            {[
              ['#infocollect', '1. WHAT INFORMATION DO WE COLLECT?'],
              ['#infouse', '2. HOW DO WE PROCESS YOUR INFORMATION?'],
              ['#legalbases', '3. WHAT LEGAL BASES DO WE RELY ON TO PROCESS YOUR PERSONAL INFORMATION?'],
              ['#whoshare', '4. WHEN AND WITH WHOM DO WE SHARE YOUR PERSONAL INFORMATION?'],
              ['#cookies', '5. DO WE USE COOKIES AND OTHER TRACKING TECHNOLOGIES?'],
              ['#ai', '6. DO WE OFFER ARTIFICIAL INTELLIGENCE-BASED PRODUCTS?'],
              ['#inforetain', '7. HOW LONG DO WE KEEP YOUR INFORMATION?'],
              ['#infosafe', '8. HOW DO WE KEEP YOUR INFORMATION SAFE?'],
              ['#infominors', '9. DO WE COLLECT INFORMATION FROM MINORS?'],
              ['#privacyrights', '10. WHAT ARE YOUR PRIVACY RIGHTS?'],
              ['#DNT', '11. CONTROLS FOR DO-NOT-TRACK FEATURES'],
              ['#uslaws', '12. DO UNITED STATES RESIDENTS HAVE SPECIFIC PRIVACY RIGHTS?'],
              ['#policyupdates', '13. DO WE MAKE UPDATES TO THIS NOTICE?'],
              ['#contact', '14. HOW CAN YOU CONTACT US ABOUT THIS NOTICE?'],
              ['#request', '15. HOW CAN YOU REVIEW, UPDATE, OR DELETE THE DATA WE COLLECT FROM YOU?'],
            ].map(([href, label]) => (
              <li key={href}>
                <a href={href} className="hover:underline">{label}</a>
              </li>
            ))}
          </ol>
        </section>

        <hr className="border-neutral-200 dark:border-neutral-700 my-8" />

        {/* Section 1 */}
        <section id="infocollect" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">1. WHAT INFORMATION DO WE COLLECT?</h2>
          <h3 className="text-base font-semibold mb-2">Personal information you disclose to us</h3>
          <div className="space-y-3 text-sm leading-relaxed">
            <p><em><strong>In Short:</strong> We collect personal information that you provide to us.</em></p>
            <p>We collect personal information that you voluntarily provide to us when you register on the Services, express an interest in obtaining information about us or our products and Services, when you participate in activities on the Services, or otherwise when you contact us.</p>
            <p><strong>Personal Information Provided by You.</strong> The personal information we collect may include: names, usernames, passwords, and contact preferences.</p>
            <p><strong>Sensitive Information.</strong> We do not process sensitive information.</p>
            <p>
              <strong>Payment Data.</strong> We may collect data necessary to process your payment if you choose to make purchases, such as your payment instrument number and security code. All payment data is handled and stored by{' '}
              <strong>Stripe</strong>. You may find their privacy notice at{' '}
              <a href="https://stripe.com/privacy" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">https://stripe.com/privacy</a>.
            </p>
            <p>All personal information that you provide to us must be true, complete, and accurate, and you must notify us of any changes to such personal information.</p>
            <h3 className="text-base font-semibold mt-4 mb-2">Google API</h3>
            <p>
              Our use of information received from Google APIs will adhere to the{' '}
              <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">Google API Services User Data Policy</a>,
              including the{' '}
              <a href="https://developers.google.com/terms/api-services-user-data-policy#limited-use" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">Limited Use requirements</a>.
            </p>
          </div>
        </section>

        {/* Section 2 */}
        <section id="infouse" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">2. HOW DO WE PROCESS YOUR INFORMATION?</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p><em><strong>In Short:</strong> We process your information to provide, improve, and administer our Services, communicate with you, for security and fraud prevention, and to comply with law.</em></p>
            <p><strong>We process your personal information for a variety of reasons, including:</strong></p>
            <ul className="list-disc ml-6 space-y-1">
              <li><strong>To facilitate account creation and authentication and otherwise manage user accounts.</strong> We may process your information so you can create and log in to your account, as well as keep your account in working order.</li>
              <li><strong>To save or protect an individual's vital interest.</strong> We may process your information when necessary to save or protect an individual's vital interest, such as to prevent harm.</li>
            </ul>
          </div>
        </section>

        {/* Section 3 */}
        <section id="legalbases" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">3. WHAT LEGAL BASES DO WE RELY ON TO PROCESS YOUR INFORMATION?</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p><em><strong>In Short:</strong> We only process your personal information when we believe it is necessary and we have a valid legal reason to do so under applicable law.</em></p>
            <p><strong><u>If you are located in the EU or UK, this section applies to you.</u></strong></p>
            <p>The General Data Protection Regulation (GDPR) and UK GDPR require us to explain the valid legal bases we rely on in order to process your personal information. We may rely on the following legal bases:</p>
            <ul className="list-disc ml-6 space-y-2">
              <li><strong>Consent.</strong> We may process your information if you have given us permission to use your personal information for a specific purpose. You can withdraw your consent at any time.</li>
              <li><strong>Legal Obligations.</strong> We may process your information where we believe it is necessary for compliance with our legal obligations.</li>
              <li><strong>Vital Interests.</strong> We may process your information where we believe it is necessary to protect your vital interests or the vital interests of a third party.</li>
            </ul>
            <p><strong><u><em>If you are located in Canada, this section applies to you.</em></u></strong></p>
            <p>We may process your information if you have given us specific permission (express consent) to use your personal information for a specific purpose, or in situations where your permission can be inferred (implied consent). You can withdraw your consent at any time.</p>
            <p>In some exceptional cases, we may be legally permitted to process your information without your consent, including for investigations and fraud detection, business transactions, or where required by law.</p>
          </div>
        </section>

        {/* Section 4 */}
        <section id="whoshare" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">4. WHEN AND WITH WHOM DO WE SHARE YOUR PERSONAL INFORMATION?</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p><em><strong>In Short:</strong> We may share information in specific situations described in this section and/or with the following third parties.</em></p>
            <p>We may need to share your personal information in the following situations:</p>
            <ul className="list-disc ml-6">
              <li><strong>Business Transfers.</strong> We may share or transfer your information in connection with, or during negotiations of, any merger, sale of company assets, financing, or acquisition of all or a portion of our business to another company.</li>
            </ul>
          </div>
        </section>

        {/* Section 5 */}
        <section id="cookies" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">5. DO WE USE COOKIES AND OTHER TRACKING TECHNOLOGIES?</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p><em><strong>In Short:</strong> We may use cookies and other tracking technologies to collect and store your information.</em></p>
            <p>We may use cookies and similar tracking technologies (like web beacons and pixels) to gather information when you interact with our Services. Some online tracking technologies help us maintain the security of our Services and your account, prevent crashes, fix bugs, save your preferences, and assist with basic site functions.</p>
            <p>We also permit third parties and service providers to use online tracking technologies on our Services for analytics and advertising, including to help manage and display advertisements or to tailor advertisements to your interests.</p>
            <p>To the extent these online tracking technologies are deemed to be a "sale"/"sharing" under applicable US state laws, you can opt out of these online tracking technologies by submitting a request as described in section 12 below.</p>
            <p>Specific information about how we use such technologies and how you can refuse certain cookies is set out in our Cookie Notice.</p>
            <h3 className="text-base font-semibold mt-4 mb-2">Google Analytics</h3>
            <p>
              We may share your information with Google Analytics to track and analyze the use of the Services. We may use Google Display Network Impressions Reporting. To opt out of being tracked by Google Analytics across the Services, visit{' '}
              <a href="https://tools.google.com/dlpage/gaoptout" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">https://tools.google.com/dlpage/gaoptout</a>.
              You can opt out of Google Analytics Advertising Features through{' '}
              <a href="https://adssettings.google.com/" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">Ads Settings</a>.
              For more information on Google's privacy practices, visit the{' '}
              <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">Google Privacy &amp; Terms page</a>.
            </p>
          </div>
        </section>

        {/* Section 6 */}
        <section id="ai" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">6. DO WE OFFER ARTIFICIAL INTELLIGENCE-BASED PRODUCTS?</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p><em><strong>In Short:</strong> We offer products, features, or tools powered by artificial intelligence, machine learning, or similar technologies.</em></p>
            <p>As part of our Services, we offer products, features, or tools powered by artificial intelligence, machine learning, or similar technologies (collectively, "AI Products"). These tools are designed to enhance your experience and provide you with innovative solutions. The terms in this Privacy Notice govern your use of the AI Products within our Services.</p>
            <p><strong>Use of AI Technologies</strong></p>
            <p>We provide the AI Products through third-party service providers ("AI Service Providers"), including <strong>Anthropic</strong>. Your input, output, and personal information will be shared with and processed by these AI Service Providers to enable your use of our AI Products. You must not use the AI Products in any way that violates the terms or policies of any AI Service Provider.</p>
            <p><strong>Our AI Products</strong></p>
            <p>Our AI Products are designed for the following functions:</p>
            <ul className="list-disc ml-6 space-y-1">
              <li>AI research</li>
              <li>AI applications</li>
              <li>AI automation</li>
              <li>AI document generation</li>
              <li>Text analysis</li>
              <li>AI predictive analytics</li>
              <li>AI search</li>
            </ul>
            <p><strong>How We Process Your Data Using AI</strong></p>
            <p>All personal information processed using our AI Products is handled in line with our Privacy Notice and our agreement with third parties. This ensures high security and safeguards your personal information throughout the process.</p>
          </div>
        </section>

        {/* Section 7 */}
        <section id="inforetain" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">7. HOW LONG DO WE KEEP YOUR INFORMATION?</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p><em><strong>In Short:</strong> We keep your information for as long as necessary to fulfill the purposes outlined in this Privacy Notice unless otherwise required by law.</em></p>
            <p>We will only keep your personal information for as long as it is necessary for the purposes set out in this Privacy Notice, unless a longer retention period is required or permitted by law. No purpose in this notice will require us keeping your personal information for longer than the period of time in which users have an account with us.</p>
            <p>When we have no ongoing legitimate business need to process your personal information, we will either delete or anonymize such information, or, if this is not possible, then we will securely store your personal information and isolate it from any further processing until deletion is possible.</p>
          </div>
        </section>

        {/* Section 8 */}
        <section id="infosafe" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">8. HOW DO WE KEEP YOUR INFORMATION SAFE?</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p><em><strong>In Short:</strong> We aim to protect your personal information through a system of organizational and technical security measures.</em></p>
            <p>We have implemented appropriate and reasonable technical and organizational security measures designed to protect the security of any personal information we process. However, despite our safeguards and efforts to secure your information, no electronic transmission over the Internet or information storage technology can be guaranteed to be 100% secure, so we cannot promise or guarantee that hackers, cybercriminals, or other unauthorized third parties will not be able to defeat our security and improperly collect, access, steal, or modify your information. Although we will do our best to protect your personal information, transmission of personal information to and from our Services is at your own risk. You should only access the Services within a secure environment.</p>
          </div>
        </section>

        {/* Section 9 */}
        <section id="infominors" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">9. DO WE COLLECT INFORMATION FROM MINORS?</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p><em><strong>In Short:</strong> We do not knowingly collect data from or market to children under 18 years of age.</em></p>
            <p>We do not knowingly collect, solicit data from, or market to children under 18 years of age, nor do we knowingly sell such personal information. By using the Services, you represent that you are at least 18 or that you are the parent or guardian of such a minor and consent to such minor dependent's use of the Services. If we learn that personal information from users less than 18 years of age has been collected, we will deactivate the account and take reasonable measures to promptly delete such data from our records. If you become aware of any data we may have collected from children under age 18, please contact us at{' '}
              <a href="mailto:mrskwiw@gmail.com" className="text-blue-600 dark:text-blue-400 hover:underline">mrskwiw@gmail.com</a>.
            </p>
          </div>
        </section>

        {/* Section 10 */}
        <section id="privacyrights" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">10. WHAT ARE YOUR PRIVACY RIGHTS?</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p><em><strong>In Short:</strong> Depending on your state of residence in the US or in some regions, such as the European Economic Area (EEA), United Kingdom (UK), Switzerland, and Canada, you have rights that allow you greater access to and control over your personal information. You may review, change, or terminate your account at any time, depending on your country, province, or state of residence.</em></p>
            <p>In some regions (like the EEA, UK, Switzerland, and Canada), you have certain rights under applicable data protection laws. These may include the right (i) to request access and obtain a copy of your personal information, (ii) to request rectification or erasure; (iii) to restrict the processing of your personal information; (iv) if applicable, to data portability; and (v) not to be subject to automated decision-making.</p>
            <p>If you are located in the EEA or UK and you believe we are unlawfully processing your personal information, you also have the right to complain to your{' '}
              <a href="https://ec.europa.eu/justice/data-protection/bodies/authorities/index_en.htm" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">Member State data protection authority</a>{' '}
              or{' '}
              <a href="https://ico.org.uk/make-a-complaint/data-protection-complaints/data-protection-complaints/" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">UK data protection authority</a>.
            </p>
            <p>If you are located in Switzerland, you may contact the{' '}
              <a href="https://www.edoeb.admin.ch/edoeb/en/home.html" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">Federal Data Protection and Information Commissioner</a>.
            </p>
            <p id="withdrawconsent"><strong><u>Withdrawing your consent:</u></strong> If we are relying on your consent to process your personal information, you have the right to withdraw your consent at any time by contacting us using the contact details provided in section 14 below.</p>
            <p>However, please note that this will not affect the lawfulness of the processing before its withdrawal.</p>
            <p><strong><u>Opting out of marketing and promotional communications:</u></strong> You can unsubscribe from our marketing and promotional communications at any time by clicking on the unsubscribe link in the emails that we send, or by contacting us using the details provided in section 14 below.</p>
            <h3 className="text-base font-semibold mt-4 mb-2">Account Information</h3>
            <p>If you would at any time like to review or change the information in your account or terminate your account, you can contact us using the contact information provided. Upon your request to terminate your account, we will deactivate or delete your account and information from our active databases. However, we may retain some information in our files to prevent fraud, troubleshoot problems, assist with any investigations, enforce our legal terms and/or comply with applicable legal requirements.</p>
            <p>If you have questions or comments about your privacy rights, you may email us at{' '}
              <a href="mailto:mrskwiw@gmail.com" className="text-blue-600 dark:text-blue-400 hover:underline">mrskwiw@gmail.com</a>.
            </p>
          </div>
        </section>

        {/* Section 11 */}
        <section id="DNT" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">11. CONTROLS FOR DO-NOT-TRACK FEATURES</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p>Most web browsers and some mobile operating systems and mobile applications include a Do-Not-Track ("DNT") feature or setting you can activate to signal your privacy preference not to have data about your online browsing activities monitored and collected. At this stage, no uniform technology standard for recognizing and implementing DNT signals has been finalized. As such, we do not currently respond to DNT browser signals or any other mechanism that automatically communicates your choice not to be tracked online. If a standard for online tracking is adopted that we must follow in the future, we will inform you about that practice in a revised version of this Privacy Notice.</p>
            <p>California law requires us to let you know how we respond to web browser DNT signals. Because there currently is not an industry or legal standard for recognizing or honoring DNT signals, we do not respond to them at this time.</p>
          </div>
        </section>

        {/* Section 12 */}
        <section id="uslaws" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">12. DO UNITED STATES RESIDENTS HAVE SPECIFIC PRIVACY RIGHTS?</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p><em><strong>In Short:</strong> If you are a resident of California, Colorado, Connecticut, Delaware, Florida, Indiana, Iowa, Kentucky, Maryland, Minnesota, Montana, Nebraska, New Hampshire, New Jersey, Oregon, Rhode Island, Tennessee, Texas, Utah, or Virginia, you may have the right to request access to and receive details about the personal information we maintain about you and how we have processed it, correct inaccuracies, get a copy of, or delete your personal information.</em></p>
            <h3 className="text-base font-semibold mt-4 mb-2">Categories of Personal Information We Collect</h3>
            <p>The following table shows the categories of personal information we may collect. We have <strong>not</strong> collected any of these categories in the past twelve (12) months:</p>
            <div className="overflow-x-auto mt-3">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="bg-neutral-100 dark:bg-neutral-800">
                    <th className="border border-neutral-300 dark:border-neutral-600 px-3 py-2 text-left">Category</th>
                    <th className="border border-neutral-300 dark:border-neutral-600 px-3 py-2 text-left">Examples</th>
                    <th className="border border-neutral-300 dark:border-neutral-600 px-3 py-2 text-left">Collected</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['A. Identifiers', 'Contact details, such as real name, alias, postal address, telephone or mobile contact number, unique personal identifier, online identifier, Internet Protocol address, email address, and account name'],
                    ['B. Personal information (CA Customer Records statute)', 'Name, contact information, education, employment, employment history, and financial information'],
                    ['C. Protected classification characteristics', 'Gender, age, date of birth, race and ethnicity, national origin, marital status, and other demographic data'],
                    ['D. Commercial information', 'Transaction information, purchase history, financial details, and payment information'],
                    ['E. Biometric information', 'Fingerprints and voiceprints'],
                    ['F. Internet or other similar network activity', 'Browsing history, search history, online behavior, interest data, and interactions with our and other websites'],
                    ['G. Geolocation data', 'Device location'],
                    ['H. Audio, electronic, sensory, or similar information', 'Images and audio, video or call recordings created in connection with our business activities'],
                    ['I. Professional or employment-related information', 'Business contact details in order to provide you our Services at a business level or job title, work history, and professional qualifications'],
                    ['J. Education Information', 'Student records and directory information'],
                    ['K. Inferences drawn from collected personal information', "Inferences drawn from any of the collected personal information listed above to create a profile or summary about an individual's preferences and characteristics"],
                    ['L. Sensitive personal Information', '—'],
                  ].map(([cat, ex]) => (
                    <tr key={cat} className="even:bg-neutral-50 dark:even:bg-neutral-900">
                      <td className="border border-neutral-300 dark:border-neutral-600 px-3 py-2 align-top">{cat}</td>
                      <td className="border border-neutral-300 dark:border-neutral-600 px-3 py-2 align-top">{ex}</td>
                      <td className="border border-neutral-300 dark:border-neutral-600 px-3 py-2 text-center align-top">NO</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <h3 className="text-base font-semibold mt-4 mb-2">Your Rights</h3>
            <p>You have rights under certain US state data protection laws, including:</p>
            <ul className="list-disc ml-6 space-y-1">
              <li><strong>Right to know</strong> whether or not we are processing your personal data</li>
              <li><strong>Right to access</strong> your personal data</li>
              <li><strong>Right to correct</strong> inaccuracies in your personal data</li>
              <li><strong>Right to request</strong> the deletion of your personal data</li>
              <li><strong>Right to obtain a copy</strong> of the personal data you previously shared with us</li>
              <li><strong>Right to non-discrimination</strong> for exercising your rights</li>
              <li><strong>Right to opt out</strong> of the processing of your personal data if it is used for targeted advertising, the sale of personal data, or profiling</li>
            </ul>
            <h3 className="text-base font-semibold mt-4 mb-2">How to Exercise Your Rights</h3>
            <p>To exercise these rights, you can contact us by visiting{' '}
              <a href="https://content-jumpstart.com/dashboard/settings" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline break-all">
                https://content-jumpstart.com/dashboard/settings
              </a>{' '}
              or by emailing us at{' '}
              <a href="mailto:mrskwiw@gmail.com" className="text-blue-600 dark:text-blue-400 hover:underline">mrskwiw@gmail.com</a>,
              or by referring to the contact details at the bottom of this document.
            </p>
            <h3 className="text-base font-semibold mt-4 mb-2">Request Verification</h3>
            <p>Upon receiving your request, we will need to verify your identity to determine you are the same person about whom we have the information in our system. We will only use personal information provided in your request to verify your identity or authority to make the request.</p>
            <h3 className="text-base font-semibold mt-4 mb-2">Appeals</h3>
            <p>Under certain US state data protection laws, if we decline to take action regarding your request, you may appeal our decision by emailing us at{' '}
              <a href="mailto:mrskwiw@gmail.com" className="text-blue-600 dark:text-blue-400 hover:underline">mrskwiw@gmail.com</a>.
              We will inform you in writing of any action taken or not taken in response to the appeal. If your appeal is denied, you may submit a complaint to your state attorney general.
            </p>
            <h3 className="text-base font-semibold mt-4 mb-2">California "Shine The Light" Law</h3>
            <p>California Civil Code Section 1798.83, also known as the "Shine The Light" law, permits our users who are California residents to request and obtain from us, once a year and free of charge, information about categories of personal information (if any) we disclosed to third parties for direct marketing purposes and the names and addresses of all third parties with which we shared personal information in the immediately preceding calendar year. If you are a California resident and would like to make such a request, please submit your request in writing to us by using the contact details provided in section 14 below.</p>
          </div>
        </section>

        {/* Section 13 */}
        <section id="policyupdates" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">13. DO WE MAKE UPDATES TO THIS NOTICE?</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p><em><strong>In Short:</strong> Yes, we will update this notice as necessary to stay compliant with relevant laws.</em></p>
            <p>We may update this Privacy Notice from time to time. The updated version will be indicated by an updated "Revised" date at the top of this Privacy Notice. If we make material changes to this Privacy Notice, we may notify you either by prominently posting a notice of such changes or by directly sending you a notification. We encourage you to review this Privacy Notice frequently to be informed of how we are protecting your information.</p>
          </div>
        </section>

        {/* Section 14 */}
        <section id="contact" className="mb-8 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">14. HOW CAN YOU CONTACT US ABOUT THIS NOTICE?</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p>If you have questions or comments about this notice, you may email us at{' '}
              <a href="mailto:mrskwiw@gmail.com" className="text-blue-600 dark:text-blue-400 hover:underline">mrskwiw@gmail.com</a>{' '}
              or contact us by post at:
            </p>
            <address className="not-italic">
              <strong>Basement Squirrel Games</strong><br />
              134 Tuscany Ln<br />
              Wentzville, MO 63385<br />
              United States
            </address>
          </div>
        </section>

        {/* Section 15 */}
        <section id="request" className="mb-12 scroll-mt-8">
          <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-4">15. HOW CAN YOU REVIEW, UPDATE, OR DELETE THE DATA WE COLLECT FROM YOU?</h2>
          <div className="space-y-3 text-sm leading-relaxed">
            <p>Based on the applicable laws of your country or state of residence in the US, you may have the right to request access to the personal information we collect from you, details about how we have processed it, correct inaccuracies, or delete your personal information. You may also have the right to withdraw your consent to our processing of your personal information. To request to review, update, or delete your personal information, please visit:{' '}
              <a href="https://content-jumpstart.com/dashboard/settings" target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline break-all">
                https://content-jumpstart.com/dashboard/settings
              </a>.
            </p>
          </div>
        </section>

        <hr className="border-neutral-200 dark:border-neutral-700 mb-6" />
        <p className="text-xs text-neutral-400 dark:text-neutral-500 text-center">
          This Privacy Policy was created using{' '}
          <a href="https://termly.io/products/privacy-policy-generator/" target="_blank" rel="noopener noreferrer" className="hover:underline">Termly's Privacy Policy Generator</a>.
        </p>
      </div>
    </div>
  );
}
