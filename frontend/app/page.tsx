"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import {
  Video, ArrowRight, Menu, X, Mic2, Brain, ListChecks,
  Upload, Zap, Mail,
} from "lucide-react";

// ── Scroll reveal ─────────────────────────────────────────────────────────────
function useInView(ref: React.RefObject<HTMLElement | null>, threshold = 0.12) {
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setInView(true); }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, [ref, threshold]);
  return inView;
}

// ── SVG Avatar ────────────────────────────────────────────────────────────────
const AVATAR_GRADIENTS: [string, string][] = [
  ["#6366f1", "#7c3aed"],
  ["#8b5cf6", "#a855f7"],
  ["#06b6d4", "#6366f1"],
  ["#10b981", "#059669"],
  ["#f59e0b", "#d97706"],
  ["#ec4899", "#db2777"],
];

function Avatar({ name, colorIdx = 0, size = 36 }: { name: string; colorIdx?: number; size?: number }) {
  const [from, to] = AVATAR_GRADIENTS[colorIdx % AVATAR_GRADIENTS.length];
  const initials = name.split(" ").slice(0, 2).map((w) => w[0]).join("").toUpperCase();
  const gid = `ag-${name.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={from} />
          <stop offset="100%" stopColor={to} />
        </linearGradient>
      </defs>
      <circle cx="18" cy="18" r="18" fill={`url(#${gid})`} />
      <text x="18" y="23" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold" fontFamily="system-ui,sans-serif">{initials}</text>
    </svg>
  );
}

// ── Waveform ──────────────────────────────────────────────────────────────────
const WAVE_HEIGHTS = [8, 18, 28, 20, 32, 24, 14, 28, 36, 22, 16, 30, 26, 18, 34, 20, 28, 12, 24, 32, 18, 26, 22, 16];
const WAVE_COLORS  = ["bg-indigo-400", "bg-violet-400", "bg-indigo-300", "bg-purple-400"];

// ── Marquee items ─────────────────────────────────────────────────────────────
const MARQUEE = [
  { icon: "🎙️", text: "Transkripsi Whisper" },
  { icon: "📝", text: "Ringkasan AI" },
  { icon: "✅", text: "Action Items" },
  { icon: "📬", text: "Email Otomatis" },
  { icon: "🔒", text: "100% Lokal" },
  { icon: "👥", text: "Diarisasi Pembicara" },
  { icon: "📄", text: "Notulen PDF" },
  { icon: "⚡", text: "Proses Cepat" },
];

// ── Feature SVG illustrations ─────────────────────────────────────────────────
const TranscriptSVG = () => (
  <svg viewBox="0 0 340 220" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
    <rect width="340" height="220" rx="16" fill="#f8fafc" />
    {[12,20,35,28,45,55,40,30,50,60,42,25,38,52,44,30,20,45,60,48,35,25,40,50,38].map((h, i) => (
      <rect key={i} x={20 + i * 12} y={80 - h / 2} width="7" height={h} rx="3"
        fill={i % 3 === 0 ? "#818cf8" : i % 3 === 1 ? "#a78bfa" : "#c4b5fd"} opacity="0.85" />
    ))}
    <rect x="20" y="115" width="55" height="14" rx="4" fill="#ede9fe" />
    <text x="47" y="126" textAnchor="middle" fontSize="8" fill="#7c3aed" fontWeight="bold">Audi</text>
    <rect x="100" y="115" width="60" height="14" rx="4" fill="#e0f2fe" />
    <text x="130" y="126" textAnchor="middle" fontSize="8" fill="#0369a1" fontWeight="bold">Helena</text>
    <rect x="185" y="115" width="55" height="14" rx="4" fill="#f0fdf4" />
    <text x="212" y="126" textAnchor="middle" fontSize="8" fill="#15803d" fontWeight="bold">Azmi</text>
    <rect x="20" y="142" width="240" height="7" rx="3" fill="#e2e8f0" />
    <rect x="20" y="155" width="180" height="7" rx="3" fill="#e2e8f0" />
    <rect x="20" y="168" width="210" height="7" rx="3" fill="#e2e8f0" />
    <rect x="20" y="181" width="155" height="7" rx="3" fill="#e2e8f0" />
    <rect x="20" y="168" width="80" height="7" rx="3" fill="#c7d2fe" />
    <circle cx="300" cy="55" r="30" fill="#ede9fe" />
    <rect x="291" y="38" width="18" height="26" rx="9" fill="#6366f1" />
    <path d="M283 58c0 9.4 7.6 17 17 17s17-7.6 17-17" stroke="#6366f1" strokeWidth="2.5" strokeLinecap="round" fill="none" />
    <line x1="300" y1="75" x2="300" y2="82" stroke="#6366f1" strokeWidth="2.5" strokeLinecap="round" />
  </svg>
);

const BrainSVG = () => (
  <svg viewBox="0 0 340 220" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
    <rect width="340" height="220" rx="16" fill="#f8fafc" />
    <circle cx="170" cy="100" r="28" fill="#ede9fe" stroke="#a78bfa" strokeWidth="2" />
    <text x="170" y="105" textAnchor="middle" fontSize="10" fill="#7c3aed" fontWeight="bold">AI</text>
    {[
      { cx: 75,  cy: 55,  label: "Transkrip",  bg: "#dbeafe", stroke: "#93c5fd" },
      { cx: 265, cy: 55,  label: "Keputusan",  bg: "#d1fae5", stroke: "#6ee7b7" },
      { cx: 55,  cy: 160, label: "Topik",      bg: "#fef3c7", stroke: "#fcd34d" },
      { cx: 285, cy: 160, label: "Action",     bg: "#fce7f3", stroke: "#f9a8d4" },
    ].map((n, i) => (
      <g key={i}>
        <line x1="170" y1="100" x2={n.cx} y2={n.cy} stroke="#c4b5fd" strokeWidth="1.5" strokeDasharray="4 3" opacity="0.7" />
        <circle cx={n.cx} cy={n.cy} r="23" fill={n.bg} stroke={n.stroke} strokeWidth="1.5" />
        <text x={n.cx} y={n.cy + 4} textAnchor="middle" fontSize="7" fill="#475569" fontWeight="600">{n.label}</text>
      </g>
    ))}
    <rect x="95" y="170" width="150" height="36" rx="8" fill="white" stroke="#e2e8f0" strokeWidth="1" />
    <rect x="105" y="180" width="90" height="5" rx="2" fill="#e2e8f0" />
    <rect x="105" y="190" width="70" height="5" rx="2" fill="#e2e8f0" />
    <rect x="105" y="200" width="80" height="5" rx="2" fill="#c7d2fe" />
  </svg>
);

const ChecklistSVG = () => (
  <svg viewBox="0 0 340 220" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
    <rect width="340" height="220" rx="16" fill="#f8fafc" />
    {[
      { task: "Deploy staging environment", assignee: "HN", done: true,  due: "Besok",      c: "#6366f1" },
      { task: "Review sprint backlog",       assignee: "AU", done: true,  due: "Lusa",       c: "#8b5cf6" },
      { task: "Fine-tuning model v2",        assignee: "AZ", done: false, due: "Jum'at",     c: "#a855f7" },
      { task: "Write API documentation",     assignee: "AU", done: false, due: "Minggu ini", c: "#7c3aed" },
    ].map((item, i) => (
      <g key={i}>
        <rect x="20" y={25 + i * 44} width="300" height="36" rx="8"
          fill={item.done ? "#f0fdf4" : "white"} stroke={item.done ? "#bbf7d0" : "#e2e8f0"} strokeWidth="1" />
        <circle cx="44" cy={43 + i * 44} r="9" fill={item.done ? "#22c55e" : "white"}
          stroke={item.done ? "#22c55e" : "#cbd5e1"} strokeWidth="1.5" />
        {item.done && <path d={`M38 ${43 + i * 44}l4.5 4.5 7-7`} stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />}
        <text x="62" y={42 + i * 44} fontSize="9" fill={item.done ? "#86efac" : "#334155"} fontWeight="500"
          textDecoration={item.done ? "line-through" : "none"}>{item.task}</text>
        <text x="62" y={53 + i * 44} fontSize="8" fill="#94a3b8">{item.due}</text>
        <circle cx="292" cy={43 + i * 44} r="11" fill={item.c} opacity="0.9" />
        <text x="292" y={47 + i * 44} textAnchor="middle" fontSize="7" fill="white" fontWeight="bold">{item.assignee}</text>
      </g>
    ))}
    <rect x="20" y="203" width="300" height="6" rx="3" fill="#e2e8f0" />
    <rect x="20" y="203" width="150" height="6" rx="3" fill="#22c55e" />
  </svg>
);

// ─────────────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  const [activeFaq, setActiveFaq] = useState<number | null>(null);
  const [menuOpen, setMenuOpen]   = useState(false);

  const featuresRef = useRef<HTMLElement>(null);
  const stepsRef    = useRef<HTMLElement>(null);
  const testiRef    = useRef<HTMLElement>(null);
  const metricsRef  = useRef<HTMLElement>(null);

  const featuresVisible = useInView(featuresRef);
  const stepsVisible    = useInView(stepsRef);
  const testiVisible    = useInView(testiRef);
  const metricsVisible  = useInView(metricsRef);

  const faqs = [
    {
      question: "Format file apa saja yang didukung oleh MeetMate?",
      answer: "MeetMate mendukung format audio dan video populer seperti MP3, WAV, M4A, dan MP4 dengan ukuran maksimal 200MB per unggahan.",
    },
    {
      question: "Berapa lama waktu yang dibutuhkan AI untuk memproses rapat?",
      answer: "Rata-rata 15–20% dari durasi rekaman. Rapat 1 jam akan selesai diproses dalam 8–12 menit.",
    },
    {
      question: "Apakah data rekaman rapat saya aman?",
      answer: "Sangat aman. MeetMate sepenuhnya self-hosted — data tidak pernah keluar dari server Anda. Tidak ada cloud pihak ketiga yang terlibat.",
    },
    {
      question: "Apakah MeetMate bisa mendeteksi bahasa campuran (Indonesia + Inggris)?",
      answer: "Ya! Model Whisper yang kami gunakan sudah dioptimalkan untuk percakapan profesional bahasa Indonesia termasuk istilah teknis bahasa Inggris.",
    },
  ];

  const testimonials = [
    {
      name: "Budi Santoso", role: "Lead Engineer", company: "Tokopedia",
      colorIdx: 0,
      quote: "Kita punya culture banyak rapat. Sebelumnya notulis manual makan waktu hampir 2 jam per minggu. Sekarang semua otomatis — upload rekaman, 10 menit kemudian notulen sudah di inbox semua orang.",
    },
    {
      name: "Anisa Rahmawati", role: "Product Manager", company: "Gojek",
      colorIdx: 1,
      quote: "Akurasi transcription-nya di luar dugaan. Istilah teknis kayak 'sprint velocity' dan 'backlog grooming' bisa ketangkap dengan benar.",
    },
    {
      name: "Dimas Prayogo", role: "CTO", company: "Fintech Startup",
      colorIdx: 2,
      quote: "Yang paling bikin saya terkesan adalah fitur Action Items. AI bisa detect siapa yang ditugaskan apa, bahkan kalau penyebutan namanya informal dalam percakapan. Tim jadi jauh lebih accountable.",
    },
    {
      name: "Rina Kusuma", role: "HR Manager", company: "Bank BCA",
      colorIdx: 3,
      quote: "Self-hosted itu dealbreaker buat kita dari sisi compliance. Senang banget ada solusi sekelas ini yang tidak kirim data ke cloud.",
    },
    {
      name: "Fajar Nugroho", role: "Project Manager", company: "Pertamina",
      colorIdx: 4,
      quote: "Sudah 3 bulan pakai MeetMate. Rapat kita rata-rata 45 menit, notulen keluar dalam 7 menit. Tim sekarang nggak ada yang nanya 'notulennya mana?'",
    },
    {
      name: "Siti Maryam", role: "Co-founder", company: "EdTech Startup",
      colorIdx: 5,
      quote: "Sebagai startup kecil, kita nggak punya budget buat tools mahal. MeetMate self-hosted ini perfect — bayar server sendiri, data sendiri, kontrol penuh.",
    },
  ];

  const features = [
    {
      dir: "normal" as const,
      icon: <Mic2 size={16} className="text-indigo-600" />,
      tag: "Transkripsi",
      title: "Suara jadi teks. Otomatis.",
      desc: "Whisper large-v3 mengonversi rekaman rapat jadi transkrip lengkap dengan akurasi tinggi. Bahasa Indonesia, istilah teknis Inggris, bahkan speaker diarization — semua ditangani.",
      points: ["Akurasi >95% untuk percakapan profesional", "Deteksi siapa yang berbicara kapan", "Bahasa campuran ID/EN didukung"],
      visual: <TranscriptSVG />,
    },
    {
      dir: "reverse" as const,
      icon: <Brain size={16} className="text-violet-600" />,
      tag: "Ringkasan AI",
      title: "Poin penting tanpa baca semua.",
      desc: "LLM lokal menganalisis transkrip dan menghasilkan ringkasan eksekutif, daftar keputusan, dan topik yang dibahas — dalam hitungan menit setelah rapat selesai.",
      points: ["Ringkasan eksekutif 1 paragraf", "Daftar keputusan terstruktur", "Topik utama otomatis terdeteksi"],
      visual: <BrainSVG />,
    },
    {
      dir: "normal" as const,
      icon: <ListChecks size={16} className="text-purple-600" />,
      tag: "Action Items",
      title: "Tugas tidak lagi tercecer di chat.",
      desc: "AI mendeteksi setiap tugas yang disebutkan dalam rapat, lengkap dengan PIC dan tenggat waktu. Otomatis terorganisir, bisa dikelola langsung dari dashboard.",
      points: ["Deteksi PIC dari konteks percakapan", "Tenggat waktu otomatis terdeteksi", "Pantau status per peserta"],
      visual: <ChecklistSVG />,
    },
  ];

  const navLinks: [string, string][] = [
    ["#features", "Fitur"],
    ["#cara-kerja", "Cara Kerja"],
    ["#testimoni", "Testimoni"],
    ["#faq", "FAQ"],
  ];

  return (
    <div className="min-h-screen bg-white text-slate-900 font-sans selection:bg-indigo-100 overflow-x-hidden">

      {/* ── NAVBAR ── */}
      <header className="sticky top-0 z-50 border-b border-slate-100 bg-white/95 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <Video size={15} className="text-white" />
            </div>
            <span className="font-bold text-lg tracking-wide text-slate-900">MeetMate</span>
          </Link>

          <nav className="hidden md:flex items-center gap-8 text-sm text-slate-500">
            {navLinks.map(([href, label]) => (
              <a key={href} href={href} className="relative group hover:text-slate-900 transition py-1">
                {label}
                <span className="absolute bottom-0 left-0 h-0.5 w-0 bg-indigo-500 rounded-full transition-all duration-300 group-hover:w-full" />
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <Link href="/login" className="hidden sm:block text-sm font-medium text-slate-600 hover:text-slate-900 transition px-3 py-2">
              Masuk
            </Link>
            <Link href="/register" className="text-sm font-semibold bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 text-white px-5 py-2 rounded-lg transition shadow-md shadow-indigo-500/20">
              Mulai Gratis
            </Link>
            <button onClick={() => setMenuOpen(!menuOpen)} className="md:hidden p-2 text-slate-500 hover:text-slate-900 transition">
              {menuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {menuOpen && (
          <div className="md:hidden border-t border-slate-100 bg-white animate-fade-in">
            <div className="px-6 py-4 space-y-1">
              {navLinks.map(([href, label]) => (
                <a key={href} href={href} onClick={() => setMenuOpen(false)}
                  className="block text-sm text-slate-600 hover:text-slate-900 py-2.5 border-b border-slate-50 last:border-0 transition">
                  {label}
                </a>
              ))}
              <Link href="/login" onClick={() => setMenuOpen(false)} className="block text-sm text-slate-500 py-2.5">
                Masuk
              </Link>
            </div>
          </div>
        )}
      </header>

      {/* ── HERO ── */}
      <section className="relative overflow-hidden min-h-[92vh] flex items-center">
        <div className="absolute inset-0 pointer-events-none">
          <div className="animate-float absolute top-16 left-[5%] w-80 h-80 rounded-full bg-indigo-400/12 blur-3xl" />
          <div className="animate-float-slow absolute top-28 right-[5%] w-96 h-96 rounded-full bg-violet-400/10 blur-3xl" />
          <div className="animate-float-delay absolute bottom-16 left-[40%] w-72 h-72 rounded-full bg-purple-300/8 blur-3xl" />
        </div>
        <div className="absolute inset-0" style={{
          backgroundImage: "linear-gradient(rgba(99,102,241,0.045) 1px,transparent 1px),linear-gradient(90deg,rgba(99,102,241,0.045) 1px,transparent 1px)",
          backgroundSize: "60px 60px",
        }} />

        <div className="relative max-w-7xl mx-auto px-6 py-20 w-full">
          <div className="grid lg:grid-cols-2 gap-14 items-center">

            {/* Left */}
            <div className="animate-fade-in">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-semibold mb-8">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                </span>
                AI Lokal · Offline-First · Zero Cloud
              </div>

              <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight leading-[1.1] mb-6">
                <span className="text-slate-900">Notulen Rapat</span>
                <br />
                <span className="animate-gradient-x bg-gradient-to-r from-indigo-600 via-violet-500 to-purple-600 bg-clip-text text-transparent inline-block">
                  Tulis Sendiri.
                </span>
                <br />
                <span className="text-slate-700 text-4xl md:text-5xl font-bold">Biarkan AI yang Kerja.</span>
              </h1>

              <p className="text-slate-500 text-lg leading-relaxed mb-8 max-w-md">
                Tak ada lagi WA <em className="not-italic font-semibold text-slate-700">"notulennya mana?"</em>. Upload rekaman — dalam 10 menit transkrip, ringkasan, dan action items sudah di inbox semua peserta.
              </p>

              <div className="flex flex-col sm:flex-row gap-3 mb-10">
                <Link href="/register"
                  className="inline-flex items-center justify-center gap-2 bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 text-white font-semibold px-7 py-3.5 rounded-xl transition shadow-xl shadow-indigo-500/25 text-sm">
                  Coba Sekarang <ArrowRight size={15} />
                </Link>
                <a href="#cara-kerja"
                  className="inline-flex items-center justify-center gap-2 bg-white hover:bg-slate-50 border border-slate-200 hover:border-slate-300 text-slate-700 font-semibold px-7 py-3.5 rounded-xl transition text-sm">
                  Lihat Cara Kerja
                </a>
              </div>

              {/* Social proof */}
              <div className="flex items-center gap-3">
                <div className="flex -space-x-2">
                  {["Budi S", "Anisa R", "Dimas P", "Rina K", "Fajar N"].map((name, i) => (
                    <div key={name} className="ring-2 ring-white rounded-full" style={{ zIndex: 5 - i }}>
                      <Avatar name={name} colorIdx={i} size={32} />
                    </div>
                  ))}
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-800">Dipercaya 200+ tim di Indonesia</p>
                  <div className="flex items-center gap-0.5 mt-0.5">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <svg key={s} width="10" height="10" viewBox="0 0 10 10" fill="#f59e0b">
                        <path d="M5 0.5l1.18 2.39 2.64.38-1.91 1.86.45 2.63L5 6.64l-2.36 1.24.45-2.63L1.18 3.27l2.64-.38z" />
                      </svg>
                    ))}
                    <span className="text-[11px] text-slate-400 ml-1">4.9/5</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Right — 3D panel */}
            <div className="hidden lg:block">
              <div className="relative" style={{ perspective: "1200px" }}>
                <div className="absolute -inset-6 bg-gradient-to-br from-indigo-500/15 to-violet-500/15 rounded-3xl blur-2xl" />
                <div className="relative bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-2xl"
                  style={{ transform: "rotateY(-8deg) rotateX(3deg)", transformStyle: "preserve-3d" }}>

                  {/* Panel header */}
                  <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-b border-slate-100">
                    <div className="flex items-center gap-2">
                      <div className="h-5 w-5 rounded-md bg-gradient-to-br from-indigo-500 to-violet-600" />
                      <span className="text-xs font-bold text-slate-800">MeetMate</span>
                    </div>
                    <div className="flex gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-rose-400/60" />
                      <div className="w-2.5 h-2.5 rounded-full bg-amber-400/60" />
                      <div className="w-2.5 h-2.5 rounded-full bg-emerald-400/60" />
                    </div>
                  </div>

                  <div className="p-5 space-y-4 bg-white">
                    {/* Meeting info */}
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-[9px] text-slate-400 uppercase tracking-wider mb-0.5">Sedang diproses</p>
                        <p className="text-sm font-bold text-slate-900">Evaluasi Q2 2025</p>
                        <p className="text-[10px] text-slate-400 mt-0.5">14 peserta · 58 menit</p>
                      </div>
                      <div className="bg-amber-50 border border-amber-200 text-amber-600 text-[9px] font-bold px-2 py-1 rounded-full shrink-0">
                        AI Memproses...
                      </div>
                    </div>

                    {/* Waveform */}
                    <div className="bg-slate-900 rounded-xl p-4">
                      <p className="text-[9px] text-slate-500 mb-2 uppercase tracking-wider">Audio Rekaman</p>
                      <div className="flex items-end gap-[3px]" style={{ height: "40px" }}>
                        {WAVE_HEIGHTS.map((h, i) => (
                          <div key={i} className={`w-1 rounded-full ${WAVE_COLORS[i % WAVE_COLORS.length]} animate-waveform`}
                            style={{ animationDelay: `${(i * 0.07) % 1.2}s`, minHeight: "4px", height: `${h}px` }} />
                        ))}
                      </div>
                    </div>

                    {/* Transcript preview */}
                    <div className="space-y-1">
                      <p className="text-[9px] text-slate-400 uppercase tracking-wider">Transkrip</p>
                      {[
                        { speaker: "Audi",   line: "Oke, kita mulai review milestone Q2 dulu ya...", hl: true  },
                        { speaker: "Helena", line: "Dashboard sudah selesai, tinggal mobile view.",  hl: false },
                        { speaker: "Azmi",   line: "Model accuracy naik 3% setelah fine-tuning.",   hl: false },
                        { speaker: "Audi",   line: "Bagus. Action item: Helena deploy staging besok.", hl: true },
                      ].map((t, i) => (
                        <div key={i} className={`flex gap-2 p-1.5 rounded-lg ${t.hl ? "bg-indigo-50" : ""}`}>
                          <span className="text-[9px] font-bold text-indigo-500 w-10 shrink-0">{t.speaker}</span>
                          <span className="text-[9px] text-slate-500 leading-relaxed">{t.line}</span>
                        </div>
                      ))}
                    </div>

                    {/* Action items preview */}
                    <div className="border-t border-slate-100 pt-3">
                      <p className="text-[9px] text-slate-400 uppercase tracking-wider mb-2">Action Items (AI)</p>
                      <div className="space-y-1.5">
                        {[
                          { task: "Deploy staging environment", assignee: "HN", done: true  },
                          { task: "Fine-tuning model v2",       assignee: "AZ", done: false },
                          { task: "Review sprint backlog",      assignee: "AU", done: false },
                        ].map((item, i) => (
                          <div key={i} className="flex items-center gap-2">
                            <div className={`h-3.5 w-3.5 rounded-full border-2 shrink-0 flex items-center justify-center ${item.done ? "bg-emerald-500 border-emerald-500" : "border-slate-300"}`}>
                              {item.done && (
                                <svg width="7" height="5" viewBox="0 0 7 5" fill="none">
                                  <path d="M1 2.5L2.5 4L6 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
                                </svg>
                              )}
                            </div>
                            <span className={`text-[9px] flex-1 ${item.done ? "line-through text-slate-400" : "text-slate-700"}`}>{item.task}</span>
                            <Avatar name={item.assignee} colorIdx={i} size={14} />
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="animate-float absolute -top-3 -right-5 bg-emerald-500 text-white text-[10px] font-bold px-3 py-1.5 rounded-full shadow-lg shadow-emerald-500/30 whitespace-nowrap">
                  ✓ Notulen Terkirim
                </div>
                <div className="animate-float-delay absolute -bottom-3 -left-5 bg-white border border-slate-200 text-slate-700 text-[10px] font-medium px-3 py-1.5 rounded-full shadow-xl whitespace-nowrap">
                  🤖 AI meringkas...
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ── MARQUEE ── */}
      <div className="bg-slate-900 border-y border-slate-800 py-4 overflow-hidden">
        <div className="flex animate-marquee whitespace-nowrap">
          {[...MARQUEE, ...MARQUEE].map((item, i) => (
            <span key={i} className="inline-flex items-center gap-2 mx-8 text-sm">
              <span>{item.icon}</span>
              <span className="font-semibold text-white">{item.text}</span>
              <span className="text-slate-700 mx-1">·</span>
            </span>
          ))}
        </div>
      </div>

      {/* ── FEATURES ── */}
      <section id="features" ref={featuresRef} className="py-28 border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center max-w-xl mx-auto mb-20">
            <p className="text-indigo-600 text-xs font-bold uppercase tracking-widest mb-3">Fitur Unggulan</p>
            <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 mb-4 leading-tight">
              Semua yang kamu butuhkan,{" "}
              <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">dalam satu tempat</span>
            </h2>
            <p className="text-slate-400 text-sm leading-relaxed">Fokus diskusi. Dokumentasi bukan urusan kamu lagi.</p>
          </div>

          <div className="space-y-24">
            {features.map((f, idx) => (
              <div key={f.tag}
                className={`flex flex-col ${f.dir === "reverse" ? "md:flex-row-reverse" : "md:flex-row"} gap-12 md:gap-16 items-center ${featuresVisible ? "animate-slide-up" : "opacity-0"}`}
                style={{ animationDelay: `${idx * 0.15}s` }}>

                {/* Text */}
                <div className="flex-1 min-w-0">
                  <div className="inline-flex items-center gap-2 bg-indigo-50 border border-indigo-100 px-3 py-1 rounded-full text-indigo-700 text-xs font-bold mb-5 uppercase tracking-wide">
                    {f.icon}
                    {f.tag}
                  </div>
                  <h3 className="text-2xl md:text-3xl font-extrabold text-slate-900 mb-4 leading-tight">{f.title}</h3>
                  <p className="text-slate-500 leading-relaxed mb-6 text-sm">{f.desc}</p>
                  <ul className="space-y-2.5">
                    {f.points.map((p) => (
                      <li key={p} className="flex items-center gap-2.5 text-sm text-slate-600">
                        <span className="h-5 w-5 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center shrink-0">
                          <svg width="8" height="6" viewBox="0 0 8 6" fill="none">
                            <path d="M1 3l2 2 4-4" stroke="#22c55e" strokeWidth="1.5" strokeLinecap="round" />
                          </svg>
                        </span>
                        {p}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Visual */}
                <div className="flex-1 w-full max-w-sm md:max-w-none">
                  <div className="aspect-[340/220] bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-lg hover:shadow-xl hover:border-indigo-200 transition-all duration-300">
                    {f.visual}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CARA KERJA — Vertical Timeline ── */}
      <section id="cara-kerja" ref={stepsRef} className="py-28 bg-slate-50 border-b border-slate-100">
        <div className="max-w-3xl mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-indigo-600 text-xs font-bold uppercase tracking-widest mb-3">Cara Kerja</p>
            <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 mb-4 leading-tight">
              Dari rekaman ke notulen,{" "}
              <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">tiga langkah.</span>
            </h2>
            <p className="text-slate-400 text-sm">Upload sekali. Semua beres otomatis.</p>
          </div>

          <div className="relative pl-12">
            {/* Vertical line */}
            <div className="absolute left-4 top-3 bottom-3 w-px bg-gradient-to-b from-indigo-300 via-violet-300 to-purple-300" />

            <div className="space-y-10">
              {[
                {
                  step: "01", icon: <Upload size={18} className="text-indigo-600" />,
                  title: "Upload Rekaman",
                  desc: "Drag & drop file audio atau video hasil rapat. MP3, WAV, M4A, MP4 semua didukung. Maksimal 200MB.",
                  badge: "Format: mp3, wav, m4a, mp4",
                },
                {
                  step: "02", icon: <Zap size={18} className="text-violet-600" />,
                  title: "AI Memproses",
                  desc: "Whisper large-v3 transkripsi audio. Diarisasi pembicara. LLM lokal ekstrak ringkasan, keputusan, dan action items. Berjalan di server kamu.",
                  badge: "~10–15% dari durasi rekaman",
                },
                {
                  step: "03", icon: <Mail size={18} className="text-purple-600" />,
                  title: "Notulen Dikirim",
                  desc: "Transkrip, ringkasan, dan action items muncul di dashboard. Email otomatis ke semua peserta. Tidak perlu intervensi manual.",
                  badge: "Email ke seluruh peserta",
                },
              ].map((s, i) => (
                <div key={s.step}
                  className={`relative ${stepsVisible ? "animate-slide-up" : "opacity-0"}`}
                  style={{ animationDelay: `${i * 0.18}s` }}>

                  {/* Dot */}
                  <div className="absolute -left-12 top-4 flex items-center justify-center">
                    <div className="animate-pulse-ring absolute h-9 w-9 rounded-full bg-indigo-200 opacity-50" />
                    <div className="relative h-7 w-7 rounded-full bg-white border-2 border-indigo-400 flex items-center justify-center shadow-md z-10">
                      {s.icon}
                    </div>
                  </div>

                  <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm hover:border-indigo-200 hover:shadow-md transition-all">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-xs font-black text-slate-300 tracking-widest">{s.step}</span>
                      <h4 className="text-base font-bold text-slate-900">{s.title}</h4>
                    </div>
                    <p className="text-slate-500 text-sm leading-relaxed mb-3">{s.desc}</p>
                    <span className="text-xs text-indigo-600 font-medium bg-indigo-50 border border-indigo-100 inline-block px-2.5 py-1 rounded-lg">{s.badge}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── METRICS BAR ── */}
      <section ref={metricsRef} className="bg-gradient-to-r from-indigo-600 to-violet-700 py-16">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-10 text-center text-white">
            {[
              { num: "10×",   label: "lebih cepat dari notulensi manual" },
              { num: "95%+",  label: "akurasi transkripsi bahasa Indonesia" },
              { num: "200+",  label: "tim aktif yang sudah menggunakan" },
              { num: "0 byte", label: "data yang keluar ke cloud" },
            ].map((m, i) => (
              <div key={i} className={metricsVisible ? "animate-slide-up" : "opacity-0"}
                style={{ animationDelay: `${i * 0.1}s` }}>
                <p className="text-4xl md:text-5xl font-black mb-2 leading-none">{m.num}</p>
                <p className="text-indigo-200 text-xs leading-relaxed max-w-[120px] mx-auto">{m.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TESTIMONI ── */}
      <section id="testimoni" ref={testiRef} className="py-28 border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-indigo-600 text-xs font-bold uppercase tracking-widest mb-3">Testimoni</p>
            <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 mb-4">
              Kata mereka yang{" "}
              <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">sudah pakai</span>
            </h2>
            <p className="text-slate-400 text-sm">Tim-tim nyata, waktu nyata yang dihemat.</p>
          </div>

          <div className={`columns-1 md:columns-2 lg:columns-3 gap-5 ${testiVisible ? "animate-fade-in" : "opacity-0"}`}>
            {testimonials.map((t, i) => (
              <div key={t.name} className="break-inside-avoid mb-5">
                <div className={`bg-white border rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300 ${i === 2 ? "border-indigo-200 ring-1 ring-indigo-100" : "border-slate-200 hover:border-slate-300"}`}>
                  {i === 2 && (
                    <div className="mb-3">
                      <span className="text-[10px] font-bold bg-indigo-50 text-indigo-600 border border-indigo-200 px-2 py-0.5 rounded-full uppercase tracking-wider">Featured</span>
                    </div>
                  )}
                  <div className="text-5xl font-serif text-indigo-100 leading-none mb-2 select-none">"</div>
                  <p className="text-slate-600 text-sm leading-relaxed mb-5">{t.quote}</p>
                  <div className="flex items-center gap-3 pt-4 border-t border-slate-100">
                    <Avatar name={t.name} colorIdx={t.colorIdx} size={36} />
                    <div>
                      <p className="text-sm font-bold text-slate-900">{t.name}</p>
                      <p className="text-xs text-slate-400">
                        {t.role} · <span className="text-indigo-500 font-medium">{t.company}</span>
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section id="faq" className="py-28 bg-slate-50 border-b border-slate-100">
        <div className="max-w-2xl mx-auto px-6">
          <div className="text-center mb-12">
            <p className="text-indigo-600 text-xs font-bold uppercase tracking-widest mb-3">FAQ</p>
            <h2 className="text-3xl font-extrabold text-slate-900 mb-3">Pertanyaan yang sering muncul</h2>
            <p className="text-slate-400 text-sm">Masih ada yang kurang jelas? Langsung aja coba dulu.</p>
          </div>

          <div className="space-y-3">
            {faqs.map((faq, idx) => (
              <div key={idx}
                className={`bg-white border rounded-xl overflow-hidden transition-all duration-200 ${activeFaq === idx ? "border-indigo-200 shadow-sm" : "border-slate-200 hover:border-slate-300"}`}>
                <button
                  onClick={() => setActiveFaq(activeFaq === idx ? null : idx)}
                  className="w-full px-6 py-5 flex items-center justify-between text-left gap-4">
                  <span className={`text-sm font-semibold ${activeFaq === idx ? "text-indigo-700" : "text-slate-700"}`}>
                    {faq.question}
                  </span>
                  <span className={`shrink-0 h-6 w-6 rounded-full border flex items-center justify-center text-sm font-bold transition-all duration-300 ${activeFaq === idx ? "bg-indigo-50 border-indigo-200 text-indigo-600 rotate-45" : "border-slate-200 text-slate-400"}`}>
                    +
                  </span>
                </button>
                <div className={`px-6 transition-all duration-300 ease-in-out overflow-hidden ${activeFaq === idx ? "max-h-40 pb-5" : "max-h-0"}`}>
                  <p className="text-slate-500 text-sm leading-relaxed">{faq.answer}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="relative bg-gradient-to-br from-indigo-600 via-violet-600 to-purple-700 py-28 overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 rounded-full bg-white/5 blur-3xl translate-x-1/2 -translate-y-1/2 pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-80 h-80 rounded-full bg-white/5 blur-3xl -translate-x-1/2 translate-y-1/2 pointer-events-none" />
        <div className="absolute inset-0 pointer-events-none" style={{
          backgroundImage: "linear-gradient(rgba(255,255,255,0.07) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.07) 1px,transparent 1px)",
          backgroundSize: "40px 40px",
        }} />

        <div className="relative max-w-2xl mx-auto px-6 text-center text-white">
          <div className="inline-flex items-center gap-2 bg-white/10 border border-white/20 px-3 py-1.5 rounded-full text-xs font-semibold text-indigo-100 mb-8">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Gratis · Self-hosted · Open Source
          </div>
          <h2 className="text-4xl md:text-5xl font-extrabold mb-5 leading-tight">
            Mulai sekarang —<br />gratis, selamanya.
          </h2>
          <p className="text-indigo-200 mb-10 leading-relaxed">
            Tidak ada biaya per pengguna. Tidak ada data ke cloud.<br />Install sendiri, kontrol penuh.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link href="/register"
              className="inline-flex items-center justify-center gap-2 bg-white text-indigo-700 hover:bg-indigo-50 font-bold px-8 py-4 rounded-xl transition shadow-xl text-sm">
              Buat Akun Gratis <ArrowRight size={15} />
            </Link>
            <a href="#cara-kerja"
              className="inline-flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-semibold px-8 py-4 rounded-xl transition text-sm">
              Pelajari Lebih Lanjut
            </a>
          </div>
          <div className="flex flex-wrap justify-center gap-4 mt-8 text-xs text-indigo-300">
            {["✓ Self-hosted", "✓ No cloud", "✓ No per-seat fee"].map((t) => (
              <span key={t}>{t}</span>
            ))}
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="bg-slate-900 py-12">
        <div className="max-w-6xl mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between gap-10 mb-10">
            <div>
              <div className="flex items-center gap-2.5 mb-3">
                <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/25">
                  <Video size={14} className="text-white" />
                </div>
                <span className="font-bold text-base text-white">MeetMate</span>
              </div>
              <p className="text-slate-400 text-xs leading-relaxed max-w-xs">
                Notulensi rapat otomatis dengan AI, sepenuhnya self-hosted. Data tidak pernah keluar dari server kamu.
              </p>
            </div>
            <div className="flex gap-14">
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Produk</p>
                <div className="space-y-2">
                  {navLinks.map(([href, label]) => (
                    <a key={href} href={href} className="block text-xs text-slate-400 hover:text-slate-200 transition">{label}</a>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Akun</p>
                <div className="space-y-2">
                  <Link href="/login" className="block text-xs text-slate-400 hover:text-slate-200 transition">Masuk</Link>
                  <Link href="/register" className="block text-xs text-slate-400 hover:text-slate-200 transition">Daftar</Link>
                </div>
              </div>
            </div>
          </div>
          <div className="pt-6 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
            <p className="text-xs text-slate-600">© {new Date().getFullYear()} MeetMate. Built for teams who value their data.</p>
            <p className="text-xs text-slate-700">Made with care · 100% self-hosted</p>
          </div>
        </div>
      </footer>

    </div>
  );
}
