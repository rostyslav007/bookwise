import { Link, useLocation } from "react-router-dom";
import { BookOpenIcon, SearchIcon } from "lucide-react";

const NAV_LINKS = [
  { to: "/search", label: "Search", icon: SearchIcon },
] as const;

export function Header() {
  const location = useLocation();

  return (
    <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-14 items-center justify-between px-4">
        <Link to="/" className="flex items-center gap-2 font-semibold text-lg hover:opacity-80 transition-opacity">
          <BookOpenIcon className="h-5 w-5 text-primary" />
          <span>Bookwise</span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV_LINKS.map(({ to, label, icon: Icon }) => {
            const isActive = location.pathname === to;
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
