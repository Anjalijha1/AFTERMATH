export function CyberRobot({ className = "w-64 h-64" }) {
  return (
    <div className={`relative flex items-center justify-center select-none ${className}`}>
      {/* Background ambient glow behind robot */}
      <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-emerald-200/50 via-teal-200/30 to-sky-200/40 blur-2xl transform scale-110 -z-10" />
      
      <svg
        viewBox="0 0 320 340"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full drop-shadow-[0_15px_25px_rgba(15,23,42,0.12)]"
      >
        <defs>
          {/* Ceramic white gradients */}
          <linearGradient id="ceramicHead" x1="60" y1="40" x2="260" y2="220" gradientUnits="userSpaceOnUse">
            <stop stopColor="#FFFFFF" />
            <stop offset="0.6" stopColor="#F1F5F9" />
            <stop offset="1" stopColor="#E2E8F0" />
          </linearGradient>

          <linearGradient id="ceramicChest" x1="80" y1="180" x2="240" y2="340" gradientUnits="userSpaceOnUse">
            <stop stopColor="#FFFFFF" />
            <stop offset="0.7" stopColor="#F8FAFC" />
            <stop offset="1" stopColor="#CBD5E1" />
          </linearGradient>

          {/* Dark onyx joints */}
          <linearGradient id="onyxDark" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="#2D3748" />
            <stop offset="0.5" stopColor="#1A202C" />
            <stop offset="1" stopColor="#0B0F17" />
          </linearGradient>

          {/* Glowing cyan visor eye gradient */}
          <linearGradient id="cyanGlow" x1="0" y1="0" x2="0" y2="1">
            <stop stopColor="#67E8F9" />
            <stop offset="1" stopColor="#06B6D4" />
          </linearGradient>

          {/* Visor face gradient */}
          <linearGradient id="visorScreen" x1="100" y1="90" x2="220" y2="160" gradientUnits="userSpaceOnUse">
            <stop stopColor="#0F172A" />
            <stop offset="1" stopColor="#020617" />
          </linearGradient>

          {/* Shadow filters */}
          <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Antenna / Earpieces */}
        <path d="M72 110C60 110 52 120 52 134C52 148 60 158 72 158" stroke="url(#onyxDark)" strokeWidth="14" strokeLinecap="round" />
        <path d="M248 110C260 110 268 120 268 134C268 148 260 158 248 158" stroke="url(#onyxDark)" strokeWidth="14" strokeLinecap="round" />
        <circle cx="56" cy="134" r="8" fill="#64748B" />
        <circle cx="264" cy="134" r="8" fill="#64748B" />

        {/* Neck joint */}
        <rect x="136" y="180" width="48" height="24" rx="8" fill="url(#onyxDark)" />
        <line x1="140" y1="188" x2="180" y2="188" stroke="#475569" strokeWidth="2" strokeDasharray="4 3" />
        <line x1="140" y1="194" x2="180" y2="194" stroke="#475569" strokeWidth="2" strokeDasharray="4 3" />

        {/* Torso & Shoulders */}
        <path d="M60 270C60 220 95 200 160 200C225 200 260 220 260 270L270 340H50L60 270Z" fill="url(#ceramicChest)" />
        
        {/* Shoulder Pods */}
        <circle cx="70" cy="245" r="24" fill="url(#onyxDark)" />
        <circle cx="250" cy="245" r="24" fill="url(#onyxDark)" />
        <circle cx="70" cy="245" r="14" fill="#334155" />
        <circle cx="250" cy="245" r="14" fill="#334155" />

        {/* Chest Panel Details */}
        <path d="M110 225H210C215 225 218 229 216 234L206 280C204 284 200 287 196 287H124C120 287 116 284 114 280L104 234C102 229 105 225 110 225Z" fill="#F8FAFC" stroke="#E2E8F0" strokeWidth="2" />
        
        {/* Chest Core Indicator */}
        <rect x="146" y="240" width="28" height="14" rx="7" fill="#E2E8F0" stroke="#CBD5E1" />
        <circle cx="160" cy="247" r="4" fill="#38BDF8" filter="url(#softGlow)" />

        {/* Chest Ventilation Grille */}
        <g stroke="#94A3B8" strokeWidth="2" strokeLinecap="round">
          <line x1="135" y1="268" x2="185" y2="268" strokeDasharray="3 3" />
          <line x1="138" y1="274" x2="182" y2="274" strokeDasharray="3 3" />
          <line x1="142" y1="280" x2="178" y2="280" strokeDasharray="3 3" />
        </g>

        {/* Head Base & Curved Ceramic Dome */}
        <rect x="76" y="44" width="168" height="144" rx="66" fill="url(#ceramicHead)" />
        <path d="M84 62C106 48 132 44 160 44C188 44 214 48 236 62" stroke="#FFFFFF" strokeWidth="6" strokeLinecap="round" opacity="0.9" />

        {/* Dark Visor Face Screen */}
        <rect x="94" y="80" width="132" height="88" rx="42" fill="url(#visorScreen)" />
        <rect x="95" y="81" width="130" height="86" rx="41" stroke="#334155" strokeWidth="1.5" />

        {/* Friendly Glowing Cyan Eyes */}
        <g filter="url(#softGlow)">
          {/* Left Eye: pill shape tilted gently */}
          <ellipse cx="132" cy="118" rx="14" ry="18" fill="url(#cyanGlow)" />
          {/* Right Eye: pill shape tilted gently */}
          <ellipse cx="188" cy="118" rx="14" ry="18" fill="url(#cyanGlow)" />
          {/* Eye specular highlights */}
          <ellipse cx="135" cy="114" rx="4" ry="7" fill="#FFFFFF" opacity="0.8" />
          <ellipse cx="191" cy="114" rx="4" ry="7" fill="#FFFFFF" opacity="0.8" />
        </g>

        {/* Visor subtle cyber smile arc */}
        <path d="M150 144Q160 148 170 144" stroke="#38BDF8" strokeWidth="2.5" strokeLinecap="round" opacity="0.75" />

        {/* Subtle decorative tech stamp on head */}
        <text x="210" y="70" fill="#94A3B8" fontSize="8" fontFamily="monospace" fontWeight="700">OS-30</text>
      </svg>
    </div>
  );
}

export function CyberRibbonCard({ title, subtitle, className = "" }) {
  return (
    <div className={`relative overflow-hidden rounded-3xl border border-slate-200/90 bg-gradient-to-br from-slate-50 via-white to-sky-50 p-6 md:p-7 shadow-card ${className}`}>
      {/* Abstract glossy wave SVG */}
      <div className="absolute right-0 top-0 bottom-0 w-1/2 opacity-30 pointer-events-none">
        <svg viewBox="0 0 200 300" fill="none" className="w-full h-full">
          <path d="M50 0C120 70 30 180 150 300H200V0H50Z" fill="url(#waveGrad)" />
          <defs>
            <linearGradient id="waveGrad" x1="50" y1="0" x2="200" y2="300" gradientUnits="userSpaceOnUse">
              <stop stopColor="#A7F3D0" />
              <stop offset="0.5" stopColor="#38BDF8" />
              <stop offset="1" stopColor="#93C5FD" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <div className="relative z-10">
        {title && <h4 className="text-base font-bold text-slate-900">{title}</h4>}
        {subtitle && <p className="mt-2 text-sm text-slate-600 leading-relaxed max-w-sm">{subtitle}</p>}
      </div>
    </div>
  );
}

export function LockBadge({ className = "w-8 h-8" }) {
  return (
    <div className={`inline-flex items-center justify-center rounded-xl bg-black text-white shadow-md ${className}`}>
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
    </div>
  );
}

export function TechGlyph() {
  return (
    <span className="inline-flex items-center gap-1.5 align-middle mx-1.5 opacity-80">
      <span className="flex h-5 w-5 items-center justify-center rounded-full border border-slate-300 text-[11px] text-slate-600">
        ❄
      </span>
      <span className="flex h-5 w-5 items-center justify-center rounded-full border border-slate-300 text-[11px] text-slate-600">
        ➔
      </span>
    </span>
  );
}
