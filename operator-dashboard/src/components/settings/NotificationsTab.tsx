export function NotificationsTab() {
  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Email Notifications</h3>
        <div className="space-y-4">
          {[
            { id: 'deliverable_ready', label: 'Deliverable ready for client', default: true },
            { id: 'new_project', label: 'New project assigned', default: true },
            { id: 'client_feedback', label: 'Client feedback received', default: false },
            { id: 'deadline_approaching', label: 'Deadline approaching (24h)', default: true },
          ].map(n => (
            <div key={n.id} className="flex items-center justify-between">
              <span className="text-sm text-neutral-700 dark:text-neutral-300">{n.label}</span>
              <label className="relative inline-flex cursor-pointer items-center">
                <input type="checkbox" defaultChecked={n.default} className="peer sr-only" />
                <div className="peer h-6 w-11 rounded-full bg-neutral-200 dark:bg-neutral-700 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 dark:border-neutral-600 after:bg-white dark:after:bg-neutral-300 after:transition-all after:content-[''] peer-checked:bg-primary-600 dark:peer-checked:bg-primary-500 peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
              </label>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">In-App Notifications</h3>
        <div className="space-y-4">
          {[
            { id: 'desktop_notifications', label: 'Desktop notifications', default: false },
            { id: 'sound_alerts', label: 'Sound alerts', default: false },
            { id: 'daily_summary', label: 'Daily activity summary (9:00 AM)', default: true },
          ].map(n => (
            <div key={n.id} className="flex items-center justify-between">
              <span className="text-sm text-neutral-700 dark:text-neutral-300">{n.label}</span>
              <label className="relative inline-flex cursor-pointer items-center">
                <input type="checkbox" defaultChecked={n.default} className="peer sr-only" />
                <div className="peer h-6 w-11 rounded-full bg-neutral-200 dark:bg-neutral-700 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 dark:border-neutral-600 after:bg-white dark:after:bg-neutral-300 after:transition-all after:content-[''] peer-checked:bg-primary-600 dark:peer-checked:bg-primary-500 peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
              </label>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
