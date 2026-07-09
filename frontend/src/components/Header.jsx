export default function Header() {
  return (
    <header className="h-16 shrink-0 flex items-center gap-3 px-6 bg-surface border-b border-border">
      <img src="/logo.webp" alt="Logo" className="w-9 h-9 object-contain" />
      <div className="flex flex-col leading-none">
        <span className="text-[15px] font-extrabold tracking-tight text-ink">DocMind</span>
        <span className="text-[11px] text-muted font-medium">Ask your documents anything</span>
      </div>
    </header>
  );
}
