import { NavLink, useNavigate } from "react-router-dom";
import { cn } from "../../utils/cn";
import { useAuth } from "../../contexts/AuthContext";

const navItems = [
  { to: "/", label: "表單填寫", icon: "📝" },
  { to: "/chat", label: "知識問答", icon: "💬" },
  { to: "/email", label: "郵件草稿", icon: "✉️" },
  { to: "/report", label: "報告生成", icon: "📊" },
  { to: "/history", label: "填寫歷史", icon: "📋" },
  { to: "/profile", label: "個人資料", icon: "👤" },
  { to: "/entities", label: "實體管理", icon: "🏷️" },
  { to: "/graph", label: "知識圖譜", icon: "🕸️" },
  { to: "/knowledge", label: "知識庫", icon: "📚" },
  { to: "/compliance", label: "合規檢查", icon: "✅" },
  { to: "/versions", label: "版本追蹤", icon: "📄" },
  { to: "/reminders", label: "智能提醒", icon: "🔔" },
  { to: "/indexing", label: "自動索引", icon: "🔍" },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <aside className="w-56 shrink-0 border-r border-gray-200 bg-gray-50 flex flex-col">
      <div className="px-5 py-5 border-b border-gray-200">
        <h1 className="text-lg font-bold text-gray-800">SmartFill</h1>
        <p className="text-xs text-gray-500">智能學術表單填寫</p>
      </div>
      <nav className="flex-1 py-3 overflow-y-auto">
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

      {/* User info + logout */}
      <div className="px-4 py-3 border-t border-gray-200">
        {user && (
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-700 truncate">
                {user.name_zh || user.name_en || user.email}
              </p>
              <p className="text-xs text-gray-400 truncate">{user.email}</p>
            </div>
            <button
              onClick={handleLogout}
              className="ml-2 shrink-0 text-xs text-gray-400 hover:text-red-500 transition-colors"
              title="登出"
            >
              登出
            </button>
          </div>
        )}
        <p className="text-xs text-gray-300 mt-2">v0.1.0</p>
      </div>
    </aside>
  );
}
