import type { DeliverableDetails } from '@/types/domain';
import { format } from 'date-fns';
import { Clock, CheckCircle, FileText } from 'lucide-react';

interface Props {
  deliverable: DeliverableDetails;
}

export function HistoryTab({ deliverable }: Props) {
  // Build timeline events
  const events = [
    {
      type: 'created',
      timestamp: deliverable.createdAt,
      icon: FileText,
      label: 'Deliverable created',
      color: 'blue',
    },
  ];

  if (deliverable.fileModifiedAt) {
    events.push({
      type: 'modified',
      timestamp: deliverable.fileModifiedAt,
      icon: Clock,
      label: 'File last modified',
      color: 'slate',
    });
  }

  if (deliverable.deliveredAt) {
    events.push({
      type: 'delivered',
      timestamp: deliverable.deliveredAt,
      icon: CheckCircle,
      label: 'Marked as delivered',
      color: 'green',
    });
  }

  // Sort by timestamp descending (most recent first)
  events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  return (
    <div className="p-6">
      <div className="space-y-6">
        {/* Timeline header */}
        <div>
          <h3 className="text-sm font-medium text-slate-900 mb-1">Timeline</h3>
          <p className="text-xs text-slate-500">
            Key events in this deliverable's lifecycle
          </p>
        </div>

        {/* Timeline */}
        <div className="relative">
          {events.length === 0 ? (
            <div className="text-sm text-slate-500 text-center py-8">
              No events recorded
            </div>
          ) : (
            <div className="space-y-4">
              {events.map((event, index) => {
                const Icon = event.icon;
                const isLast = index === events.length - 1;

                return (
                  <div key={index} className="relative">
                    {/* Connector line */}
                    {!isLast && (
                      <div
                        className="absolute left-5 top-10 bottom-0 w-0.5 bg-slate-200"
                        style={{ height: '24px' }}
                      />
                    )}

                    {/* Event */}
                    <div className="flex items-start gap-4">
                      {/* Icon */}
                      <div className={`
                        flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center
                        ${event.color === 'green' ? 'bg-green-100' :
                          event.color === 'blue' ? 'bg-blue-100' :
                          'bg-slate-100'}
                      `}>
                        <Icon className={`
                          h-5 w-5
                          ${event.color === 'green' ? 'text-green-600' :
                            event.color === 'blue' ? 'text-blue-600' :
                            'text-slate-600'}
                        `} />
                      </div>

                      {/* Content */}
                      <div className="flex-1 pt-1">
                        <div className="text-sm font-medium text-slate-900">
                          {event.label}
                        </div>
                        <div className="text-xs text-slate-500 mt-0.5">
                          {format(new Date(event.timestamp), 'PPpp')}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Additional info */}
        <div className="pt-4 border-t border-slate-200">
          <div className="text-xs text-slate-500">
            <p className="mb-2">
              <strong>Note:</strong> Download tracking is not currently enabled.
            </p>
            <p>
              Future versions will include detailed download history,
              including timestamps, users, and IP addresses.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
