import { Link } from "react-router-dom";

function DashboardLayout({
  user,
  roleLabel,
  eyebrow,
  title,
  description,
  navItems,
  activeItem,
  onNavigate,
  stats,
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
    <div className="dashboard-layout">
      <aside className="dashboard-sidebar">
        <Link className="dashboard-brand" to="/">
          <span className="dashboard-brand-mark">E</span>
          <span>Eventora<small>EVENT MANAGEMENT</small></span>
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
              <span className="dashboard-nav-marker" aria-hidden="true" />
              {item.label}
              {item.count != null && <span className="dashboard-nav-count">{item.count}</span>}
            </button>
          ))}
        </nav>
        <div className="dashboard-account">
          <span className="dashboard-avatar">{initials}</span>
          <span className="dashboard-account-copy">
            <strong>{user.full_name}</strong>
            <small>{roleLabel}</small>
          </span>
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
        <div className="dashboard-workspace">{children}</div>
      </main>
    </div>
  );
}

export default DashboardLayout;
