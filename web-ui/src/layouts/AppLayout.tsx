import { useState } from 'react';
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

function HamburgerIcon({ open }: { open: boolean }) {
  return (
    <svg
      className="h-6 w-6"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      viewBox="0 0 24 24"
    >
      {open ? (
        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
      ) : (
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
      )}
    </svg>
  );
}

function SidebarContent({ onNavigate, logout }: { onNavigate: () => void; logout: () => void }) {
  return (
    <>
      <nav className="flex-1 space-y-0.5 p-3">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === '/'}
            onClick={onNavigate}
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
    </>
  );
}

export function AppLayout() {
  const { logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const closeMobile = () => setMobileOpen(false);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/40 md:hidden"
          onClick={closeMobile}
          aria-hidden="true"
        />
      )}

      {/* Mobile slide-in sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-64 flex-col border-r border-gray-200 bg-white transition-transform duration-200 md:hidden ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
          <h1 className="text-lg font-bold text-gray-900">HomeIOT</h1>
          <button
            onClick={closeMobile}
            className="rounded-md p-1 text-gray-500 hover:bg-gray-100"
            aria-label="Close menu"
          >
            <HamburgerIcon open={true} />
          </button>
        </div>
        <SidebarContent onNavigate={closeMobile} logout={logout} />
      </aside>

      {/* Desktop sidebar */}
      <aside className="hidden w-56 flex-col border-r border-gray-200 bg-white md:flex">
        <div className="border-b border-gray-200 px-5 py-4">
          <h1 className="text-lg font-bold text-gray-900">HomeIOT</h1>
        </div>
        <SidebarContent onNavigate={() => {}} logout={logout} />
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile top bar */}
        <header className="flex items-center border-b border-gray-200 bg-white px-4 py-3 md:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded-md p-1 text-gray-600 hover:bg-gray-100"
            aria-label="Open menu"
          >
            <HamburgerIcon open={false} />
          </button>
          <span className="ml-3 text-base font-bold text-gray-900">HomeIOT</span>
        </header>

        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
