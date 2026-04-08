import { NavLink, Outlet } from 'react-router';
import { useAuth } from '../lib/auth';

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/devices', label: 'Devices' },
  { to: '/modules', label: 'Modules' },
  { to: '/ota', label: 'OTA' },
  { to: '/users', label: 'Users' },
  { to: '/dev-commands', label: 'Dev Commands' },
];

export function AppLayout() {
  const { logout } = useAuth();

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="flex w-56 flex-col border-r border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-5 py-4">
          <h1 className="text-lg font-bold text-gray-900">HomeIOT</h1>
        </div>
        <nav className="flex-1 space-y-0.5 p-3">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === '/'}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm font-medium ${
                  isActive
                    ? 'bg-gray-100 text-gray-900'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-gray-200 p-3">
          <button
            onClick={logout}
            className="w-full rounded-md px-3 py-2 text-left text-sm text-gray-600 hover:bg-gray-50"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
