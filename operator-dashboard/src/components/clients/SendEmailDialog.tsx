import { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { X, Send, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { clientsApi, type SendEmailInput } from '@/api/clients';
import type { Client } from '@/types/domain';
import { getApiErrorMessage } from '@/utils/apiError';

type EmailTypeValue = SendEmailInput['email_type'];

interface EmailTypeConfig {
  label: string;
  defaultSubject: string;
  defaultBody: (clientName: string) => string;
  variables: { key: string; label: string; placeholder: string; required: boolean; defaultValue?: string }[];
}

const EMAIL_TYPES: Record<EmailTypeValue, EmailTypeConfig> = {
  general: {
    label: 'General Message',
    defaultSubject: '',
    defaultBody: () => '',
    variables: [],
  },
  deliverable: {
    label: 'Content Package Ready',
    defaultSubject: "Your Content Package is Ready! 🎉",
    defaultBody: (name) => `Hi ${name},

Great news! Your {post_count}-post content package is complete and ready to use.

What's Included:
• {post_count} custom social media posts
• Brand voice guide
• Quality assurance report
• Posting schedule recommendations

If you need any revisions (up to 5 changes included), just reply with specifics.

Looking forward to seeing your content perform!

Best regards,
The Content Jumpstart Team`,
    variables: [
      { key: 'post_count', label: 'Number of Posts', placeholder: '30', required: true, defaultValue: '30' },
    ],
  },
  feedback_request: {
    label: 'Request Feedback',
    defaultSubject: "How are your posts performing? 📊",
    defaultBody: (name) => `Hi ${name},

It's been 2 weeks since we delivered your content package. We'd love to hear how it's going!

Quick Questions:
1. How many posts have you used so far?
2. Which posts got the best engagement?
3. Any posts that didn't resonate?
4. Do you need any adjustments for future rounds?

Reply to this email or visit: {feedback_link}

Thanks for your time!

Best regards,
The Content Jumpstart Team`,
    variables: [
      { key: 'feedback_link', label: 'Feedback Link', placeholder: 'https://yoursite.com/feedback', required: false },
    ],
  },
  invoice_reminder: {
    label: 'Invoice Reminder',
    defaultSubject: "Friendly Reminder: Invoice #{invoice_number} 💳",
    defaultBody: (name) => `Hi ${name},

This is a friendly reminder that Invoice #{invoice_number} for ${'{amount}'} is now {days_overdue} days overdue.

Invoice Details:
• Amount: ${'{amount}'}
• Due Date: {due_date}
• Service: 30-Day Content Package

Pay Now: {payment_link}

If you've already paid, please disregard. Questions? Just reply to this email.

Thank you!

Best regards,
The Content Jumpstart Team`,
    variables: [
      { key: 'invoice_number', label: 'Invoice Number', placeholder: 'INV-001', required: true },
      { key: 'amount', label: 'Amount', placeholder: '1200.00', required: true },
      { key: 'days_overdue', label: 'Days Overdue', placeholder: '7', required: true },
      { key: 'due_date', label: 'Due Date', placeholder: 'March 15, 2026', required: true },
      { key: 'payment_link', label: 'Payment Link', placeholder: 'https://pay.stripe.com/...', required: false },
    ],
  },
  revision_confirmation: {
    label: 'Revision Complete',
    defaultSubject: "Revision Complete ✅",
    defaultBody: (name) => `Hi ${name},

Your revision request has been completed!

What Changed:
{revision_summary}

You have {remaining_revisions} revision changes remaining in your package.

Please review and let us know if you need any further adjustments.

Best regards,
The Content Jumpstart Team`,
    variables: [
      { key: 'revision_summary', label: 'What Changed', placeholder: 'Updated tone on LinkedIn posts 3, 7, and 12', required: true },
      { key: 'remaining_revisions', label: 'Revisions Remaining', placeholder: '3', required: false },
    ],
  },
};

function substituteVariables(text: string, vars: Record<string, string>): string {
  let result = text;
  for (const [key, value] of Object.entries(vars)) {
    if (value) {
      result = result.replaceAll(`{${key}}`, value);
    }
  }
  return result;
}

interface SendEmailDialogProps {
  client: Client;
  onClose: () => void;
  onSuccess: () => void;
}

export function SendEmailDialog({ client, onClose, onSuccess }: SendEmailDialogProps) {
  const [emailType, setEmailType] = useState<EmailTypeValue>('general');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [variables, setVariables] = useState<Record<string, string>>({});

  const config = EMAIL_TYPES[emailType];

  // Auto-fill subject and body when type changes. Effect-based prop->state
  // sync is the established pattern for repopulating this form on emailType change.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional prop->state sync on emailType change
    setSubject(config.defaultSubject);
    setBody(config.defaultBody(client.name));
    const defaults: Record<string, string> = {};
    for (const v of config.variables) {
      if (v.defaultValue !== undefined) defaults[v.key] = v.defaultValue;
    }
    setVariables(defaults);
  }, [emailType, client.name]); // eslint-disable-line react-hooks/exhaustive-deps

  const renderedBody = substituteVariables(body, variables);
  const renderedSubject = substituteVariables(subject, variables);

  const sendMutation = useMutation({
    mutationFn: () =>
      clientsApi.sendEmail(client.id, {
        email_type: emailType,
        subject: renderedSubject,
        content: renderedBody,
      }),
    onSuccess: () => {
      onSuccess();
    },
  });

  const hasRequiredVariables = config.variables
    .filter((v) => v.required)
    .every((v) => variables[v.key]?.trim());

  const canSend =
    renderedSubject.trim().length > 0 &&
    renderedBody.trim().length > 0 &&
    hasRequiredVariables &&
    !sendMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-2xl rounded-xl bg-white dark:bg-neutral-900 shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700 shrink-0">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
              Send Email
            </h2>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              To: {client.name}{client.email ? ` <${client.email}>` : ''}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          {/* No email warning */}
          {!client.email && (
            <div className="flex items-center gap-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 px-4 py-3 text-sm text-amber-700 dark:text-amber-300">
              <AlertCircle className="h-4 w-4 shrink-0" />
              This client has no email address on file. Add one via Edit Client before sending.
            </div>
          )}

          {/* Type selector */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
              Email Type
            </label>
            <select
              value={emailType}
              onChange={(e) => setEmailType(e.target.value as EmailTypeValue)}
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
            >
              {(Object.entries(EMAIL_TYPES) as [EmailTypeValue, EmailTypeConfig][]).map(([val, cfg]) => (
                <option key={val} value={val}>{cfg.label}</option>
              ))}
            </select>
          </div>

          {/* Dynamic variable fields */}
          {config.variables.length > 0 && (
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 space-y-3 bg-neutral-50 dark:bg-neutral-800/50">
              <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                Template Variables
              </p>
              {config.variables.map((v) => (
                <div key={v.key}>
                  <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                    {v.label}
                    {v.required && <span className="text-red-500 ml-1">*</span>}
                  </label>
                  <input
                    type="text"
                    value={variables[v.key] ?? ''}
                    onChange={(e) => setVariables((prev) => ({ ...prev, [v.key]: e.target.value }))}
                    placeholder={v.placeholder}
                    className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
                  />
                </div>
              ))}
            </div>
          )}

          {/* Subject */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
              Subject
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Email subject..."
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400"
            />
          </div>

          {/* Body */}
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">
              Message
            </label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Write your message..."
              rows={10}
              className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm placeholder-neutral-400 dark:placeholder-neutral-500 focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:focus:ring-primary-400 resize-none font-mono"
            />
            {variables && Object.values(variables).some(Boolean) && (
              <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                Variables substituted in preview — body above is editable.
              </p>
            )}
          </div>

          {/* Send result */}
          {sendMutation.isSuccess && (
            <div className="flex items-center gap-2 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-700 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              {sendMutation.data.status === 'sent'
                ? 'Email sent successfully and logged to communication history.'
                : 'Email logged to communication history (dev mode — no SMTP configured).'}
            </div>
          )}

          {sendMutation.isError && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 px-4 py-3 text-sm text-red-700 dark:text-red-300">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {getApiErrorMessage(sendMutation.error)}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-neutral-200 dark:border-neutral-700 shrink-0">
          {sendMutation.isSuccess ? (
            <button
              onClick={onClose}
              className="ml-auto rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600"
            >
              Done
            </button>
          ) : (
            <>
              <button
                onClick={onClose}
                className="text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100"
              >
                Cancel
              </button>
              <button
                onClick={() => sendMutation.mutate()}
                disabled={!canSend || !client.email}
                className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {sendMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    Send Email
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
