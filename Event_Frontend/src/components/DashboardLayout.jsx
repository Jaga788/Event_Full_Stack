import { Link } from "react-router-dom";
import { LogOut } from "lucide-react";

function DashboardLayout({
  user,
  roleLabel,
  onLogout,
  eyebrow,
  title,
  description,
  navItems,
  activeItem,
  onNavigate,
  stats,
  variant = "default",
  workspaceRef,
  children,
}) {
  const initials = user.full_name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  return (
    <div className={`dashboard-layout dashboard-layout-${variant}`}>
      <aside className="dashboard-sidebar">
        <Link className="dashboard-brand" to="/">
          <span className="dashboard-brand-mark">J</span>
          <span>Jaga Events<small>EVENT MANAGEMENT</small></span>
        </Link>
        <p className="dashboard-sidebar-label">{roleLabel} workspace</p>
        <nav className="dashboard-navigation" aria-label={`${roleLabel} navigation`}>
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={activeItem === item.id ? "active" : ""}
              aria-current={activeItem === item.id ? "page" : undefined}
              disabled={item.disabled}
              onClick={() => onNavigate(item.id)}
            >
              <span className="dashboard-nav-icon" aria-hidden="true">
                {item.icon ? <item.icon size={16} strokeWidth={1.8} /> : <span className="dashboard-nav-marker" />}
              </span>
              {item.label}
              {item.count != null && <span className="dashboard-nav-count">{item.count}</span>}
            </button>
          ))}
        </nav>
        <div className={`dashboard-account${onLogout ? " dashboard-account-admin" : ""}`}>
          <div className="dashboard-account-profile">
            <span className="dashboard-avatar">{initials}</span>
            <span className="dashboard-account-copy">
              <strong>{user.full_name}</strong>
              <small>{roleLabel}</small>
            </span>
          </div>
          {onLogout && (
            <div className="dashboard-account-actions">
              <Link to="/">Visit website</Link>
              <button type="button" onClick={onLogout}>
                <LogOut size={15} aria-hidden="true" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </aside>

      <main className="dashboard-main">
        <header className="dashboard-header" id="dashboard-overview">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h1>{title}</h1>
            <p>{description}</p>
          </div>
          <span className="dashboard-role-badge">{roleLabel}</span>
        </header>
        {stats?.length > 0 && (
          <section className="dashboard-stats" aria-label="Workspace summary">
            {stats.map((stat) => (
              <article className="dashboard-stat" key={stat.label}>
                <span>{stat.label}</span>
                <strong>{stat.value}</strong>
                {stat.detail && <small>{stat.detail}</small>}
              </article>
            ))}
          </section>
        )}
        <div ref={workspaceRef} className="dashboard-workspace">{children}</div>
      </main>
    </div>
  );
}

export default DashboardLayout;
