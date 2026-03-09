import { NavLink } from "react-router-dom";
import { cn } from "../../utils/cn";

const navItems = [
  { to: "/", label: "表單填寫", icon: "📝" },
  { to: "/history", label: "填寫歷史", icon: "📋" },
  { to: "/profile", label: "個人資料", icon: "👤" },
  { to: "/knowledge", label: "知識庫", icon: "📚" },
];

export default function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col">
      <div className="px-5 py-5 border-b border-gray-200">
        <h1 className="text-lg font-bold text-gray-800">SmartFill</h1>
        <p className="text-xs text-gray-500">智能學術表單填寫</p>
      </div>
      <nav className="flex-1 py-3">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-5 py-2.5 text-sm transition-colors",
                isActive
                  ? "bg-blue-50 text-blue-700 border-l-3 border-blue-600 font-medium"
                  : "text-gray-600 hover:bg-gray-100 border-l-3 border-transparent",
              )
            }
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="px-5 py-3 border-t border-gray-200 text-xs text-gray-400">
        v0.1.0
      </div>
    </aside>
  );
}
