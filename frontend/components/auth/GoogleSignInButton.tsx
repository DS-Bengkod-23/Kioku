"use client";

import { useEffect, useRef } from "react";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
          }) => void;
          renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void;
        };
      };
    };
  }
}

const GSI_SCRIPT_SRC = "https://accounts.google.com/gsi/client";

interface GoogleSignInButtonProps {
  onCredential: (idToken: string) => void;
  text?: "signin_with" | "signup_with";
}

export default function GoogleSignInButton({ onCredential, text = "signin_with" }: GoogleSignInButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId || !containerRef.current) return;
    let cancelled = false;

    const render = () => {
      if (cancelled || !containerRef.current || !window.google) return;
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (response) => onCredential(response.credential),
      });
      window.google.accounts.id.renderButton(containerRef.current, {
        theme: "outline",
        size: "large",
        // Samain lebar sama elemen lain di form (mis. tombol "Masuk Sekarang" yang
        // w-full) — Google gak punya opsi width "auto"/"100%", jadi diukur manual
        // dari lebar container-nya sendiri. Google clamp nilai ini maks. 400px.
        width: Math.min(containerRef.current.offsetWidth, 400),
        text,
      });
    };

    const existingScript = document.querySelector<HTMLScriptElement>(`script[src="${GSI_SCRIPT_SRC}"]`);
    if (existingScript) {
      if (window.google) render();
      else existingScript.addEventListener("load", render);
    } else {
      const script = document.createElement("script");
      script.src = GSI_SCRIPT_SRC;
      script.async = true;
      script.defer = true;
      script.onload = render;
      document.head.appendChild(script);
    }

    return () => {
      cancelled = true;
    };
  }, [clientId, onCredential, text]);

  // NEXT_PUBLIC_GOOGLE_CLIENT_ID belum di-set (setup Google Cloud project belum
  // kelar di sisi BE/infra — lihat plan/handoff-google-integration.md). Sembunyikan
  // tombol daripada nampilin tombol Google yang gagal init dengan client_id kosong.
  if (!clientId) return null;

  return <div ref={containerRef} className="flex justify-center" />;
}
