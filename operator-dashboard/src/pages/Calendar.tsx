import { useState, useMemo } from 'react';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Clock,
  FileText,
  Download,
  Plus,
  Users,
  Filter,
  X,
} from 'lucide-react';
import {
  format,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  isSameMonth,
  isSameDay,
  isToday,
  addMonths,
  subMonths,
  parseISO,
} from 'date-fns';

type ViewMode = 'month' | 'week' | 'list';

type EventType = 'post' | 'deadline' | 'team';

interface CalendarEvent {
  id: string;
  title: string;
  date: string; // ISO date string
  type: EventType;
  client?: string;
  project?: string;
  description?: string;
  time?: string;
}

export default function Calendar() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState<ViewMode>('month');
  const [selectedEventTypes, setSelectedEventTypes] = useState<EventType[]>(['post', 'deadline', 'team']);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  // Mock events - would come from API
  const mockEvents: CalendarEvent[] = [
    { id: '1', title: 'LinkedIn Post - TechFlow', date: '2024-12-18', type: 'post', client: 'TechFlow Solutions', project: 'Q4 Campaign', time: '09:00 AM' },
    { id: '2', title: 'Deliverable Due - Creative Agency', date: '2024-12-19', type: 'deadline', client: 'Creative Agency Pro', project: 'Holiday Series', time: '05:00 PM' },
    { id: '3', title: 'Team Meeting', date: '2024-12-20', type: 'team', description: 'Weekly content review', time: '02:00 PM' },
    { id: '4', title: 'Twitter Thread - Marketing Masters', date: '2024-12-20', type: 'post', client: 'Marketing Masters', project: 'Social Strategy', time: '11:00 AM' },
    { id: '5', title: 'Blog Post - Content Kings', date: '2024-12-22', type: 'post', client: 'Content Kings', project: 'SEO Initiative', time: '10:00 AM' },
    { id: '6', title: 'Final Review - Digital Dynamics', date: '2024-12-23', type: 'deadline', client: 'Digital Dynamics', project: 'Brand Refresh', time: '03:00 PM' },
    { id: '7', title: 'Facebook Posts - TechFlow', date: '2024-12-24', type: 'post', client: 'TechFlow Solutions', project: 'Q4 Campaign', time: '01:00 PM' },
    { id: '8', title: 'Team Out of Office', date: '2024-12-25', type: 'team', description: 'Holiday - Office Closed' },
    { id: '9', title: 'LinkedIn Carousel - Creative Agency', date: '2024-12-26', type: 'post', client: 'Creative Agency Pro', project: 'Year End Wrap', time: '08:00 AM' },
    { id: '10', title: 'Project Kickoff - New Client', date: '2024-12-27', type: 'team', description: 'Discovery call with GrowthCo', time: '10:00 AM' },
    { id: '11', title: 'Deliverable Package - Marketing Masters', date: '2024-12-30', type: 'deadline', client: 'Marketing Masters', project: 'Q1 Prep', time: '04:00 PM' },
    { id: '12', title: 'Email Newsletter - Content Kings', date: '2024-12-31', type: 'post', client: 'Content Kings', project: 'Monthly Newsletter', time: '09:00 AM' },
  ];

  // Filter events by selected types
  const filteredEvents = useMemo(() => {
    return mockEvents.filter(event => selectedEventTypes.includes(event.type));
  }, [mockEvents, selectedEventTypes]);

  // Get calendar days for current month view
  const calendarDays = useMemo(() => {
    const start = startOfWeek(startOfMonth(currentDate));
    const end = endOfWeek(endOfMonth(currentDate));
    return eachDayOfInterval({ start, end });
  }, [currentDate]);

  // Get events for a specific date
  const getEventsForDate = (date: Date) => {
    return filteredEvents.filter(event =>
      isSameDay(parseISO(event.date), date)
    );
  };

  // Get upcoming events (next 7 days)
  const upcomingEvents = useMemo(() => {
    const today = new Date();
    const sevenDaysLater = new Date(today);
    sevenDaysLater.setDate(today.getDate() + 7);

    return filteredEvents
      .filter(event => {
        const eventDate = parseISO(event.date);
        return eventDate >= today && eventDate <= sevenDaysLater;
      })
      .sort((a, b) => parseISO(a.date).getTime() - parseISO(b.date).getTime());
  }, [filteredEvents]);

  // Toggle event type filter
  const toggleEventType = (type: EventType) => {
    setSelectedEventTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  // Navigate months
  const goToPreviousMonth = () => setCurrentDate(subMonths(currentDate, 1));
  const goToNextMonth = () => setCurrentDate(addMonths(currentDate, 1));
  const goToToday = () => setCurrentDate(new Date());

  // Get event type badge color
  const getEventTypeBadge = (type: EventType) => {
    switch (type) {
      case 'post':
        return 'bg-primary-100 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 border-primary-200 dark:border-primary-700';
      case 'deadline':
        return 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300 border-red-200 dark:border-red-700';
      case 'team':
        return 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-700';
    }
  };

  const getEventTypeIcon = (type: EventType) => {
    switch (type) {
      case 'post':
        return FileText;
      case 'deadline':
        return Clock;
      case 'team':
        return Users;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100">Calendar</h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Posting schedules, delivery deadlines, and team availability
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-2 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800">
            <Plus className="h-4 w-4" />
            Add Event
          </button>
          <button className="inline-flex items-center gap-2 rounded-lg bg-primary-600 dark:bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 dark:hover:bg-primary-600">
            <Download className="h-4 w-4" />
            Export ICS
          </button>
        </div>
      </header>

      {/* Filters */}
      <div className="flex items-center gap-4 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-neutral-400 dark:text-neutral-500" />
          <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">Filter by:</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => toggleEventType('post')}
            className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
              selectedEventTypes.includes('post')
                ? 'border-primary-600 dark:border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800'
            }`}
          >
            <FileText className="h-3 w-3" />
            Posts
            {!selectedEventTypes.includes('post') && <X className="h-3 w-3" />}
          </button>
          <button
            onClick={() => toggleEventType('deadline')}
            className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
              selectedEventTypes.includes('deadline')
                ? 'border-red-600 dark:border-red-500 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
                : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800'
            }`}
          >
            <Clock className="h-3 w-3" />
            Deadlines
            {!selectedEventTypes.includes('deadline') && <X className="h-3 w-3" />}
          </button>
          <button
            onClick={() => toggleEventType('team')}
            className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
              selectedEventTypes.includes('team')
                ? 'border-emerald-600 dark:border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300'
                : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800'
            }`}
          >
            <Users className="h-3 w-3" />
            Team
            {!selectedEventTypes.includes('team') && <X className="h-3 w-3" />}
          </button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Main Calendar */}
        <div className="space-y-4">
          {/* Calendar Navigation */}
          <div className="flex items-center justify-between rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
            <div className="flex items-center gap-2">
              <button
                onClick={goToPreviousMonth}
                className="inline-flex items-center justify-center rounded-lg border border-neutral-200 dark:border-neutral-700 p-2 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                onClick={goToNextMonth}
                className="inline-flex items-center justify-center rounded-lg border border-neutral-200 dark:border-neutral-700 p-2 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
            <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
              {format(currentDate, 'MMMM yyyy')}
            </h2>
            <button
              onClick={goToToday}
              className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-4 py-2 text-sm font-medium text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-800"
            >
              Today
            </button>
          </div>

          {/* View Tabs */}
          <div className="flex items-center gap-2 border-b border-neutral-200 dark:border-neutral-700">
            <button
              onClick={() => setViewMode('month')}
              className={`border-b-2 px-4 py-2 text-sm font-medium ${
                viewMode === 'month'
                  ? 'border-primary-600 dark:border-primary-500 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'
              }`}
            >
              Month View
            </button>
            <button
              onClick={() => setViewMode('week')}
              className={`border-b-2 px-4 py-2 text-sm font-medium ${
                viewMode === 'week'
                  ? 'border-primary-600 dark:border-primary-500 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'
              }`}
            >
              Week View
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`border-b-2 px-4 py-2 text-sm font-medium ${
                viewMode === 'list'
                  ? 'border-primary-600 dark:border-primary-500 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-neutral-100'
              }`}
            >
              List View
            </button>
          </div>

          {/* Calendar Grid (Month View) */}
          {viewMode === 'month' && (
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
              {/* Day headers */}
              <div className="grid grid-cols-7 gap-2 mb-2">
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                  <div key={day} className="text-center text-sm font-semibold text-neutral-600 dark:text-neutral-400 py-2">
                    {day}
                  </div>
                ))}
              </div>

              {/* Calendar days */}
              <div className="grid grid-cols-7 gap-2">
                {calendarDays.map((day, index) => {
                  const dayEvents = getEventsForDate(day);
                  const isCurrentMonth = isSameMonth(day, currentDate);
                  const isTodayDate = isToday(day);

                  return (
                    <div
                      key={index}
                      onClick={() => setSelectedDate(day)}
                      className={`min-h-[100px] rounded-lg border p-2 cursor-pointer transition-colors ${
                        isTodayDate
                          ? 'border-primary-600 dark:border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                          : selectedDate && isSameDay(day, selectedDate)
                          ? 'border-primary-400 dark:border-primary-600 bg-primary-50 dark:bg-primary-900/20'
                          : isCurrentMonth
                          ? 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 hover:bg-neutral-50 dark:hover:bg-neutral-800'
                          : 'border-neutral-100 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-800'
                      }`}
                    >
                      <div className={`text-sm font-medium mb-1 ${
                        isTodayDate
                          ? 'text-primary-700 dark:text-primary-300'
                          : isCurrentMonth
                          ? 'text-neutral-900 dark:text-neutral-100'
                          : 'text-neutral-400 dark:text-neutral-600'
                      }`}>
                        {format(day, 'd')}
                      </div>
                      <div className="space-y-1">
                        {dayEvents.slice(0, 3).map(event => {
                          const Icon = getEventTypeIcon(event.type);
                          return (
                            <div
                              key={event.id}
                              className={`rounded px-1.5 py-0.5 text-xs font-medium border ${getEventTypeBadge(event.type)}`}
                            >
                              <div className="flex items-center gap-1 truncate">
                                <Icon className="h-3 w-3 flex-shrink-0" />
                                <span className="truncate">{event.title.split(' - ')[0]}</span>
                              </div>
                            </div>
                          );
                        })}
                        {dayEvents.length > 3 && (
                          <div className="text-xs text-neutral-500 dark:text-neutral-400 px-1.5">
                            +{dayEvents.length - 3} more
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Week View */}
          {viewMode === 'week' && (
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-8">
              <div className="flex flex-col items-center justify-center text-center">
                <div className="rounded-full bg-primary-100 dark:bg-primary-900/20 p-4 mb-4">
                  <CalendarIcon className="h-12 w-12 text-primary-600 dark:text-primary-400" />
                </div>
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                  Week View
                </h3>
                <p className="text-sm text-neutral-600 dark:text-neutral-400 max-w-md">
                  Detailed week view with hourly time slots and drag-and-drop scheduling.
                </p>
              </div>
            </div>
          )}

          {/* List View */}
          {viewMode === 'list' && (
            <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
              <div className="divide-y divide-neutral-200 dark:divide-neutral-700">
                {filteredEvents
                  .sort((a, b) => parseISO(a.date).getTime() - parseISO(b.date).getTime())
                  .map(event => {
                    const Icon = getEventTypeIcon(event.type);
                    return (
                      <div key={event.id} className="p-4 hover:bg-neutral-50 dark:hover:bg-neutral-800">
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3">
                            <div className={`rounded-lg p-2 ${
                              event.type === 'post' ? 'bg-primary-100 dark:bg-primary-900/20' :
                              event.type === 'deadline' ? 'bg-red-100 dark:bg-red-900/20' :
                              'bg-emerald-100 dark:bg-emerald-900/20'
                            }`}>
                              <Icon className={`h-4 w-4 ${
                                event.type === 'post' ? 'text-primary-600 dark:text-primary-400' :
                                event.type === 'deadline' ? 'text-red-600 dark:text-red-400' :
                                'text-emerald-600 dark:text-emerald-400'
                              }`} />
                            </div>
                            <div>
                              <h4 className="font-medium text-neutral-900 dark:text-neutral-100">{event.title}</h4>
                              {event.client && (
                                <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                                  Client: {event.client} • Project: {event.project}
                                </p>
                              )}
                              {event.description && (
                                <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{event.description}</p>
                              )}
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                              {format(parseISO(event.date), 'MMM d, yyyy')}
                            </p>
                            {event.time && (
                              <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{event.time}</p>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar - Upcoming Events */}
        <div className="space-y-4">
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Upcoming Events</h3>
            <div className="space-y-3">
              {upcomingEvents.length > 0 ? (
                upcomingEvents.map(event => {
                  const Icon = getEventTypeIcon(event.type);
                  const eventDate = parseISO(event.date);
                  return (
                    <div key={event.id} className="rounded-lg border border-neutral-200 dark:border-neutral-700 p-3 hover:border-primary-300 dark:hover:border-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors cursor-pointer">
                      <div className="flex items-start gap-2 mb-2">
                        <div className={`rounded p-1 ${
                          event.type === 'post' ? 'bg-primary-100 dark:bg-primary-900/20' :
                          event.type === 'deadline' ? 'bg-red-100 dark:bg-red-900/20' :
                          'bg-emerald-100 dark:bg-emerald-900/20'
                        }`}>
                          <Icon className={`h-3 w-3 ${
                            event.type === 'post' ? 'text-primary-600 dark:text-primary-400' :
                            event.type === 'deadline' ? 'text-red-600 dark:text-red-400' :
                            'text-emerald-600 dark:text-emerald-400'
                          }`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">{event.title}</p>
                          <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
                            {format(eventDate, 'MMM d')} {event.time && `• ${event.time}`}
                          </p>
                        </div>
                      </div>
                      {event.client && (
                        <div className="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400">
                          <span className="truncate">{event.client}</span>
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-8">
                  <CalendarIcon className="h-8 w-8 text-neutral-300 dark:text-neutral-700 mx-auto mb-2" />
                  <p className="text-sm text-neutral-500 dark:text-neutral-400">No upcoming events</p>
                </div>
              )}
            </div>
          </div>

          {/* Quick Stats */}
          <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-4">
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">This Week</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-primary-600 dark:text-primary-400" />
                  <span className="text-sm text-neutral-700 dark:text-neutral-300">Scheduled Posts</span>
                </div>
                <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                  {filteredEvents.filter(e => e.type === 'post').length}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-red-600 dark:text-red-400" />
                  <span className="text-sm text-neutral-700 dark:text-neutral-300">Deadlines</span>
                </div>
                <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                  {filteredEvents.filter(e => e.type === 'deadline').length}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  <span className="text-sm text-neutral-700 dark:text-neutral-300">Team Events</span>
                </div>
                <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                  {filteredEvents.filter(e => e.type === 'team').length}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
