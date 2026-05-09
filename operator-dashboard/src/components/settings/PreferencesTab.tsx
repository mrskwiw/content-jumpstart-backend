import { useTheme } from '@/contexts/ThemeContext';

export function PreferencesTab() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-6">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">UI Preferences</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Theme</label>
            <select value={theme === 'system' ? 'light' : theme} onChange={e => setTheme(e.target.value as 'light' | 'dark')} className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500">
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">Timezone</label>
            <select className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500">
              <option value="UTC">UTC (Coordinated Universal Time)</option>
              <optgroup label="Americas">
                <option value="America/New_York">Eastern Time (ET)</option>
                <option value="America/Chicago">Central Time (CT)</option>
                <option value="America/Denver">Mountain Time (MT)</option>
                <option value="America/Los_Angeles">Pacific Time (PT)</option>
                <option value="America/Anchorage">Alaska Time (AKT)</option>
                <option value="Pacific/Honolulu">Hawaii-Aleutian Time (HAT)</option>
                <option value="America/Toronto">Toronto</option>
                <option value="America/Vancouver">Vancouver</option>
                <option value="America/Mexico_City">Mexico City</option>
                <option value="America/Sao_Paulo">São Paulo</option>
                <option value="America/Buenos_Aires">Buenos Aires</option>
              </optgroup>
              <optgroup label="Europe">
                <option value="Europe/London">London (GMT/BST)</option>
                <option value="Europe/Paris">Paris (CET/CEST)</option>
                <option value="Europe/Berlin">Berlin (CET/CEST)</option>
                <option value="Europe/Rome">Rome (CET/CEST)</option>
                <option value="Europe/Madrid">Madrid (CET/CEST)</option>
                <option value="Europe/Amsterdam">Amsterdam (CET/CEST)</option>
                <option value="Europe/Brussels">Brussels (CET/CEST)</option>
                <option value="Europe/Vienna">Vienna (CET/CEST)</option>
                <option value="Europe/Stockholm">Stockholm (CET/CEST)</option>
                <option value="Europe/Warsaw">Warsaw (CET/CEST)</option>
                <option value="Europe/Istanbul">Istanbul (TRT)</option>
                <option value="Europe/Moscow">Moscow (MSK)</option>
              </optgroup>
              <optgroup label="Asia">
                <option value="Asia/Dubai">Dubai (GST)</option>
                <option value="Asia/Kolkata">India (IST)</option>
                <option value="Asia/Bangkok">Bangkok (ICT)</option>
                <option value="Asia/Singapore">Singapore (SGT)</option>
                <option value="Asia/Hong_Kong">Hong Kong (HKT)</option>
                <option value="Asia/Shanghai">Shanghai (CST)</option>
                <option value="Asia/Tokyo">Tokyo (JST)</option>
                <option value="Asia/Seoul">Seoul (KST)</option>
              </optgroup>
              <optgroup label="Australia & Pacific">
                <option value="Australia/Sydney">Sydney (AEDT/AEST)</option>
                <option value="Australia/Melbourne">Melbourne (AEDT/AEST)</option>
                <option value="Australia/Brisbane">Brisbane (AEST)</option>
                <option value="Australia/Perth">Perth (AWST)</option>
                <option value="Pacific/Auckland">Auckland (NZDT/NZST)</option>
              </optgroup>
              <optgroup label="Africa">
                <option value="Africa/Cairo">Cairo (EET)</option>
                <option value="Africa/Johannesburg">Johannesburg (SAST)</option>
                <option value="Africa/Lagos">Lagos (WAT)</option>
              </optgroup>
            </select>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-neutral-700 dark:text-neutral-300">Compact view mode</span>
            <label className="relative inline-flex cursor-pointer items-center">
              <input type="checkbox" className="peer sr-only" />
              <div className="peer h-6 w-11 rounded-full bg-neutral-200 dark:bg-neutral-700 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 dark:border-neutral-600 after:bg-white dark:after:bg-neutral-300 after:transition-all after:content-[''] peer-checked:bg-primary-600 dark:peer-checked:bg-primary-500 peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
            </label>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-neutral-700 dark:text-neutral-300">Auto-refresh data</span>
            <label className="relative inline-flex cursor-pointer items-center">
              <input type="checkbox" defaultChecked className="peer sr-only" />
              <div className="peer h-6 w-11 rounded-full bg-neutral-200 dark:bg-neutral-700 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 dark:border-neutral-600 after:bg-white dark:after:bg-neutral-300 after:transition-all after:content-[''] peer-checked:bg-primary-600 dark:peer-checked:bg-primary-500 peer-checked:after:translate-x-full peer-checked:after:border-white"></div>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
